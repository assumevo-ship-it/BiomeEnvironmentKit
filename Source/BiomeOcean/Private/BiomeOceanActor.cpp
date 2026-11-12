#include "BiomeOceanActor.h"
#include "BiomeOcean.h"
#include "BiomeWindSea.h"
#include "BiomeWindSource.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "TextureResource.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"

namespace
{
	const TCHAR* DefaultMaterialPath = TEXT("/BiomeAutoMaterials/Ocean/M_BiomeOcean.M_BiomeOcean");
	const TCHAR* UnderwaterMaterialPath = TEXT("/BiomeAutoMaterials/Ocean/M_BiomeUnderwater.M_BiomeUnderwater");
	constexpr float GridExtent = 8000000.f;   // 80 km: past the horizon from up to ~500 m (a shorter grid left a band of the atmosphere's ground)

	float GridPos(int32 I, float G, float FirstStep)
	{
		const int32 A = FMath::Abs(I);
		const float P = FirstStep * (FMath::Pow(G, float(A)) - 1.f) / (G - 1.f);
		return I < 0 ? -P : P;
	}

	float SolveGrowth(int32 HalfRes, float FirstStep)
	{
		// FirstStep * (g^HalfRes - 1) / (g - 1) = GridExtent, solved for g.
		float Lo = 1.0001f, Hi = 1.5f;
		for (int32 It = 0; It < 80; ++It)
		{
			const float Mid = 0.5f * (Lo + Hi);
			const float P = FirstStep * (FMath::Pow(Mid, float(HalfRes)) - 1.f) / (Mid - 1.f);
			(P > GridExtent ? Hi : Lo) = Mid;
		}
		return 0.5f * (Lo + Hi);
	}

	float Smooth01(float A, float B, float X) { return BiomeOcean::SmoothStep01(A, B, X); }

	/** Exact Euclidean distance transform (Felzenszwalb & Huttenlocher) of one row or column, squared distances. */
	void EDT1D(const TArray<float>& F, TArray<float>& D, int32 N, TArray<int32>& V, TArray<float>& Z)
	{
		int32 K = 0;
		V[0] = 0;
		Z[0] = -1e20f;
		Z[1] = 1e20f;
		for (int32 Q = 1; Q < N; ++Q)
		{
			float S;
			for (;;)
			{
				S = ((F[Q] + Q * Q) - (F[V[K]] + V[K] * V[K])) / (2.f * Q - 2.f * V[K]);
				if (S <= Z[K] && K > 0) { --K; continue; }
				break;
			}
			if (S <= Z[K]) { V[K] = Q; Z[K] = -1e20f; Z[K + 1] = 1e20f; continue; }
			++K;
			V[K] = Q;
			Z[K] = S;
			Z[K + 1] = 1e20f;
		}
		K = 0;
		for (int32 Q = 0; Q < N; ++Q)
		{
			while (Z[K + 1] < Q) ++K;
			D[Q] = FMath::Square(float(Q - V[K])) + F[V[K]];
		}
	}

	/** Squared distance (texels) from every texel to the nearest texel where Inside is true. */
	TArray<float> DistanceTo(const TArray<bool>& Inside, int32 N)
	{
		TArray<float> Grid;
		Grid.SetNumUninitialized(N * N);
		for (int32 I = 0; I < N * N; ++I) Grid[I] = Inside[I] ? 0.f : 1e20f;
		TArray<float> F, D, Zs;
		TArray<int32> V;
		F.SetNumUninitialized(N); D.SetNumUninitialized(N); V.SetNumUninitialized(N); Zs.SetNumUninitialized(N + 1);
		for (int32 X = 0; X < N; ++X)
		{
			for (int32 Y = 0; Y < N; ++Y) F[Y] = Grid[Y * N + X];
			EDT1D(F, D, N, V, Zs);
			for (int32 Y = 0; Y < N; ++Y) Grid[Y * N + X] = D[Y];
		}
		for (int32 Y = 0; Y < N; ++Y)
		{
			for (int32 X = 0; X < N; ++X) F[X] = Grid[Y * N + X];
			EDT1D(F, D, N, V, Zs);
			for (int32 X = 0; X < N; ++X) Grid[Y * N + X] = D[X];
		}
		return Grid;
	}
}

