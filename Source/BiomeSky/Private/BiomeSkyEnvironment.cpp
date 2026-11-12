#include "BiomeSkyEnvironment.h"
#include "BiomeSky.h"
#include "BiomeSkyAstronomy.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "MaterialShared.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "RHIGlobals.h"

namespace
{
	const TCHAR* SkyMaterialPath = TEXT("/BiomeAutoMaterials/Sky/M_BiomeSky.M_BiomeSky");
	const TCHAR* CloudMaterialPath = TEXT("/BiomeAutoMaterials/Sky/M_BiomeClouds.M_BiomeClouds");
	const TCHAR* PrecipitationMaterialPath = TEXT("/BiomeAutoMaterials/Sky/M_BiomePrecipitation.M_BiomePrecipitation");
	const TCHAR* CollectionPath = TEXT("/BiomeAutoMaterials/Sky/MPC_BiomeSky.MPC_BiomeSky");
	const TCHAR* DomeMeshPath = TEXT("/Engine/EngineSky/SM_SkySphere.SM_SkySphere");
	const TCHAR* PlaneMeshPath = TEXT("/Engine/BasicShapes/Plane.Plane");

	/** The star dome's radius (cm). The fog stops short of it (FogCutoffDistance) so it never hides the sky. */
	constexpr float DomeRadius = 4000000.f;
	/** Half extents of the box of falling rain or snow that follows the camera (cm). */
	const FVector PrecipitationBox(1500.f, 1500.f, 900.f);
	/** A directional light only turns once the sky has moved this far (cos 0.15 deg): any turn re-renders every cached
	 *  virtual shadow map page, and 0.15 deg moves a 20 m shadow by 5 cm. */
	constexpr double SkyStepCos = 0.99999657;

	FLinearColor V4(const FVector& V, float W = 0.f) { return FLinearColor(float(V.X), float(V.Y), float(V.Z), W); }
}

FBiomeSkyWeatherState FBiomeSkyWeatherState::Lerp(const FBiomeSkyWeatherState& A, const FBiomeSkyWeatherState& B, float T)
{
	FBiomeSkyWeatherState O;
	// Clouds build ahead of the rain and clear after it (the rain trails the cover both ways).
	const float Building = B.CloudCover >= A.CloudCover ? 1.f : 0.f;
	const float CoverT = FMath::SmoothStep(Building > 0.f ? 0.f : 0.22f, Building > 0.f ? 0.72f : 1.f, T);
	const float RainT = FMath::SmoothStep(Building > 0.f ? 0.35f : 0.f, Building > 0.f ? 1.f : 0.6f, T);
	O.CloudCover = FMath::Lerp(A.CloudCover, B.CloudCover, CoverT);
	O.Convection = FMath::Lerp(A.Convection, B.Convection, FMath::SmoothStep(0.12f, 0.88f, T));
	O.Precipitation = FMath::Lerp(A.Precipitation, B.Precipitation, RainT);
	O.HighCloud = FMath::Lerp(A.HighCloud, B.HighCloud, FMath::SmoothStep(0.08f, 1.f, T));
	// Visibility blends in log space (25 km to 300 m should not linger at 12 km).
	O.VisibilityKm = FMath::Exp(FMath::Lerp(FMath::Loge(FMath::Max(A.VisibilityKm, 0.01f)), FMath::Loge(FMath::Max(B.VisibilityKm, 0.01f)), RainT));
	O.Storm = FMath::Lerp(A.Storm, B.Storm, RainT);
	O.Snow = FMath::Lerp(A.Snow, B.Snow, T);
	return O;
}

FBiomeSkyWeatherState ABiomeSkyEnvironment::GetDefaultPreset(EBiomeSkyWeather Preset)
{
	FBiomeSkyWeatherState S;
	auto Set = [&S](float Cover, float Conv, float Precip, float High, float Vis, float Storm, float Snow)
	{
		S.CloudCover = Cover; S.Convection = Conv; S.Precipitation = Precip; S.HighCloud = High;
		S.VisibilityKm = Vis; S.Storm = Storm; S.Snow = Snow;
	};
	switch (Preset)
	{
	case EBiomeSkyWeather::Clear:    Set(0.06f, 0.02f, 0.f, 0.08f, 40.f, 0.f, 0.f); break;
	case EBiomeSkyWeather::Fair:     Set(0.36f, 0.12f, 0.f, 0.22f, 25.f, 0.f, 0.f); break;
	case EBiomeSkyWeather::Overcast: Set(0.74f, 0.26f, 0.f, 0.40f, 15.f, 0.f, 0.f); break;
	case EBiomeSkyWeather::Rain:     Set(0.88f, 0.40f, 0.62f, 0.54f, 4.f, 0.f, 0.f); break;
	case EBiomeSkyWeather::Storm:    Set(0.95f, 0.85f, 0.95f, 0.72f, 1.5f, 1.f, 0.f); break;
	case EBiomeSkyWeather::Snow:     Set(0.86f, 0.15f, 0.55f, 0.35f, 2.5f, 0.f, 1.f); break;
	case EBiomeSkyWeather::Fog:      Set(0.55f, 0.05f, 0.f, 0.15f, 0.3f, 0.f, 0.f); break;
	}
	return S;
}

