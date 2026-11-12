#include "BiomeWindSea.h"
#include "BiomeOcean.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TextureResource.h"

namespace
{
	UTexture2D* CreateCascadeTexture(int32 N)
	{
		UTexture2D* Texture = UTexture2D::CreateTransient(N, N, PF_FloatRGBA);
		if (!Texture) return nullptr;
		FTexturePlatformData* Data = Texture->GetPlatformData();
		for (int32 Width = N / 2; Width >= 1; Width /= 2)
		{
			FTexture2DMipMap* Mip = new FTexture2DMipMap(Width, Width, 1);
			Data->Mips.Add(Mip);
			Mip->BulkData.Lock(LOCK_READ_WRITE);
			FMemory::Memzero(Mip->BulkData.Realloc(int64(Width) * Width * sizeof(FFloat16Color)), int64(Width) * Width * sizeof(FFloat16Color));
			Mip->BulkData.Unlock();
		}
		Texture->SRGB = false;
		Texture->Filter = TF_Trilinear;
		Texture->AddressX = TA_Wrap;
		Texture->AddressY = TA_Wrap;
		Texture->NeverStream = true;
		Texture->UpdateResource();
		return Texture;
	}

	void Upload(UTexture2D* Texture, const TArray<FFloat16Color>& Texels, int32 N)
	{
		if (!Texture || Texels.Num() == 0 || !Texture->GetResource()) return;
		FFloat16Color* Block = (FFloat16Color*)FMemory::Malloc(Texels.Num() * sizeof(FFloat16Color));
		FMemory::Memcpy(Block, Texels.GetData(), Texels.Num() * sizeof(FFloat16Color));
		int32 Offset = 0, Mip = 0;
		const int32 MipCount = Texture->GetPlatformData()->Mips.Num();
		for (int32 Width = N; Width >= 1 && Mip < MipCount; Width /= 2, ++Mip)
		{
			FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, Width, Width);
			const bool bLast = Width == 1 || Mip == MipCount - 1;
			Texture->UpdateTextureRegions(Mip, 1, Region, Width * sizeof(FFloat16Color), sizeof(FFloat16Color), (uint8*)(Block + Offset),
				[Block, bLast](uint8*, const FUpdateTextureRegion2D* Done) { delete Done; if (bLast) FMemory::Free(Block); });
			Offset += Width * Width;
		}
	}
}

void UBiomeWindSea::Configure(uint32 Seed, int32 CascadeCount, bool bInTextures)
{
	Flush();
	Cascades.Reset();
	Textures.Reset();
	Field.Reset();
	Updates = 0;
	bTextures = bInTextures;
	bShaped = false;
	const int32 Count = FMath::Clamp(CascadeCount, 1, BiomeOcean::MaxCascades);
	for (int32 Index = 0; Index < Count; ++Index)
	{
		BiomeOcean::InitCascade(Cascades.AddDefaulted_GetRef(), Index, Count, Seed + 7919u * Index);
		if (bTextures)
		{
			for (int32 Which = 0; Which < 3; ++Which) Textures.Add(CreateCascadeTexture(BiomeOcean::FFTSize));
		}
	}
	UE_LOG(LogBiomeOcean, Log, TEXT("BiomeOcean: wind sea of %d FFT cascades (%d^2)%s"), Count, BiomeOcean::FFTSize, bTextures ? TEXT("") : TEXT(", no textures"));
}

void UBiomeWindSea::Flush()
{
	if (bPending)
	{
		Pending.Wait();
		Collect();
	}
}

void UBiomeWindSea::Collect()
{
	FResult Result = Pending.GetResult();
	bPending = false;
	TSharedPtr<BiomeOcean::FField, ESPMode::ThreadSafe> Next = MakeShared<BiomeOcean::FField, ESPMode::ThreadSafe>();
	Next->Time = Result.Time;
	Next->BeforeTime = Field.IsValid() ? Field->Time : Result.Time;
	Next->Count = Cascades.Num();
	for (int32 Index = 0; Index < Cascades.Num(); ++Index)
	{
		BiomeOcean::FPatch& P = Next->Patches[Index];
		P.PatchCm = Cascades[Index].PatchM * 100.0;
		P.Cos = float(FMath::Cos(Cascades[Index].RotationRad));
		P.Sin = float(FMath::Sin(Cascades[Index].RotationRad));
		P.Now = Result.Disp[Index];
		P.Before = Field.IsValid() && Index < Field->Count ? Field->Patches[Index].Now : nullptr;
		if (bTextures && Textures.IsValidIndex(Index * 3 + 2))
		{
			Upload(Textures[Index * 3 + 0], Result.A[Index], BiomeOcean::FFTSize);
			Upload(Textures[Index * 3 + 1], Result.B[Index], BiomeOcean::FFTSize);
			Upload(Textures[Index * 3 + 2], Result.C[Index], BiomeOcean::FFTSize);
		}
		HeightVariance[Index] = Result.HeightVariance[Index];
		for (int32 L = 0; L < 4; ++L) SlopeVariance[Index][L] = Result.SlopeVariance[Index][L];
	}
	Field = Next;
	++Updates;
}