ABiomeOcean::ABiomeOcean()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	SetReplicates(false);

	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	RootComponent = Root;

	// Under water: an unbound post-process that only weighs in while the view is below the surface.
	Underwater = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Underwater"));
	Underwater->SetupAttachment(Root);
	Underwater->bUnbound = true;
	Underwater->BlendWeight = 0.f;
	Underwater->Priority = 10.f;

	Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Surface"));
	Surface->SetupAttachment(Root);
	Surface->SetUsingAbsoluteLocation(true);
	Surface->SetUsingAbsoluteRotation(true);
	Surface->SetUsingAbsoluteScale(true);
	Surface->SetMobility(EComponentMobility::Movable);
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetCastShadow(false);
	Surface->bAffectDistanceFieldLighting = false;
	// Out of hardware ray tracing: off-screen Lumen reflection rays on a wavy sea hit the sea itself and bring back its
	// dark surface cache instead of the sky (a dark jagged band along the screen edges).
	Surface->SetVisibleInRayTracing(false);
	Surface->SetCanEverAffectNavigation(false);
	Surface->SetGenerateOverlapEvents(false);
	Surface->bSelectable = false;
	// OceanMaterial stays empty here and EnsureMaterial loads the default on first use: a hard load in the constructor
	// would pin M_BiomeOcean to the class default object, and the material builder could no longer replace it.
}

// ---------------------------------------------------------------------------------------------------------------------
// Lifetime

bool ABiomeOcean::ShouldTickIfViewportsOnly() const
{
	return bPreviewInEditor;
}

void ABiomeOcean::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	if (ShoreData.Num() > 0 && !ShoreTexture) RebuildShoreTexture();
	EnsureMaterial();
}

void ABiomeOcean::BeginPlay()
{
	Super::BeginPlay();
	bWindReady = false;
	bConditionReady = false;
	if (ShoreData.Num() > 0) RebuildShoreTexture();
	EnsureMaterial();
}

void ABiomeOcean::EndPlay(const EEndPlayReason::Type Reason)
{
	if (WindSea) WindSea->Flush();
	Super::EndPlay(Reason);
}

#if WITH_EDITOR
void ABiomeOcean::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
	Super::PostEditChangeProperty(Event);
	const FName Name = Event.GetPropertyName();
	if (Name == GET_MEMBER_NAME_CHECKED(ABiomeOcean, OceanMaterial))
	{
		MID = nullptr;
		GridTier = -1;
	}
	if (Name == GET_MEMBER_NAME_CHECKED(ABiomeOcean, Seed) || Name == GET_MEMBER_NAME_CHECKED(ABiomeOcean, Quality))
	{
		SeaCascades = -1;
		GridTier = -1;
	}
	// The settled sea follows the new settings at once.
	bConditionReady = false;
	bWindReady = false;
	EnsureMaterial();
}
#endif

// ---------------------------------------------------------------------------------------------------------------------
// Quality and grid

ABiomeOcean::FTier ABiomeOcean::CurrentTier() const
{
	int32 Level = int32(Quality) - 1;   // Low 0 .. Epic 3
	if (Quality == EBiomeOceanQuality::Auto)
	{
		static IConsoleVariable* Effects = IConsoleManager::Get().FindConsoleVariable(TEXT("sg.EffectsQuality"));
		Level = Effects ? FMath::Clamp(Effects->GetInt(), 0, 3) : 3;
	}
	switch (FMath::Clamp(Level, 0, 3))
	{
	case 0: return { 0, 128, 60.f, 1 };
	case 1: return { 1, 192, 40.f, 2 };
	case 2: return { 2, 256, 30.f, 3 };
	default: return { 3, 384, 20.f, 3 };
	}
}