ABiomeSkyEnvironment::ABiomeSkyEnvironment()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;
	bReplicates = false;
	Tags.Add(TEXT("BiomeSky"));

	SkyMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(SkyMaterialPath));
	CloudMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(CloudMaterialPath));
	PrecipitationMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(PrecipitationMaterialPath));
	ParameterCollection = TSoftObjectPtr<UMaterialParameterCollection>(FSoftObjectPath(CollectionPath));
	SkyDomeMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(DomeMeshPath));
	ParticleMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(PlaneMeshPath));
	for (EBiomeSkyWeather W : { EBiomeSkyWeather::Clear, EBiomeSkyWeather::Fair, EBiomeSkyWeather::Overcast, EBiomeSkyWeather::Rain,
		EBiomeSkyWeather::Storm, EBiomeSkyWeather::Snow, EBiomeSkyWeather::Fog })
	{
		WeatherPresets.Add(W, GetDefaultPreset(W));
	}

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	RootComponent = Root;

	// The sun: the atmosphere's light 0, a real 0.53-degree disc, cloud shadows and per-pixel atmospheric colour at dawn.
	SunLight = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("SunLight"));
	SunLight->SetupAttachment(Root);
	SunLight->SetUsingAbsoluteRotation(true);
	SunLight->SetMobility(EComponentMobility::Movable);
	SunLight->SetAtmosphereSunLight(true);
	SunLight->SetAtmosphereSunLightIndex(0);
	SunLight->LightSourceAngle = 0.545f;
	SunLight->bCastCloudShadows = true;
	SunLight->bCastShadowsOnClouds = true;
	SunLight->bPerPixelAtmosphereTransmittance = true;
	SunLight->CloudShadowExtent = 35.f;
	SunLight->CloudShadowMapResolutionScale = 1.5f;
	SunLight->VolumetricScatteringIntensity = 1.2f;
	SunLight->SetLightColor(FLinearColor(1.f, 0.96f, 0.9f));
	SunLight->SetIntensity(SunIntensity);

	// The moon: the atmosphere's light 1 (so its light reddens and dims low down too); its disc is drawn by the sky material.
	MoonLight = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("MoonLight"));
	MoonLight->SetupAttachment(Root);
	MoonLight->SetUsingAbsoluteRotation(true);
	MoonLight->SetMobility(EComponentMobility::Movable);
	MoonLight->SetAtmosphereSunLight(true);
	MoonLight->SetAtmosphereSunLightIndex(1);
	MoonLight->LightSourceAngle = 0.52f;
	MoonLight->bCastCloudShadows = true;
	MoonLight->SetLightColor(FLinearColor(0.72f, 0.80f, 1.f));
	MoonLight->SetIntensity(0.f);

	// The planet's top sits GroundDepth under the actor: with per-pixel transmittance everything below the planet's
	// ground is in its shadow, so a seabed at the actor's height would lose the sun.
	Atmosphere = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Atmosphere"));
	Atmosphere->SetupAttachment(Root);
	Atmosphere->SetMobility(EComponentMobility::Movable);
	Atmosphere->TransformMode = ESkyAtmosphereTransformMode::PlanetTopAtComponentTransform;
	Atmosphere->SetRelativeLocation(FVector(0.f, 0.f, -GroundDepth));
	// The ground under the air is dark (ocean ~6%, forest ~10%): the default 40% grey filled the lower half of the sky
	// capture and every rough reflection with a tan glow.
	Atmosphere->GroundAlbedo = FColor(40, 56, 68);

	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->bRealTimeCapture = true;
	SkyLight->CubemapResolution = 512;   // keeps clouds' texture in sharp reflections (water)
	SkyLight->bCloudAmbientOcclusion = true;
	SkyLight->CloudAmbientOcclusionStrength = 0.7f;
	SkyLight->CloudAmbientOcclusionExtent = 25.f;

	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(Root);
	Fog->SetMobility(EComponentMobility::Movable);
	Fog->FogDensity = 0.001f;
	Fog->FogHeightFalloff = 0.2f;

	Clouds = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("Clouds"));
	Clouds->SetupAttachment(Root);
	Clouds->SetMobility(EComponentMobility::Movable);
	// The cloud shader's bands assume this 0.8-12 km shell (Tools/sky/hlsl/BiomeClouds.hlsl).
	Clouds->LayerBottomAltitude = 0.8f;
	Clouds->LayerHeight = 11.2f;
	Clouds->TracingStartMaxDistance = 250.f;
	Clouds->TracingMaxDistance = 100.f;
	Clouds->GroundAlbedo = FColor(18, 26, 32);
	Clouds->StopTracingTransmittanceThreshold = 0.005f;
	Clouds->bUsePerSampleAtmosphericLightTransmittance = true;
	Clouds->ViewSampleCountScale = 2.f;
	Clouds->ShadowViewSampleCountScale = 2.f;
	Clouds->ReflectionViewSampleCountScaleValue = 0.6f;
	Clouds->ShadowReflectionViewSampleCountScaleValue = 0.6f;
	Clouds->ShadowTracingDistance = 12.f;
	Clouds->Material = nullptr;   // set once its shaders are compiled (the cloud renderer asserts on a fallback material)

	SkyDome = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SkyDome"));
	SkyDome->SetupAttachment(Root);
	SkyDome->SetMobility(EComponentMobility::Movable);
	SkyDome->SetUsingAbsoluteLocation(true);
	SkyDome->SetUsingAbsoluteRotation(true);
	SkyDome->SetUsingAbsoluteScale(true);
	SkyDome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SkyDome->SetCastShadow(false);
	SkyDome->bAffectDistanceFieldLighting = false;
	SkyDome->SetVisibleInRayTracing(false);
	SkyDome->bVisibleInRealTimeSkyCaptures = true;
	SkyDome->SetCanEverAffectNavigation(false);

	Exposure = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Exposure"));
	Exposure->SetupAttachment(Root);
	Exposure->bUnbound = true;
	Exposure->Priority = 0.f;

	Precipitation = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Precipitation"));
	Precipitation->SetupAttachment(Root);
	Precipitation->SetMobility(EComponentMobility::Movable);
	Precipitation->SetUsingAbsoluteLocation(true);
	Precipitation->SetUsingAbsoluteRotation(true);
	Precipitation->SetUsingAbsoluteScale(true);
	Precipitation->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Precipitation->SetCastShadow(false);
	Precipitation->SetGenerateOverlapEvents(false);
	Precipitation->SetCanEverAffectNavigation(false);
	Precipitation->bAffectDistanceFieldLighting = false;
	Precipitation->SetVisibleInRayTracing(false);
	Precipitation->bVisibleInRealTimeSkyCaptures = false;
	Precipitation->SetVisibility(false);

	LightningLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("LightningLight"));
	LightningLight->SetupAttachment(Root);
	LightningLight->SetMobility(EComponentMobility::Movable);
	LightningLight->SetUsingAbsoluteLocation(true);
	LightningLight->SetCastShadows(false);
	LightningLight->SetIntensityUnits(ELightUnits::Candelas);
	LightningLight->SetIntensity(0.f);
	LightningLight->SetAttenuationRadius(1200000.f);
	LightningLight->SetLightColor(FLinearColor(0.72f, 0.8f, 1.f));
	LightningLight->SetVisibility(false);

	LightningRandom.Initialize(9157);
}

