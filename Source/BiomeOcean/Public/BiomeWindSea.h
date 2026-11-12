#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Tasks/Task.h"
#include "BiomeOceanModel.h"
#include "BiomeWindSea.generated.h"

class UTexture2D;
class UMaterialInstanceDynamic;

/**
 * The wind sea as Tessendorf FFT cascades (1543 m, 251 m and 41 m tiles, 256^2 each), evaluated on worker threads every
 * frame. Gameplay samples the same displacement the material draws. Textures per cascade, with box-filtered mips:
 * A (Dx, Dy, H cm, whitecap foam), B (Sx, Sy, Sx^2, Sy^2), C (Dxx, Dyy, Dxy). Without textures (a dedicated server) only
 * the displacement is computed.
 */
UCLASS(Transient)
class BIOMEOCEAN_API UBiomeWindSea : public UObject
{
	GENERATED_BODY()
public:
	void Configure(uint32 Seed, int32 CascadeCount, bool bInTextures);
	bool IsActive() const { return Cascades.Num() > 0; }
	int32 GetCascadeCount() const { return Cascades.Num(); }
	/** Collects the finished update (if any) and launches the next for Time + DeltaSeconds. */
	void Tick(float DeltaSeconds, double Time, const FBiomeSeaCondition& Condition, float WhitecapCover, float FoamLifetime);
	void Bind(UMaterialInstanceDynamic* Material) const;
	/** Blocks until the update in flight is done (tests, shutdown). */
	void Flush();
	TSharedPtr<const BiomeOcean::FField, ESPMode::ThreadSafe> GetField() const { return Field; }
	double GetSlopeVariance() const;
	double GetHeightVariance() const;
	float GetChoppiness() const { return Chop; }
	virtual void BeginDestroy() override;

private:
	struct FResult
	{
		double Time = 0.0;
		TSharedPtr<TArray<FVector3f>, ESPMode::ThreadSafe> Disp[BiomeOcean::MaxCascades];
		TArray<FFloat16Color> A[BiomeOcean::MaxCascades], B[BiomeOcean::MaxCascades], C[BiomeOcean::MaxCascades];
		double HeightVariance[BiomeOcean::MaxCascades] = {};
		double SlopeVariance[BiomeOcean::MaxCascades][4] = {};
	};
	void Collect();

	TArray<BiomeOcean::FCascade> Cascades;
	UPROPERTY() TArray<TObjectPtr<UTexture2D>> Textures;   // A0 B0 C0 A1 B1 C1 ...
	UE::Tasks::TTask<FResult> Pending;
	bool bPending = false;
	bool bTextures = true;
	FBiomeSeaCondition Shaped;
	bool bShaped = false;
	double ShapedAt = -1e9;
	double LastWhen = 0.0;
	float Chop = 1.f;
	int32 Updates = 0;
	double HeightVariance[BiomeOcean::MaxCascades] = {};
	double SlopeVariance[BiomeOcean::MaxCascades][4] = {};
	TSharedPtr<const BiomeOcean::FField, ESPMode::ThreadSafe> Field;
};