bool ABiomeOcean::BuildGrid(const FTier& Tier)
{
	const int32 HalfRes = FMath::Clamp(Tier.HalfRes, 32, 512);
	const float FirstStep = FMath::Max(5.f, Tier.FirstStep);
	const float G = SolveGrowth(HalfRes, FirstStep);
	const int32 Res = 2 * HalfRes + 1;

	FMeshDescription MD;
	FStaticMeshAttributes Attr(MD);
	Attr.Register();
	TVertexAttributesRef<FVector3f> Positions = Attr.GetVertexPositions();
	TVertexInstanceAttributesRef<FVector3f> Normals = Attr.GetVertexInstanceNormals();
	TVertexInstanceAttributesRef<FVector3f> Tangents = Attr.GetVertexInstanceTangents();
	TVertexInstanceAttributesRef<float> Signs = Attr.GetVertexInstanceBinormalSigns();
	TVertexInstanceAttributesRef<FVector2f> UVs = Attr.GetVertexInstanceUVs();
	TPolygonGroupAttributesRef<FName> Slots = Attr.GetPolygonGroupMaterialSlotNames();

	const int32 NumV = Res * Res + 3;
	MD.ReserveNewVertices(NumV);
	MD.ReserveNewVertexInstances(NumV);
	MD.ReserveNewTriangles((Res - 1) * (Res - 1) * 2 + 1);
	const FPolygonGroupID Group = MD.CreatePolygonGroup();
	Slots[Group] = TEXT("Ocean");

	TArray<float> Coord;
	Coord.SetNumUninitialized(Res);
	for (int32 I = 0; I < Res; ++I) Coord[I] = GridPos(I - HalfRes, G, FirstStep);
	TArray<FVertexInstanceID> Inst;
	Inst.SetNumUninitialized(NumV);
	auto AddVertex = [&](int32 Index, const FVector3f& P)
	{
		const FVertexID V = MD.CreateVertex();
		Positions[V] = P;
		const FVertexInstanceID VI = MD.CreateVertexInstance(V);
		Normals[VI] = FVector3f::UpVector;
		Tangents[VI] = FVector3f::ForwardVector;
		Signs[VI] = 1.f;
		UVs.Set(VI, 0, FVector2f(P.X, P.Y) / 10000.f);
		Inst[Index] = VI;
	};
	for (int32 Y = 0; Y < Res; ++Y)
		for (int32 X = 0; X < Res; ++X)
			AddVertex(Y * Res + X, FVector3f(Coord[X], Coord[Y], 0.f));
	for (int32 Y = 0; Y < Res - 1; ++Y)
	{
		for (int32 X = 0; X < Res - 1; ++X)
		{
			const FVertexInstanceID A = Inst[Y * Res + X], B = Inst[Y * Res + X + 1], C = Inst[(Y + 1) * Res + X], D = Inst[(Y + 1) * Res + X + 1];
			// The diagonal alternates by quadrant so the grid stays symmetric about the camera.
			if ((X < HalfRes) == (Y < HalfRes))
			{
				MD.CreateTriangle(Group, { A, C, D });
				MD.CreateTriangle(Group, { A, D, B });
			}
			else
			{
				MD.CreateTriangle(Group, { A, C, B });
				MD.CreateTriangle(Group, { B, C, D });
			}
		}
	}
	// A hair-thin vertical sliver at the far corner gives the bounds height, so crests are never culled.
	AddVertex(Res * Res + 0, FVector3f(GridExtent, GridExtent, -3000.f));
	AddVertex(Res * Res + 1, FVector3f(GridExtent, GridExtent, 3000.f));
	AddVertex(Res * Res + 2, FVector3f(GridExtent - 1.f, GridExtent, 0.f));
	MD.CreateTriangle(Group, { Inst[Res * Res], Inst[Res * Res + 1], Inst[Res * Res + 2] });

	UStaticMesh* Mesh = NewObject<UStaticMesh>(this, NAME_None, RF_Transient);
	Mesh->GetStaticMaterials().Add(FStaticMaterial(OceanMaterial, TEXT("Ocean")));
	UStaticMesh::FBuildMeshDescriptionsParams Params;
	Params.bBuildSimpleCollision = false;
	Params.bFastBuild = true;
	Params.bAllowCpuAccess = false;
	if (!Mesh->BuildFromMeshDescriptions({ &MD }, Params)) return false;
	Surface->SetStaticMesh(Mesh);
	GridTier = Tier.Level;
	GridHalfRes = HalfRes;
	GridFirstStep = FirstStep;
	GridGrowth = G;
	UE_LOG(LogBiomeOcean, Log, TEXT("BiomeOcean: surface grid %dx%d, growth %.4f, first step %.0f cm"), Res, Res, G, FirstStep);
	return true;
}

void ABiomeOcean::EnsureMaterial()
{
	if (!Surface) return;
	if (!OceanMaterial)
	{
		OceanMaterial = LoadObject<UMaterialInterface>(nullptr, DefaultMaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	}
	const FTier Tier = CurrentTier();
	if (GridTier != Tier.Level || !Surface->GetStaticMesh())
	{
		BuildGrid(Tier);
	}
	if (OceanMaterial && (!MID || MID->Parent != OceanMaterial))
	{
		MID = UMaterialInstanceDynamic::Create(OceanMaterial, this);
	}
	if (MID && Surface->GetMaterial(0) != MID) Surface->SetMaterial(0, MID);
	Surface->SetVisibility(MID != nullptr);
	if (MID) UpdateVisuals();
}

// ---------------------------------------------------------------------------------------------------------------------
// Time, wind and sea

float ABiomeOcean::GetOceanTime() const
{
	const UWorld* World = GetWorld();
	if (!World) return 0.f;
	if (World->IsGameWorld())
	{
		const AGameStateBase* GS = World->GetGameState();
		if (bUseServerTime && GS) return float(GS->GetServerWorldTimeSeconds());
		return float(World->GetTimeSeconds());
	}
	// Editor preview: a clock that runs while the viewport ticks.
	return float(FMath::Fmod(FPlatformTime::Seconds(), 86400.0));
}

FVector2D ABiomeOcean::WindVector() const
{
	const float Rad = FMath::DegreesToRadians(WindDirection);
	return FVector2D(FMath::Cos(Rad), FMath::Sin(Rad)) * WindSpeed;
}

FVector ABiomeOcean::GetWindVelocity() const
{
	return FVector(CurrentWind.X, CurrentWind.Y, 0.0);
}

void ABiomeOcean::UpdateWind(float DeltaSeconds)
{
	UWorld* World = GetWorld();
	AActor* Source = WindSource;
	if (!Source && bFindWindSourceAutomatically && World)
	{
		SearchCooldown -= DeltaSeconds;
		if (!FoundWindSource && SearchCooldown <= 0.f)
		{
			SearchCooldown = 2.f;
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				if (*It == this) continue;
				if (It->GetClass()->ImplementsInterface(UBiomeWindSource::StaticClass()) || It->ActorHasTag(TEXT("BiomeSky")))
				{
					FoundWindSource = *It;
					break;
				}
			}
		}
		Source = FoundWindSource;
	}
	FVector2D Target = WindVector();
	if (IsValid(Source))
	{
		if (Source->GetClass()->ImplementsInterface(UBiomeWindSource::StaticClass()))
		{
			const FVector W = IBiomeWindSource::Execute_GetBiomeWindVelocity(Source);
			Target = FVector2D(W.X, W.Y);
		}
		else if (const FStructProperty* Prop = FindFProperty<FStructProperty>(Source->GetClass(), TEXT("WindVelocity")))
		{
			// The BiomeSky actor (or anything with a FVector WindVelocity in m/s), read without linking its module.
			if (Prop->Struct == TBaseStructure<FVector>::Get())
			{
				const FVector W = *Prop->ContainerPtrToValuePtr<FVector>(Source);
				Target = FVector2D(W.X, W.Y);
			}
		}
	}
	else
	{
		FoundWindSource = nullptr;
	}
	if (!bWindReady)
	{
		CurrentWind = Target;
		bWindReady = true;
	}
	else
	{
		CurrentWind = FMath::Lerp(CurrentWind, Target, 1.f - FMath::Exp(-DeltaSeconds * 1.5f));
	}
}