// ---------------------------------------------------------------------------------------------------------------------
// Blueprint API

void ABiomeSkyEnvironment::SetTimeOfDay(float Hours)
{
	TimeOfDay = FMath::Fmod(FMath::Fmod(Hours, 24.f) + 24.f, 24.f);
	UpdateCelestial();
	UpdateLights();
}

void ABiomeSkyEnvironment::SetDate(int32 InYear, int32 InMonth, int32 InDay)
{
	Year = FMath::Clamp(InYear, 1, 9998);
	Month = FMath::Clamp(InMonth, 1, 12);
	Day = FMath::Clamp(InDay, 1, FDateTime::DaysInMonth(Year, Month));
	UpdateCelestial();
	UpdateLights();
}

void ABiomeSkyEnvironment::SetLocation(float InLatitude, float InLongitude)
{
	Latitude = FMath::Clamp(InLatitude, -89.9f, 89.9f);
	Longitude = FMath::Clamp(InLongitude, -180.f, 180.f);
	UpdateCelestial();
	UpdateLights();
}

void ABiomeSkyEnvironment::SetWeather(EBiomeSkyWeather NewWeather, float BlendSeconds)
{
	if (NewWeather == AppliedWeather && bWeatherInitialised) return;
	BlendFrom = CurrentWeather;
	BlendTime = 0.f;
	BlendDuration = BlendSeconds < 0.f ? WeatherBlendSeconds : BlendSeconds;
	Weather = NewWeather;
	AppliedWeather = NewWeather;
	bWeatherInitialised = true;
	if (BlendDuration <= 0.f) bSnap = true;
}

void ABiomeSkyEnvironment::SetCloudCover(float Cover)
{
	bOverrideCloudCover = Cover >= 0.f;
	CloudCover = FMath::Clamp(Cover, 0.f, 1.f);
}

void ABiomeSkyEnvironment::SetWind(float DirectionDegrees, float SpeedMetresPerSecond)
{
	WindDirection = DirectionDegrees;
	WindSpeed = FMath::Max(0.f, SpeedMetresPerSecond);
}

void ABiomeSkyEnvironment::SnapToTarget()
{
	bSnap = true;
}

FBiomeSkyWeatherState ABiomeSkyEnvironment::GetPreset(EBiomeSkyWeather Preset) const
{
	const FBiomeSkyWeatherState* Found = WeatherPresets.Find(Preset);
	return Found ? *Found : GetDefaultPreset(Preset);
}

double ABiomeSkyEnvironment::GetDaysSinceJ2000() const
{
	const double Offset = bSolarTime ? Longitude / 15.0 : UtcOffsetHours;
	return BiomeSkyAstronomy::DaysSinceJ2000(BiomeSkyAstronomy::JulianDate(Year, Month, Day, TimeOfDay, Offset));
}

ABiomeSkyEnvironment* ABiomeSkyEnvironment::FindSky(const UObject* WorldContext)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World) return nullptr;
	for (TActorIterator<ABiomeSkyEnvironment> It(World); It; ++It) return *It;
	return nullptr;
}

// ---------------------------------------------------------------------------------------------------------------------
// Lifetime

void ABiomeSkyEnvironment::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyStaticSettings();
	EnsureMaterials();
	if (!GetWorld() || !GetWorld()->IsGameWorld())
	{
		// The editor shows the chosen weather at once.
		bSnap = true;
		bWeatherInitialised = false;
	}
	Tick(0.f);
}

void ABiomeSkyEnvironment::BeginPlay()
{
	Super::BeginPlay();
	bWeatherInitialised = false;
	bSnap = true;
	ApplyStaticSettings();
	EnsureMaterials();
}

#if WITH_EDITOR
void ABiomeSkyEnvironment::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
	Super::PostEditChangeProperty(Event);
	bSnap = true;
	bWeatherInitialised = false;
	ParticleCount = -1;
}
#endif