void UBiomeWindSea::Tick(float DeltaSeconds, double Time, const FBiomeSeaCondition& Condition, float WhitecapCover, float FoamLifetime)
{
	if (!IsActive()) return;
	if (bPending)
	{
		if (!Pending.IsCompleted()) return;   // never block the game thread: skip a frame instead
		Collect();
	}
	// Reshape (a few ms per cascade, on the worker) only for a real change, at most four times a second while the sea grows.
	const bool bChanged = !bShaped || Condition.Generation != Shaped.Generation
		|| FMath::Abs(Condition.WindU - Shaped.WindU) > 0.05f
		|| FMath::Abs(FMath::Loge(FMath::Max(Condition.Fetch, 1.f) / FMath::Max(Shaped.Fetch, 1.f))) > 0.01f
		|| FMath::Abs(FMath::FindDeltaAngleDegrees(Condition.HeadingDeg, Shaped.HeadingDeg)) > 0.3f
		|| FMath::Abs(Condition.OldVariance - Shaped.OldVariance) > 0.01f * FMath::Max(Shaped.OldVariance, 0.05f)
		|| FMath::Abs(Condition.OldPeriod - Shaped.OldPeriod) > 0.05f
		|| FMath::Abs(FMath::FindDeltaAngleDegrees(Condition.OldHeadingDeg, Shaped.OldHeadingDeg)) > 0.5f;
	const bool bReshape = !bShaped || Condition.Generation != Shaped.Generation || (bChanged && FMath::Abs(Time - ShapedAt) > 0.25);
	if (bReshape)
	{
		Shaped = Condition;
		bShaped = true;
		ShapedAt = Time;
	}
	Chop = BiomeOcean::Choppiness(Shaped.WindU);
	const double When = Time + DeltaSeconds;
	// Foam decays over the game time between this update and the last.
	const float Step = float(FMath::Clamp(When - LastWhen, 0.0, 0.5));
	LastWhen = When;
	const float FoamKeep = FMath::Exp(-Step / FMath::Max(0.2f, FoamLifetime));
	TArray<BiomeOcean::FCascade>* Source = &Cascades;
	const FBiomeSeaCondition ShapeFor = Shaped;
	const float Lambda = Chop;
	const bool bGPU = bTextures;
	const float Cover = WhitecapCover;
	Pending = UE::Tasks::Launch(UE_SOURCE_LOCATION, [Source, When, ShapeFor, bReshape, Lambda, bGPU, Cover, FoamKeep]()
	{
		using namespace BiomeOcean;
		FResult Out;
		Out.Time = When;
		for (int32 Index = 0; Index < Source->Num(); ++Index)
		{
			FCascade& Cascade = (*Source)[Index];
			if (bReshape) ShapeCascade(Cascade, ShapeFor);
			Out.HeightVariance[Index] = Cascade.HeightVariance;
			for (int32 L = 0; L < 4; ++L) Out.SlopeVariance[Index][L] = Cascade.SlopeVariance[L];
			EvaluateCascade(Cascade, When, Lambda, Cover, FoamKeep, Out.Disp[Index], bGPU ? &Out.A[Index] : nullptr,
				bGPU ? &Out.B[Index] : nullptr, bGPU ? &Out.C[Index] : nullptr);
		}
		return Out;
	});
	bPending = true;
}

double UBiomeWindSea::GetSlopeVariance() const
{
	double Sum = 0.0;
	for (int32 Index = 0; Index < Cascades.Num(); ++Index) Sum += SlopeVariance[Index][0];
	return Sum;
}

double UBiomeWindSea::GetHeightVariance() const
{
	double Sum = 0.0;
	for (int32 Index = 0; Index < Cascades.Num(); ++Index) Sum += HeightVariance[Index];
	return Sum;
}

void UBiomeWindSea::Bind(UMaterialInstanceDynamic* Material) const
{
	if (!Material) return;
	static const FName A[3] = { TEXT("WindA0"), TEXT("WindA1"), TEXT("WindA2") };
	static const FName B[3] = { TEXT("WindB0"), TEXT("WindB1"), TEXT("WindB2") };
	static const FName C[3] = { TEXT("WindC0"), TEXT("WindC1"), TEXT("WindC2") };
	static const FName Info[3] = { TEXT("WindInfo0"), TEXT("WindInfo1"), TEXT("WindInfo2") };
	static const FName Var[3] = { TEXT("WindVar0"), TEXT("WindVar1"), TEXT("WindVar2") };
	for (int32 Index = 0; Index < BiomeOcean::MaxCascades; ++Index)
	{
		if (!Cascades.IsValidIndex(Index) || !bTextures || Updates == 0)
		{
			Material->SetVectorParameterValue(Info[Index], FLinearColor(1.f, 0.f, 1.f, 0.f));
			continue;
		}
		const BiomeOcean::FCascade& Cascade = Cascades[Index];
		Material->SetTextureParameterValue(A[Index], Textures[Index * 3 + 0]);
		Material->SetTextureParameterValue(B[Index], Textures[Index * 3 + 1]);
		Material->SetTextureParameterValue(C[Index], Textures[Index * 3 + 2]);
		// (tile cm, turn rad, texel cm, on) and the slope variance mips 0-3 keep.
		Material->SetVectorParameterValue(Info[Index], FLinearColor(float(Cascade.PatchM * 100.0), float(Cascade.RotationRad),
			float(Cascade.PatchM * 100.0 / BiomeOcean::FFTSize), 1.f));
		Material->SetVectorParameterValue(Var[Index], FLinearColor(float(SlopeVariance[Index][0]), float(SlopeVariance[Index][1]),
			float(SlopeVariance[Index][2]), float(SlopeVariance[Index][3])));
	}
}

void UBiomeWindSea::BeginDestroy()
{
	if (bPending) { Pending.Wait(); bPending = false; }
	Super::BeginDestroy();
}