void ABiomeOcean::SetSeaCondition(const FBiomeSeaCondition& Condition)
{
	SeaCondition = Condition;
	++SeaCondition.Generation;
	bConditionReady = true;
}

void ABiomeOcean::UpdateSea(float DeltaSeconds)
{
	const float U = float(CurrentWind.Size());
	const float Heading = U > 0.05f ? float(FMath::RadiansToDegrees(FMath::Atan2(CurrentWind.Y, CurrentWind.X))) : WindDirection;
	const double FetchM = double(FetchKm) * 1000.0;
	const float SwellScale = bSwellFollowsWind ? FMath::Lerp(0.45f, 1.8f, Smooth01(2.f, 24.f, U)) : 1.f;
	if (bGrowSeaOverTime && bConditionReady)
	{
		BiomeOcean::Advance(SeaCondition, Heading, U, FetchM, DeltaSeconds, SeaGrowthTimeScale);
		SeaCondition.Swell = FMath::Lerp(SeaCondition.Swell, SwellScale, 1.f - FMath::Exp(-DeltaSeconds * 0.05f));
	}
	else
	{
		// The sea this wind raises over the fetch and duration, settled. Small changes ease in; big ones reshape at once.
		FBiomeSeaCondition Target;
		Target.WindU = FMath::Max(0.5f, U);
		double Fetch = BiomeOcean::MaxFetch(Target.WindU, FetchM);
		if (WindDurationHours > 0.f) Fetch = FMath::Min(Fetch, BiomeOcean::DurationFetch(Target.WindU, WindDurationHours));
		Target.Fetch = float(Fetch);
		Target.HeadingDeg = Heading;
		Target.OldVariance = FMath::Square(FMath::Max(0.f, CrossSeaHeight) / 4.f);
		Target.OldPeriod = CrossSeaPeriod;
		Target.OldHeadingDeg = CrossSeaDirection;
		Target.Swell = SwellScale;
		if (!bConditionReady)
		{
			Target.Generation = uint8(SeaCondition.Generation + 1);
			SeaCondition = Target;
			bConditionReady = true;
		}
		else
		{
			const float B = 1.f - FMath::Exp(-DeltaSeconds * 2.f);
			SeaCondition.WindU = FMath::Lerp(SeaCondition.WindU, Target.WindU, B);
			SeaCondition.Fetch = FMath::Exp(FMath::Lerp(FMath::Loge(FMath::Max(SeaCondition.Fetch, 1.f)), FMath::Loge(FMath::Max(Target.Fetch, 1.f)), B));
			SeaCondition.HeadingDeg = FMath::UnwindDegrees(SeaCondition.HeadingDeg + FMath::FindDeltaAngleDegrees(SeaCondition.HeadingDeg, Target.HeadingDeg) * B);
			SeaCondition.OldVariance = FMath::Lerp(SeaCondition.OldVariance, Target.OldVariance, B);
			SeaCondition.OldPeriod = FMath::Lerp(SeaCondition.OldPeriod, Target.OldPeriod, B);
			SeaCondition.OldHeadingDeg = FMath::UnwindDegrees(SeaCondition.OldHeadingDeg + FMath::FindDeltaAngleDegrees(SeaCondition.OldHeadingDeg, Target.OldHeadingDeg) * B);
			SeaCondition.Swell = FMath::Lerp(SeaCondition.Swell, Target.Swell, B);
		}
	}

	BiomeOcean::BuildSeaState(SeaCondition, SwellDirection, SwellAmount, Seed, Sea);

	const FTier Tier = CurrentTier();
	const UWorld* World = GetWorld();
	const bool bDraws = World && World->GetNetMode() != NM_DedicatedServer;
	if (!WindSea) WindSea = NewObject<UBiomeWindSea>(this);
	if (SeaCascades != Tier.Cascades)
	{
		SeaCascades = Tier.Cascades;
		WindSea->Configure(uint32(Seed) + 31u, Tier.Cascades, bDraws);
	}
	const float Cover = BiomeOcean::WhitecapCover(SeaCondition.WindU) * FMath::Max(0.f, WhitecapAmount);
	const float Life = FoamLifetime * FMath::Lerp(1.f, 2.5f, Smooth01(8.f, 25.f, SeaCondition.WindU));
	WindSea->Tick(DeltaSeconds, double(GetOceanTime()), SeaCondition, Cover, Life);
	Sea.WindSea = WindSea->GetField();
	if (WindSea->GetHeightVariance() > 0.0) Sea.WindSeaVariance = float(WindSea->GetHeightVariance() * 1e4);
}