void ABiomeSkyEnvironment::ApplyStaticSettings()
{
	if (Atmosphere) Atmosphere->SetRelativeLocation(FVector(0.f, 0.f, -GroundDepth));
	if (SkyDome && !SkyDome->GetStaticMesh())
	{
		if (UStaticMesh* Dome = SkyDomeMesh.LoadSynchronous())
		{
			SkyDome->SetStaticMesh(Dome);
		}
	}
	if (SkyDome && SkyDome->GetStaticMesh())
	{
		const float Radius = FMath::Max(1.f, float(SkyDome->GetStaticMesh()->GetBounds().SphereRadius));
		SkyDome->SetWorldScale3D(FVector(DomeRadius / Radius));
	}
	if (Precipitation && !Precipitation->GetStaticMesh())
	{
		if (UStaticMesh* Plane = ParticleMesh.LoadSynchronous())
		{
			Precipitation->SetStaticMesh(Plane);
		}
	}
}

void ABiomeSkyEnvironment::EnsureMaterials()
{
	if (SkyDome && SkyDome->GetStaticMesh())
	{
		UMaterialInterface* Parent = SkyMaterial.LoadSynchronous();
		if (Parent && (!SkyMID || SkyMID->Parent != Parent))
		{
			SkyMID = UMaterialInstanceDynamic::Create(Parent, this);
		}
		if (SkyMID && SkyDome->GetMaterial(0) != SkyMID) SkyDome->SetMaterial(0, SkyMID);
		SkyDome->SetVisibility(SkyMID != nullptr);
	}
	if (Clouds)
	{
		UMaterialInterface* Parent = CloudMaterial.LoadSynchronous();
		if (Parent && (!CloudMID || CloudMID->Parent != Parent))
		{
			CloudMID = nullptr;
			PendingCloudMaterial = Parent;
		}
		if (CloudMID && Clouds->GetMaterial() != CloudMID) Clouds->SetMaterial(CloudMID);
	}
	if (Precipitation && Precipitation->GetStaticMesh())
	{
		UMaterialInterface* Parent = PrecipitationMaterial.LoadSynchronous();
		if (Parent && (!PrecipitationMID || PrecipitationMID->Parent != Parent))
		{
			PrecipitationMID = UMaterialInstanceDynamic::Create(Parent, this);
			Precipitation->SetMaterial(0, PrecipitationMID);
		}
	}
}

void ABiomeSkyEnvironment::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!GetWorld()) return;
	DeltaSeconds = FMath::Clamp(DeltaSeconds, 0.f, 0.5f);
	ClockSeconds += DeltaSeconds;
	UpdateClock(DeltaSeconds);
	UpdateWeather(DeltaSeconds);
	UpdateCelestial();
	UpdateLights();
	UpdateFogAndExposure();
	UpdateClouds(DeltaSeconds);
	UpdateSkyMaterial();
	UpdatePrecipitation(DeltaSeconds);
	UpdateLightning(DeltaSeconds);
	UpdateParameterCollection();
	bSnap = false;
}

// ---------------------------------------------------------------------------------------------------------------------
// Helpers

FVector ABiomeSkyEnvironment::ViewLocation() const
{
	const UWorld* World = GetWorld();
	if (World && World->IsGameWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			FVector Loc;
			FRotator Rot;
			PC->GetPlayerViewPoint(Loc, Rot);
			return Loc;
		}
	}
	if (World && World->ViewLocationsRenderedLastFrame.Num() > 0)
	{
		return World->ViewLocationsRenderedLastFrame[0];
	}
	return GetActorLocation();
}

FVector ABiomeSkyEnvironment::LocalToWorld(const FVector& NEU) const
{
	// World +X points at compass heading NorthOffset: north = cos(h) X - sin(h) Y, east = sin(h) X + cos(h) Y.
	const double H = FMath::DegreesToRadians(double(NorthOffset));
	const FVector North(FMath::Cos(H), -FMath::Sin(H), 0.0);
	const FVector East(FMath::Sin(H), FMath::Cos(H), 0.0);
	return North * NEU.X + East * NEU.Y + FVector::UpVector * NEU.Z;
}

float ABiomeSkyEnvironment::SkyClock() const
{
	// Kept under an hour so float maths in the shaders stays precise.
	return float(FMath::Fmod(ClockSeconds, 3600.0));
}

// ---------------------------------------------------------------------------------------------------------------------
// Time and weather

void ABiomeSkyEnvironment::UpdateClock(float DeltaSeconds)
{
	const UWorld* World = GetWorld();
	const bool bRun = bTimeRunning && (World->IsGameWorld() ? !World->IsPaused() : bRunInEditor);
	if (!bRun || DeltaSeconds <= 0.f) return;
	TimeOfDay += DeltaSeconds / FMath::Max(0.01f, SecondsPerGameHour);
	while (TimeOfDay >= 24.f)
	{
		TimeOfDay -= 24.f;
		const FDateTime Next = FDateTime(FMath::Clamp(Year, 1, 9998), FMath::Clamp(Month, 1, 12), FMath::Clamp(Day, 1, FDateTime::DaysInMonth(Year, Month))) + FTimespan::FromDays(1.0);
		Year = Next.GetYear();
		Month = Next.GetMonth();
		Day = Next.GetDay();
	}
}