void ABiomeOcean::FlushWindSea()
{
	if (WindSea)
	{
		WindSea->Flush();
		Sea.WindSea = WindSea->GetField();
	}
}

bool ABiomeOcean::GetViewLocation(FVector& Out) const
{
	const UWorld* World = GetWorld();
	if (!World) return false;
	if (World->IsGameWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			FRotator Rot;
			PC->GetPlayerViewPoint(Out, Rot);
			return true;
		}
	}
	if (World->ViewLocationsRenderedLastFrame.Num() > 0)
	{
		Out = World->ViewLocationsRenderedLastFrame[0];
		return true;
	}
	Out = GetActorLocation();
	return true;
}

void ABiomeOcean::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UWorld* World = GetWorld();
	if (!World) return;
	if (!World->IsGameWorld() && !bPreviewInEditor) return;
	DeltaSeconds = FMath::Clamp(DeltaSeconds, 0.f, 0.25f);
	UpdateWind(DeltaSeconds);
	UpdateSea(DeltaSeconds);
	if (World->GetNetMode() != NM_DedicatedServer)
	{
		if (GridTier != CurrentTier().Level) EnsureMaterial();
		UpdateVisuals();
	}
}

void ABiomeOcean::UpdateVisuals()
{
	if (!MID || !Surface) return;
	FVector View;
	GetViewLocation(View);
	const float SeaZ = float(GetActorLocation().Z);
	const double Snap = GridFirstStep * 4.0;
	const FVector At(FMath::GridSnap(View.X, Snap), FMath::GridSnap(View.Y, Snap), SeaZ);
	Surface->SetWorldLocation(At);

	static const FName WaveNames[BiomeOcean::NumSwells] = { TEXT("Wave0"), TEXT("Wave1"), TEXT("Wave2"), TEXT("Wave3"), TEXT("Wave4") };
	for (int32 I = 0; I < BiomeOcean::NumSwells; ++I)
	{
		const BiomeOcean::FWave& W = Sea.Waves[I];
		MID->SetVectorParameterValue(WaveNames[I], FLinearColor(W.Dir.X, W.Dir.Y, W.K, W.Amp));
	}
	MID->SetVectorParameterValue(TEXT("WavePhaseA"), FLinearColor(Sea.Waves[0].Phase, Sea.Waves[1].Phase, Sea.Waves[2].Phase, Sea.Waves[3].Phase));
	// (phase of swell 4, Gerstner Q, sea strength, beach run-up cm)
	MID->SetVectorParameterValue(TEXT("WavePhaseB"), FLinearColor(Sea.Waves[4].Phase, Sea.Choppiness, Sea.Strength, Sea.RunUp));
	MID->SetScalarParameterValue(TEXT("WaveTime"), GetOceanTime());
	// (seed, total wind-sea variance cm^2, wind-sea choppiness, sea level Z)
	MID->SetVectorParameterValue(TEXT("SeaInfo"), FLinearColor(float(Sea.Seed), Sea.WindSeaVariance, WindSea ? WindSea->GetChoppiness() : 1.f, SeaZ));
	const float WindU = SeaCondition.WindU;
	MID->SetVectorParameterValue(TEXT("SeaWind"), FLinearColor(Sea.SeaHeading.X, Sea.SeaHeading.Y, WindU, BiomeOcean::WhitecapCover(WindU) * WhitecapAmount));
	MID->SetVectorParameterValue(TEXT("GridShape"), FLinearColor(GridGrowth, GridFirstStep, float(GridHalfRes), 0.f));
	MID->SetScalarParameterValue(TEXT("ShoreFoam"), ShoreFoam);
	MID->SetVectorParameterValue(TEXT("DeepAbsorption"), DeepAbsorption);
	MID->SetVectorParameterValue(TEXT("DeepScattering"), DeepScattering);
	MID->SetVectorParameterValue(TEXT("ShallowAbsorption"), ShallowAbsorption);
	MID->SetVectorParameterValue(TEXT("ShallowScattering"), ShallowScattering);
	MID->SetScalarParameterValue(TEXT("WaterRoughness"), WaterRoughness);
	MID->SetVectorParameterValue(TEXT("FoamColor"), FoamColor);
	const bool bShore = ShoreTexture && ShoreBounds.W > 0.5;
	MID->SetScalarParameterValue(TEXT("HasShore"), bShore ? 1.f : 0.f);
	if (bShore)
	{
		MID->SetTextureParameterValue(TEXT("ShoreField"), ShoreTexture);
		MID->SetVectorParameterValue(TEXT("ShoreBounds"), FLinearColor(float(ShoreBounds.X), float(ShoreBounds.Y), float(ShoreBounds.Z), float(ShoreBounds.W)));
	}
	double Slopes = WindSea ? WindSea->GetSlopeVariance() : 0.0;
	MID->SetScalarParameterValue(TEXT("ResolvedSlopeVar"), float(Slopes));
	if (WindSea) WindSea->Bind(MID);
	UpdateUnderwater(View);
}

void ABiomeOcean::UpdateUnderwater(const FVector& View)
{
	if (!Underwater) return;
	if (!bUnderwaterView)
	{
		Underwater->BlendWeight = 0.f;
		return;
	}
	if (!UnderwaterMaterial)
	{
		UnderwaterMaterial = LoadObject<UMaterialInterface>(nullptr, UnderwaterMaterialPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!UnderwaterMaterial) return;
	}
	if (!UnderwaterMID || UnderwaterMID->Parent != UnderwaterMaterial)
	{
		UnderwaterMID = UMaterialInstanceDynamic::Create(UnderwaterMaterial, this);
		Underwater->Settings.WeightedBlendables.Array.Reset();
		Underwater->Settings.WeightedBlendables.Array.Add(FWeightedBlendable(1.f, UnderwaterMID));
	}
	// Below the crest over the camera (with a few cm either way so the waterline does not flicker).
	const float DepthCm = GetWaterHeightAt(View) - float(View.Z);
	Underwater->BlendWeight = FMath::Clamp((DepthCm + 4.f) / 8.f, 0.f, 1.f);
	if (Underwater->BlendWeight <= 0.f) return;

	// Daylight from the atmosphere's sun (any directional light that lights the sky), by its height.
	if (!SunForUnderwater.IsValid())
	{
		for (TObjectIterator<UDirectionalLightComponent> It; It; ++It)
		{
			if (It->GetWorld() == GetWorld() && It->IsUsedAsAtmosphereSunLight() && It->IsVisible()) { SunForUnderwater = *It; break; }
		}
	}
	float Day = 1.f;
	if (const UDirectionalLightComponent* Sun = SunForUnderwater.Get())
	{
		const float Up = float(-Sun->GetDirection().Z);   // the light travels down when the sun is up
		Day = FMath::Lerp(0.015f, 1.f, FMath::SmoothStep(-0.1f, 0.35f, Up));
	}
	const float M = FMath::Max(DepthCm, 0.f) / 100.f;
	const FLinearColor Down(FMath::Exp(-UnderwaterExtinction.R * M), FMath::Exp(-UnderwaterExtinction.G * M), FMath::Exp(-UnderwaterExtinction.B * M));
	UnderwaterMID->SetVectorParameterValue(TEXT("Extinction"), UnderwaterExtinction);
	UnderwaterMID->SetVectorParameterValue(TEXT("WaterLight"), UnderwaterLight * Down * Day);
}

// ---------------------------------------------------------------------------------------------------------------------
// Queries

BiomeOcean::FShore ABiomeOcean::SampleShore(const FVector2D& XYcm) const
{
	BiomeOcean::FShore Out;
	const int32 N = int32(ShoreBounds.W);
	if (N <= 1 || ShoreData.Num() != N * N * 4) return Out;
	const double U = (XYcm.X - ShoreBounds.X) / ShoreBounds.Z * N - 0.5;
	const double V = (XYcm.Y - ShoreBounds.Y) / ShoreBounds.Z * N - 0.5;
	if (U < -0.5 || V < -0.5 || U > N - 0.5 || V > N - 0.5) return Out;
	const int32 X0 = FMath::Clamp(int32(FMath::Floor(U)), 0, N - 1), Y0 = FMath::Clamp(int32(FMath::Floor(V)), 0, N - 1);
	const int32 X1 = FMath::Min(X0 + 1, N - 1), Y1 = FMath::Min(Y0 + 1, N - 1);
	const float TX = float(FMath::Clamp(U - X0, 0.0, 1.0)), TY = float(FMath::Clamp(V - Y0, 0.0, 1.0));
	auto At = [&](int32 X, int32 Y, int32 C) { return ShoreData[(Y * N + X) * 4 + C]; };
	auto Bi = [&](int32 C) { return FMath::Lerp(FMath::Lerp(At(X0, Y0, C), At(X1, Y0, C), TX), FMath::Lerp(At(X0, Y1, C), At(X1, Y1, C), TX), TY); };
	// Fade into the open sea at the field's border, so its edge never shows as a line.
	const float Edge = Smooth01(0.f, 8.f, float(FMath::Min(FMath::Min(U, V), FMath::Min(N - 1 - U, N - 1 - V))));
	Out.SignedDistM = FMath::Lerp(300.f, Bi(0), Edge);
	Out.DepthM = FMath::Lerp(40.f, Bi(1), Edge);
	FVector2f Dir(Bi(2), Bi(3));
	Out.ToShore = Dir.SizeSquared() > 1e-6f ? Dir.GetSafeNormal() : FVector2f(1.f, 0.f);
	return Out;
}