void ABiomeSkyEnvironment::UpdateWeather(float DeltaSeconds)
{
	if (!bWeatherInitialised || Weather != AppliedWeather)
	{
		const bool bFirst = !bWeatherInitialised;
		SetWeather(Weather, (bFirst || bSnap || !GetWorld()->IsGameWorld()) ? 0.f : -1.f);
	}
	FBiomeSkyWeatherState Target = GetPreset(Weather);
	if (bOverrideCloudCover) Target.CloudCover = CloudCover;
	if (bSnap || BlendDuration <= 0.f)
	{
		CurrentWeather = Target;
		BlendTime = BlendDuration;
	}
	else
	{
		BlendTime = FMath::Min(BlendTime + DeltaSeconds, BlendDuration);
		CurrentWeather = FBiomeSkyWeatherState::Lerp(BlendFrom, Target, BlendTime / BlendDuration);
	}
	// The cover the clouds draw eases a little more (cover slider drags, override toggles).
	SmoothedCover = bSnap ? CurrentWeather.CloudCover : FMath::Lerp(SmoothedCover, CurrentWeather.CloudCover, 1.f - FMath::Exp(-DeltaSeconds * 0.8f));
	CloudCoverNow = SmoothedCover;
	const double Heading = FMath::DegreesToRadians(double(WindDirection));
	WindVelocity = LocalToWorld(FVector(FMath::Cos(Heading), FMath::Sin(Heading), 0.0)) * WindSpeed;
}

void ABiomeSkyEnvironment::UpdateCelestial()
{
	using namespace BiomeSkyAstronomy;
	const double Days = GetDaysSinceJ2000();
	const double Lat = FMath::DegreesToRadians(double(Latitude));
	LocalSiderealTime = FMath::Fmod(GreenwichSiderealTime(Days) + FMath::DegreesToRadians(double(Longitude)) + 4.0 * UE_DOUBLE_PI, 2.0 * UE_DOUBLE_PI);

	const FEcliptic SunE = Sun(Days);
	const FEquatorial SunQ = ToEquatorial(SunE, Days);
	SunDirection = LocalToWorld(HorizonDirection(LocalSiderealTime - SunQ.RightAscension, SunQ.Declination, Lat));
	SunElevation = float(FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(SunDirection.Z, -1.0, 1.0))));

	const FEcliptic MoonE = Moon(Days);
	const FEquatorial MoonQ = ToEquatorial(MoonE, Days);
	MoonDirection = LocalToWorld(HorizonDirection(LocalSiderealTime - MoonQ.RightAscension, MoonQ.Declination, Lat));
	MoonPhase = bOverrideMoonPhase ? FMath::Frac(MoonPhaseOverride) : float(BiomeSkyAstronomy::MoonPhase(SunE, MoonE));
	MoonIllumination = float(BiomeSkyAstronomy::MoonIllumination(MoonPhase));
	if (bOverrideMoonPhase)
	{
		// Keep the moon where it is but light it for the forced phase: put the sun's light at the right angle in the
		// shader by rotating the sun direction about the moon (only the material sees this; see UpdateSkyMaterial).
	}
	DayLight = FMath::Clamp((SunElevation + 6.f) / 14.f, 0.f, 1.f);
}

// ---------------------------------------------------------------------------------------------------------------------
// Lights, fog, exposure

void ABiomeSkyEnvironment::UpdateLights()
{
	if (!SunLight || !MoonLight) return;
	const float Overcast = SmoothedCover;
	const float Storm = CurrentWeather.Storm;
	if (bSnap || FVector::DotProduct(SunDirection, AppliedSunDir) < SkyStepCos)
	{
		AppliedSunDir = SunDirection;
		SunLight->SetWorldRotation((-SunDirection).Rotation());
	}
	// The sun keeps lighting the high air after it sets (the ground is in the planet's shadow through per-pixel
	// transmittance): that is the twilight glow, gone at -18 degrees. Thick cloud already shades the ground through the
	// cloud shadow map; this also takes out what a deck of storm cloud lets through.
	const float SunVisible = FMath::Clamp((SunElevation + 18.f) / 26.f, 0.f, 1.f);
	SunLight->SetIntensity(SunIntensity * SunVisible * (1.f - 0.3f * Overcast - 0.25f * Storm));

	if (bSnap || FVector::DotProduct(MoonDirection, AppliedMoonDir) < SkyStepCos)
	{
		AppliedMoonDir = MoonDirection;
		MoonLight->SetWorldRotation((-MoonDirection).Rotation());
	}
	// Moonlight falls off much faster than the lit fraction (a half moon gives about a tenth of the full moon's light:
	// the opposition surge, and a half disc is seen side-on), so ~ illumination^3.
	const float Up = FMath::Clamp(float(MoonDirection.Z) * 6.f, 0.f, 1.f);
	MoonLightAmount = FMath::Pow(MoonIllumination, 3.f) * Up * (1.f - 0.85f * Overcast);
	const float DayFactor = FMath::Clamp((SunElevation + 4.f) / 12.f, 0.f, 1.f);
	MoonLight->SetIntensity(MoonIntensity * (0.004f + MoonLightAmount) * (1.f - DayFactor));
}