float ABiomeOcean::GetWaterHeightAt(const FVector& Location) const
{
	const float SeaZ = float(GetActorLocation().Z);
	return SeaZ + BiomeOcean::SurfaceHeight(Sea, [this](const FVector2D& P) { return SampleShore(P); }, FVector2D(Location), GetOceanTime());
}

void ABiomeOcean::GetWaterHeights(TArrayView<const FVector2D> PointsXY, TArrayView<float> OutZ) const
{
	const float SeaZ = float(GetActorLocation().Z);
	const float T = GetOceanTime();
	for (int32 I = 0; I < PointsXY.Num() && I < OutZ.Num(); ++I)
	{
		OutZ[I] = SeaZ + BiomeOcean::SurfaceHeight(Sea, [this](const FVector2D& P) { return SampleShore(P); }, PointsXY[I], T);
	}
}

void ABiomeOcean::GetWaterSurfaceAt(const FVector& Location, float& Height, FVector& Normal, FVector& Velocity) const
{
	const BiomeOcean::FSurfaceSample S = BiomeOcean::SurfaceKinematics(Sea, [this](const FVector2D& P) { return SampleShore(P); }, FVector2D(Location), GetOceanTime());
	Height = float(GetActorLocation().Z) + S.Height;
	Normal = S.Normal;
	Velocity = S.Velocity;
}

bool ABiomeOcean::IsUnderwater(const FVector& Location, float& Depth) const
{
	Depth = GetWaterHeightAt(Location) - float(Location.Z);
	return Depth > 0.f;
}

float ABiomeOcean::GetSignificantWaveHeight() const
{
	double Var = Sea.WindSeaVariance;   // cm^2
	for (const BiomeOcean::FWave& W : Sea.Waves) Var += 0.5 * double(W.Amp) * W.Amp;
	return float(4.0 * FMath::Sqrt(Var) / 100.0);
}

FVector ABiomeOcean::GetWaveDisplacementAt(const FVector& Location) const
{
	const FVector2D XY(Location);
	return BiomeOcean::Displacement(Sea, SampleShore(XY), XY, GetOceanTime());
}

ABiomeOcean* ABiomeOcean::FindOcean(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	if (!World) return nullptr;
	for (TActorIterator<ABiomeOcean> It(World); It; ++It) return *It;
	return nullptr;
}

// ---------------------------------------------------------------------------------------------------------------------
// Shore field

void ABiomeOcean::BakeShoreField()
{
	UWorld* World = GetWorld();
	if (!World) return;
	int32 N = FMath::RoundUpToPowerOfTwo(FMath::Clamp(ShoreBakeResolution, 64, 2048));
	const FVector Centre = GetActorLocation();
	const double Span = 2.0 * ShoreBakeHalfSize;
	const double MinX = Centre.X - ShoreBakeHalfSize, MinY = Centre.Y - ShoreBakeHalfSize;
	const double Texel = Span / N;
	const double SeaZ = Centre.Z;
	const double TopZ = SeaZ + 200000.0, BottomZ = SeaZ - ShoreMaxDepth * 100.0 - 5000.0;

	FCollisionQueryParams Query(SCENE_QUERY_STAT(BiomeOceanShoreBake), true, this);
	TArray<float> Depth;   // metres of water (negative: land above the sea)
	Depth.SetNumUninitialized(N * N);
	int32 Land = 0, Hits = 0;
	for (int32 Y = 0; Y < N; ++Y)
	{
		for (int32 X = 0; X < N; ++X)
		{
			const double WX = MinX + (X + 0.5) * Texel, WY = MinY + (Y + 0.5) * Texel;
			FHitResult Hit;
			float D = ShoreMaxDepth + 10.f;
			if (World->LineTraceSingleByChannel(Hit, FVector(WX, WY, TopZ), FVector(WX, WY, BottomZ), ShoreTraceChannel, Query))
			{
				D = float((SeaZ - Hit.ImpactPoint.Z) / 100.0);
				++Hits;
			}
			Depth[Y * N + X] = D;
			if (D < 0.f) ++Land;
		}
	}
	if (Land == 0)
	{
		UE_LOG(LogBiomeOcean, Warning, TEXT("BiomeOcean: no land above the sea within %.0f m of the ocean actor (%d of %d traces hit ground): no shore field."),
			ShoreBakeHalfSize / 100.f, Hits, N * N);
		ClearShoreField();
		return;
	}
	TArray<bool> IsLand, IsWater;
	IsLand.SetNumUninitialized(N * N);
	IsWater.SetNumUninitialized(N * N);
	for (int32 I = 0; I < N * N; ++I) { IsLand[I] = Depth[I] < 0.f; IsWater[I] = !IsLand[I]; }
	const TArray<float> ToLand = DistanceTo(IsLand, N);
	const TArray<float> ToWater = DistanceTo(IsWater, N);
	TArray<float> Signed;
	Signed.SetNumUninitialized(N * N);
	const float TexelM = float(Texel / 100.0);
	for (int32 I = 0; I < N * N; ++I)
	{
		// Distance to the waterline: half a texel either side of it.
		Signed[I] = IsLand[I] ? -(FMath::Sqrt(ToWater[I]) - 0.5f) * TexelM : (FMath::Sqrt(ToLand[I]) - 0.5f) * TexelM;
	}
	// A little smoothing so the direction to the shore turns gently round headlands.
	TArray<float> Smooth = Signed;
	for (int32 Pass = 0; Pass < 2; ++Pass)
	{
		TArray<float> Next = Smooth;
		for (int32 Y = 1; Y < N - 1; ++Y)
			for (int32 X = 1; X < N - 1; ++X)
			{
				float Sum = 0.f;
				for (int32 DY = -1; DY <= 1; ++DY) for (int32 DX = -1; DX <= 1; ++DX) Sum += Smooth[(Y + DY) * N + X + DX];
				Next[Y * N + X] = Sum / 9.f;
			}
		Smooth = MoveTemp(Next);
	}
	ShoreData.SetNumUninitialized(N * N * 4);
	for (int32 Y = 0; Y < N; ++Y)
	{
		for (int32 X = 0; X < N; ++X)
		{
			const int32 I = Y * N + X;
			const float GX = Smooth[Y * N + FMath::Min(X + 1, N - 1)] - Smooth[Y * N + FMath::Max(X - 1, 0)];
			const float GY = Smooth[FMath::Min(Y + 1, N - 1) * N + X] - Smooth[FMath::Max(Y - 1, 0) * N + X];
			FVector2f Dir(-GX, -GY);   // down the distance: towards the land
			Dir = Dir.SizeSquared() > 1e-8f ? Dir.GetSafeNormal() : FVector2f(1.f, 0.f);
			// Depth: real where it is shallow, eased into the 40 m reference sea the swells are tuned for.
			const float D = FMath::Max(Depth[I], -5.f);
			ShoreData[I * 4 + 0] = FMath::Clamp(Signed[I], -300.f, 300.f);
			ShoreData[I * 4 + 1] = FMath::Lerp(FMath::Max(D, 0.f), 40.f, Smooth01(20.f, FMath::Max(25.f, ShoreMaxDepth), D));
			ShoreData[I * 4 + 2] = Dir.X;
			ShoreData[I * 4 + 3] = Dir.Y;
		}
	}
	ShoreBounds = FVector4(MinX, MinY, Span, N);
	Modify();
	RebuildShoreTexture();
	UE_LOG(LogBiomeOcean, Log, TEXT("BiomeOcean: shore field baked, %dx%d over %.0f m (%.1f m texels), %d land texels"), N, N, Span / 100.0, TexelM, Land);
}

void ABiomeOcean::ClearShoreField()
{
	Modify();
	ShoreData.Reset();
	ShoreBounds = FVector4(0, 0, 1, 0);
	ShoreTexture = nullptr;
}

void ABiomeOcean::RebuildShoreTexture()
{
	const int32 N = int32(ShoreBounds.W);
	if (N <= 1 || ShoreData.Num() != N * N * 4)
	{
		ShoreTexture = nullptr;
		return;
	}
	UTexture2D* Texture = UTexture2D::CreateTransient(N, N, PF_A32B32G32R32F);
	if (!Texture) return;
	Texture->SRGB = false;
	Texture->Filter = TF_Bilinear;
	Texture->AddressX = TA_Clamp;
	Texture->AddressY = TA_Clamp;
	Texture->NeverStream = true;
	void* Bytes = Texture->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE);
	FMemory::Memcpy(Bytes, ShoreData.GetData(), ShoreData.Num() * sizeof(float));
	Texture->GetPlatformData()->Mips[0].BulkData.Unlock();
	Texture->UpdateResource();
	ShoreTexture = Texture;
}