void ABiomeSkyEnvironment::UpdateFogAndExposure()
{
	const float Overcast = SmoothedCover;
	const float Storm = FMath::Max(CurrentWeather.Storm, FMath::SmoothStep(0.85f, 0.97f, Overcast) * CurrentWeather.Convection);
	const float Wet = CurrentWeather.Precipitation;
	if (Fog)
	{
		// Visibility V (km) to fog density by Koschmieder (extinction 3.912 / V), in the fog's units; half of it in
		// light weather (any more veils the sky), all of it in a downpour. Lightning shows things a little farther.
		const float VisibilityM = FMath::Max(30.f, 1000.f * CurrentWeather.VisibilityKm * VisibilityScale * FMath::Lerp(1.f, 2.f, FlashLight));
		Fog->SetFogDensity(FMath::Lerp(0.5f, 1.f, FMath::SmoothStep(0.f, 0.55f, Wet)) * 39.12f / VisibilityM);
		// The murk hugs the ground (a taller haze veiled a storm deck into one flat grey sheet); in a real downpour the
		// rain fills the air up to the cloud base.
		Fog->SetFogHeightFalloff(FMath::Lerp(FMath::Lerp(0.2f, 0.3f, FMath::Max(Wet, Storm)), 0.15f, Wet * Wet));
		// The star dome is 40 km out: stop the fog short of it unless the rain hides the horizon anyway.
		Fog->SetFogCutoffDistance(Wet > 0.5f ? 0.f : DomeRadius * 0.75f);
		const float DayFactor = DayLight;
		const float TwilightHaze = (1.f - FMath::SmoothStep(0.f, 12.f, SunElevation)) * FMath::SmoothStep(-8.f, -2.f, SunElevation) * (1.f - 0.8f * Wet);
		const FLinearColor HazeTint = FMath::Lerp(FLinearColor::White, FLinearColor(0.7f, 0.11f, 0.03f), TwilightHaze);
		const FLinearColor Clear(0.6f, 0.72f, 0.85f);
		const FLinearColor Murk = FMath::Lerp(Clear, FLinearColor(0.42f, 0.45f, 0.48f), FMath::Max(FMath::Max(Wet, Storm), FMath::SmoothStep(0.6f, 1.f, 1.f - FMath::Min(CurrentWeather.VisibilityKm, 10.f) / 10.f)))
			* FMath::Lerp(1.f, 0.5f, Storm) * FMath::Lerp(1.f, 0.8f, Overcast);
		Fog->SetFogInscatteringColor(Murk * HazeTint * FMath::Lerp(0.04f, 1.f, DayFactor));
	}
	if (Exposure)
	{
		FPostProcessSettings& S = Exposure->Settings;
		S.bOverride_AutoExposureMinBrightness = bExposureFloor;
		S.bOverride_AutoExposureMaxBrightness = bExposureFloor;
		S.bOverride_AutoExposureBias = true;
		// The camera adapts like an eye, which would make a moonless night as bright as noon. Limit how far it opens:
		// below the floor the scene simply gets darker. The night limit closes in through twilight (full at -15 deg),
		// so the dusk glow stays; under a storm deck by day it keeps the gloom.
		const float Night = 1.f - FMath::SmoothStep(-15.f, -3.f, SunElevation);
		const float StormDark = FMath::Max(Storm, FMath::SmoothStep(0.6f, 0.95f, Overcast) * 0.5f);
		float Floor = FMath::Lerp(DayExposureFloor, StormExposureFloor, StormDark);
		Floor = FMath::Lerp(Floor, NightExposureFloor, Night);
		S.AutoExposureMinBrightness = Floor;
		S.AutoExposureMaxBrightness = 20.f;
		// A storm by day is a third of a stop to about a stop darker than a plain overcast.
		const float DayFactor = FMath::Clamp((SunElevation + 6.f) / 14.f, 0.f, 1.f);
		S.AutoExposureBias = ExposureBias - FMath::Lerp(0.3f, 0.9f, CurrentWeather.Storm) * StormDark * DayFactor;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Clouds and sky

void ABiomeSkyEnvironment::UpdateClouds(float DeltaSeconds)
{
	if (!Clouds) return;
	if (PendingCloudMaterial)
	{
		const FMaterialResource* Res = PendingCloudMaterial->GetMaterialResource(GMaxRHIShaderPlatform);
#if WITH_EDITOR
		const bool bCompiled = Res && Res->IsCompilationFinished() && Res->IsGameThreadShaderMapComplete();
		if (Res && !bCompiled && !Res->IsCompilationFinished())
		{
			// keep waiting
		}
#else
		const bool bCompiled = Res && Res->IsGameThreadShaderMapComplete();
#endif
		if (bCompiled)
		{
			CloudMID = UMaterialInstanceDynamic::Create(PendingCloudMaterial, this);
			Clouds->SetMaterial(CloudMID);
			PendingCloudMaterial = nullptr;
			UE_LOG(LogBiomeSky, Log, TEXT("Volumetric clouds on (%s)"), *CloudMID->Parent->GetName());
		}
		else if (Res)
		{
			PendingCloudMaterial->CacheShaders(EMaterialShaderPrecompileMode::Background);
		}
	}
	// The clouds drift with the wind aloft, a little faster than at the surface.
	const FVector2D Drift(WindVelocity.X * 140.f, WindVelocity.Y * 140.f);
	CloudOffset += Drift * DeltaSeconds;
	if (FMath::Abs(CloudOffset.X) > 2.0e7 || FMath::Abs(CloudOffset.Y) > 2.0e7) CloudOffset = FVector2D::ZeroVector;
	if (!CloudMID) return;
	const double Heading = FMath::DegreesToRadians(double(WindDirection));
	const FVector Flow = LocalToWorld(FVector(FMath::Cos(Heading), FMath::Sin(Heading), 0.0));
	CloudMID->SetScalarParameterValue(TEXT("Coverage"), SmoothedCover);
	CloudMID->SetScalarParameterValue(TEXT("SkyTime"), SkyClock());
	CloudMID->SetScalarParameterValue(TEXT("Density"), 0.018f * CloudDensityScale);
	CloudMID->SetVectorParameterValue(TEXT("CloudClimate"), FLinearColor(SmoothedCover, CurrentWeather.Convection, CurrentWeather.Precipitation, CurrentWeather.HighCloud));
	CloudMID->SetVectorParameterValue(TEXT("WeatherState"), FLinearColor(WindSpeed, float(CloudSeed % 1000003), SkyClock(), 1.f));
	CloudMID->SetVectorParameterValue(TEXT("WindOffset"), FLinearColor(float(CloudOffset.X), float(CloudOffset.Y), float(Flow.X), float(Flow.Y)));
	CloudMID->SetVectorParameterValue(TEXT("CloudLightning"), FLinearColor(float(FlashPosition.X), float(FlashPosition.Y), float(FlashPosition.Z), FlashLight));
}

void ABiomeSkyEnvironment::UpdateSkyMaterial()
{
	if (!SkyMID || !SkyDome) return;
	SkyDome->SetWorldLocation(ViewLocation());
	const float Overcast = SmoothedCover;
	const float Night = FMath::Clamp((-SunElevation - 2.f) / 12.f, 0.f, 1.f);
	const double Lat = FMath::DegreesToRadians(double(Latitude));
	SkyMID->SetVectorParameterValue(TEXT("SkyNorth"), V4(LocalToWorld(FVector(1, 0, 0))));
	SkyMID->SetVectorParameterValue(TEXT("SkyEast"), V4(LocalToWorld(FVector(0, 1, 0))));
	SkyMID->SetVectorParameterValue(TEXT("SkyFrame"), FLinearColor(float(FMath::Sin(Lat)), float(FMath::Cos(Lat)), float(LocalSiderealTime), Latitude >= 0.f ? 1.f : -1.f));
	SkyMID->SetScalarParameterValue(TEXT("StarIntensity"), FMath::Clamp(-SunElevation / 4.f, 0.f, 1.f) * (1.f - 0.85f * Overcast));
	SkyMID->SetScalarParameterValue(TEXT("StarBrightness"), StarBrightness);
	SkyMID->SetScalarParameterValue(TEXT("MilkyWayGain"), MilkyWayBrightness);
	SkyMID->SetScalarParameterValue(TEXT("SkyGrey"), FMath::SmoothStep(0.55f, 0.9f, Overcast));
	SkyMID->SetScalarParameterValue(TEXT("Meteors"), bShootingStars ? 1.f : 0.f);
	const float AuroraSeen = bAuroras ? FMath::Clamp(AuroraStrength, 0.f, 1.f) * Night * (1.f - 0.9f * Overcast) : 0.f;
	SkyMID->SetScalarParameterValue(TEXT("Aurora"), AuroraSeen);
	// How bright the night sky is sets how faint a star (and whether the Milky Way) one sees: twilight (30 at the end of
	// civil twilight, ~1 at -12, nothing at -18), the moonlight, the aurora's own glow. 1 = a full moon high and clear.
	const float Twilight = FMath::Min(30.f * FMath::Exp((SunElevation + 6.f) * 0.55f), 1.0e4f);
	SkyMID->SetScalarParameterValue(TEXT("SkyGlow"), Twilight + MoonLightAmount + 0.6f * AuroraSeen);
	SkyMID->SetVectorParameterValue(TEXT("MoonDir"), V4(MoonDirection));
	// The moon is lit by the sun, so the phase shows; a forced phase swings the lighting direction round the moon.
	FVector LitFrom = SunDirection;
	if (bOverrideMoonPhase)
	{
		const FVector M = MoonDirection;
		FVector Side = FVector::CrossProduct(FVector::CrossProduct(M, SunDirection), M).GetSafeNormal();
		if (Side.IsNearlyZero()) Side = FVector::CrossProduct(M, FVector::UpVector).GetSafeNormal();
		const float Elong = 2.f * PI * MoonPhase;   // 0 new: sun behind the moon; pi full: sun behind us
		LitFrom = (M * FMath::Cos(Elong) + Side * FMath::Sin(Elong)).GetSafeNormal();
	}
	SkyMID->SetVectorParameterValue(TEXT("SunDir"), V4(LitFrom));
	SkyMID->SetScalarParameterValue(TEXT("MoonScale"), MoonDrawScale);
	SkyMID->SetScalarParameterValue(TEXT("MoonDisk"), MoonBrightness * FMath::Lerp(1.f, 0.25f, DayLight));
	SkyMID->SetScalarParameterValue(TEXT("SkyTime"), SkyClock());
}

// ---------------------------------------------------------------------------------------------------------------------
// Rain, snow, lightning

void ABiomeSkyEnvironment::UpdatePrecipitation(float DeltaSeconds)
{
	if (!Precipitation || !PrecipitationMID) return;
	const float Amount = bPrecipitationParticles ? FMath::Clamp(CurrentWeather.Precipitation * 1.1f, 0.f, 1.f) * FMath::SmoothStep(0.55f, 0.8f, SmoothedCover) : 0.f;
	const int32 Wanted = Amount > 0.002f ? MaxPrecipitationParticles : 0;
	if (Wanted != ParticleCount)
	{
		ParticleCount = Wanted;
		Precipitation->ClearInstances();
		if (Wanted > 0)
		{
			// Every particle is placed by the material round the camera; the transforms only give the bounds.
			TArray<FTransform> Instances;
			Instances.Init(FTransform(FQuat::Identity, FVector::ZeroVector, FVector(PrecipitationBox.X / 50.f)), Wanted);
			Precipitation->AddInstances(Instances, false);
		}
	}
	Precipitation->SetVisibility(Wanted > 0);
	if (Wanted == 0) return;
	Precipitation->SetWorldLocation(ViewLocation());
	const float Snow = CurrentWeather.Snow;
	const float LightScale = FMath::Lerp(0.05f, 1.f, DayLight) * FMath::Lerp(1.f, 0.55f, CurrentWeather.Storm) + 3.f * FlashLight;
	const FLinearColor Tint = FMath::Lerp(FLinearColor(0.55f, 0.6f, 0.66f), FLinearColor(0.92f, 0.94f, 0.98f), Snow);
	PrecipitationMID->SetScalarParameterValue(TEXT("PrecipTime"), SkyClock());
	PrecipitationMID->SetScalarParameterValue(TEXT("PrecipDensity"), Amount);
	PrecipitationMID->SetScalarParameterValue(TEXT("PrecipSnow"), Snow);
	PrecipitationMID->SetScalarParameterValue(TEXT("PrecipStreak"), FMath::Clamp(DeltaSeconds, 1.f / 60.f, 1.f / 12.f));
	PrecipitationMID->SetVectorParameterValue(TEXT("PrecipWind"), FLinearColor(float(WindVelocity.X) * 100.f, float(WindVelocity.Y) * 100.f, 0.f, 0.f));
	PrecipitationMID->SetVectorParameterValue(TEXT("PrecipBox"), V4(PrecipitationBox));
	PrecipitationMID->SetVectorParameterValue(TEXT("PrecipLight"), Tint * (0.8f * LightScale));
}

void ABiomeSkyEnvironment::UpdateLightning(float DeltaSeconds)
{
	const float Storm = bLightning ? CurrentWeather.Storm * FMath::SmoothStep(0.75f, 0.92f, SmoothedCover) : 0.f;
	FlashLight = 0.f;
	if (FlashAge >= 0.f)
	{
		FlashAge += DeltaSeconds;
		if (FlashAge > FlashLife)
		{
			FlashAge = -1.f;
		}
		else
		{
			// A strike is a few return strokes tens of milliseconds apart, each a sharp flash that dies away.
			const float T = FlashAge / FlashLife;
			const float Strokes = FMath::Abs(FMath::Sin(T * PI * (2.f + 3.f * FlashPower))) * FMath::Exp(-T * 2.5f);
			FlashLight = FMath::Clamp(FlashPower * Strokes, 0.f, 1.f);
		}
	}
	else if (Storm > 0.01f && LightningPerMinute > 0.f && GetWorld()->IsGameWorld())
	{
		LightningTimer -= DeltaSeconds;
		if (LightningTimer <= 0.f)
		{
			// Strikes arrive at random (exponential gaps) at LightningPerMinute x storm.
			LightningTimer = -FMath::Loge(FMath::Max(1e-3f, LightningRandom.FRand())) * 60.f / (LightningPerMinute * Storm);
			const FVector View = ViewLocation();
			const float Angle = LightningRandom.FRandRange(0.f, 2.f * PI);
			const float Range = LightningRandom.FRandRange(800.f, 7000.f) * 100.f;
			FlashPosition = FVector(View.X + FMath::Cos(Angle) * Range, View.Y + FMath::Sin(Angle) * Range, GetActorLocation().Z + LightningRandom.FRandRange(1500.f, 4000.f) * 100.f);
			FlashLife = LightningRandom.FRandRange(0.25f, 0.7f);
			FlashPower = LightningRandom.FRandRange(0.35f, 1.f);
			FlashAge = 0.f;
		}
	}
	if (LightningLight)
	{
		LightningLight->SetVisibility(FlashLight > 0.001f);
		if (FlashLight > 0.001f)
		{
			LightningLight->SetWorldLocation(FlashPosition);
			LightningLight->SetIntensity(4.0e7f * FlashLight);
		}
	}
}

void ABiomeSkyEnvironment::UpdateParameterCollection()
{
	UMaterialParameterCollection* Collection = ParameterCollection.LoadSynchronous();
	UWorld* World = GetWorld();
	if (!Collection || !World) return;
	UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(Collection);
	if (!Instance) return;
	const double Heading = FMath::DegreesToRadians(double(WindDirection));
	Instance->SetVectorParameterValue(TEXT("SunDirection"), V4(SunDirection, SunElevation));
	Instance->SetVectorParameterValue(TEXT("MoonDirection"), V4(MoonDirection, MoonPhase));
	Instance->SetVectorParameterValue(TEXT("Wind"), FLinearColor(float(WindVelocity.X), float(WindVelocity.Y), WindSpeed, float(FMath::RadiansToDegrees(Heading))));
	Instance->SetVectorParameterValue(TEXT("SkyState"), FLinearColor(DayLight, SmoothedCover, CurrentWeather.Precipitation, CurrentWeather.Storm));
	Instance->SetVectorParameterValue(TEXT("Moonlight"), FLinearColor(MoonLightAmount, MoonIllumination, FlashLight, CurrentWeather.Snow));
	Instance->SetScalarParameterValue(TEXT("SkyTime"), SkyClock());
}
