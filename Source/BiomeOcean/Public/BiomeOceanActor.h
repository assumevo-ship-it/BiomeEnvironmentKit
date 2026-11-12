#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/EngineTypes.h"
#include "BiomeOceanModel.h"
#include "BiomeOceanActor.generated.h"

class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTexture2D;
class UBiomeWindSea;

UENUM(BlueprintType)
enum class EBiomeOceanQuality : uint8
{
	/** Follows the Effects scalability group (sg.EffectsQuality). */
	Auto,
	Low,
	Medium,
	High,
	Epic,
};

/**
 * A realistic open ocean you drop into a level: one actor, no other setup. Its own Z is the sea level.
 *
 * The surface is a camera-following grid (fine under the camera, coarse towards the 20 km horizon) displaced on the GPU by
 * five Gerstner swells plus a wind sea of FFT cascades (JONSWAP spectrum, Mitsuyasu spreading) grown from the wind speed,
 * direction, fetch and duration. Whitecaps form where the crests are most compressed; over a baked shore field the swells
 * shoal, break and wash up the beach. Water height, normal and velocity queries come from the same model on the CPU.
 * See Docs/Ocean.md.
 */
UCLASS(hidecategories = (Collision, Physics, Input, LOD, Cooking, Replication, HLOD, Networking), meta = (DisplayName = "Biome Ocean"))
class BIOMEOCEAN_API ABiomeOcean : public AActor
{
	GENERATED_BODY()

public:
	ABiomeOcean();

	// ---------------------------------------------------------------- Wind
	/** Wind speed 10 m above the sea (m/s). 3 light air, 8 fresh breeze, 14 near gale, 20 gale, 28 storm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Interp, Category = "Ocean|Wind", meta = (ClampMin = "0", ClampMax = "40", UIMax = "32"))
	float WindSpeed = 8.f;
	/** The direction the wind blows towards, as a yaw in degrees (0 = +X, 90 = +Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Interp, Category = "Ocean|Wind")
	float WindDirection = 0.f;
	/** Open water the wind has blown over (km). Short fetch: short, steep chop; 300+ km: an open-ocean sea. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind", meta = (ClampMin = "0.1", UIMax = "1000"))
	float FetchKm = 300.f;
	/** How long the wind has blown (hours); 0 = long enough to be fully grown for the fetch. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind", meta = (ClampMin = "0", UIMax = "48"))
	float WindDurationHours = 0.f;
	/** Let the sea grow and age with time instead of jumping to the sea of the current wind: a rising wind builds the sea
	 *  over minutes, a falling or turning wind leaves its old sea running as swell (crossed seas after a front). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind")
	bool bGrowSeaOverTime = false;
	/** Sea seconds per game second while growing (400: a gale's day-long sea builds in about two minutes). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind", meta = (EditCondition = "bGrowSeaOverTime", ClampMin = "1", UIMax = "2000"))
	float SeaGrowthTimeScale = 400.f;
	/** Optional actor implementing IBiomeWindSource (e.g. the BiomeSky actor) that supplies speed and direction. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind")
	TObjectPtr<AActor> WindSource;
	/** With no Wind Source set, use the first actor in the level that implements IBiomeWindSource. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Wind")
	bool bFindWindSourceAutomatically = true;

	// ---------------------------------------------------------------- Swell
	/** Scale of the five long swells from distant storms (0 none, 1 typical ocean swell, ~1 m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Interp, Category = "Ocean|Swell", meta = (ClampMin = "0", UIMax = "3"))
	float SwellAmount = 1.f;
	/** Yaw (degrees) the swells run towards. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell")
	float SwellDirection = 0.f;
	/** Also scale the swells with the weather (calm 0.45 .. storm 1.8). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell")
	bool bSwellFollowsWind = true;
	/** A second, older sea from another direction (significant height, m): a crossed sea. 0 = none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell", meta = (ClampMin = "0", UIMax = "8"))
	float CrossSeaHeight = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell", meta = (ClampMin = "3", UIMax = "18"))
	float CrossSeaPeriod = 9.f;
	/** Yaw (degrees) the cross sea runs towards. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell")
	float CrossSeaDirection = 90.f;
	/** Random draw of the waves (same seed, same sea on every machine). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Swell")
	int32 Seed = 1234;

	// ---------------------------------------------------------------- Foam
	/** Whitecap amount: 0 none, 1 calibrated to the wind (~2% of the sea in a fresh breeze, a quarter in a gale). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Interp, Category = "Ocean|Foam", meta = (ClampMin = "0", UIMax = "3"))
	float WhitecapAmount = 1.f;
	/** Seconds a whitecap's foam takes to fade (longer in strong winds automatically). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Foam", meta = (ClampMin = "0.3", UIMax = "15"))
	float FoamLifetime = 3.f;
	/** Brightness of breaker and swash foam on the shore field. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Foam", meta = (ClampMin = "0", UIMax = "2"))
	float ShoreFoam = 1.f;

	// ---------------------------------------------------------------- Look (pushed to the material instance)
	/** Single Layer Water material (generated by Tools/ocean/build_ocean_assets.py). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ocean|Look")
	TObjectPtr<UMaterialInterface> OceanMaterial;
	/** Absorption of open water per metre (RGB): red goes first, so the deep sea is blue. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look")
	FLinearColor DeepAbsorption = FLinearColor(0.45f, 0.065f, 0.022f);
	/** Scattering of open water per metre: the brightness and hue of the water body (sapphire). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look")
	FLinearColor DeepScattering = FLinearColor(0.0006f, 0.0014f, 0.0025f);
	/** Over shallow sand (from the shore field): clear water that turns turquoise. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look")
	FLinearColor ShallowAbsorption = FLinearColor(0.30f, 0.045f, 0.028f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look")
	FLinearColor ShallowScattering = FLinearColor(0.005f, 0.026f, 0.022f);
	/** Roughness of the calm surface before the unresolved wave slopes are added. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look", meta = (ClampMin = "0.01", ClampMax = "0.5"))
	float WaterRoughness = 0.06f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Look")
	FLinearColor FoamColor = FLinearColor(0.85f, 0.88f, 0.87f);

	// ---------------------------------------------------------------- Under water (a post-process while the view is below the waves)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Underwater")
	bool bUnderwaterView = true;
	/** Post-process material (generated by Tools/ocean/build_ocean_assets.py: M_BiomeUnderwater). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ocean|Underwater")
	TObjectPtr<UMaterialInterface> UnderwaterMaterial;
	/** How fast light is lost per metre of water (RGB; absorption plus scattering out of the ray). Clear tropical water
	 *  sees ~30 m; coastal green water ~8 m (try 0.6, 0.18, 0.22). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Underwater")
	FLinearColor UnderwaterExtinction = FLinearColor(0.40f, 0.075f, 0.045f);
	/** Colour of the water's own glow (sunlight scattered towards the eye) just under the surface at noon; it dims with
	 *  the camera's depth through the same extinction and with the sun's height. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Underwater")
	FLinearColor UnderwaterLight = FLinearColor(0.10f, 0.42f, 0.52f);

	// ---------------------------------------------------------------- Quality
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Quality")
	EBiomeOceanQuality Quality = EBiomeOceanQuality::Auto;
	/** Draw the ocean in the editor viewports (it then follows the editor camera). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Quality")
	bool bPreviewInEditor = true;
	/** Use the replicated server clock (AGameStateBase) so every machine sees the same crest. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Quality")
	bool bUseServerTime = true;

	// ---------------------------------------------------------------- Shore
	/** Half the side of the square baked round the actor (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Shore", meta = (ClampMin = "10000"))
	float ShoreBakeHalfSize = 300000.f;
	/** Texels along a side (power of two; 512 over 6 km: about 12 m per texel). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Shore", meta = (ClampMin = "64", ClampMax = "2048"))
	int32 ShoreBakeResolution = 512;
	/** Water deeper than this (m) counts as open sea; traces reaching no ground also do. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Shore", meta = (ClampMin = "5"))
	float ShoreMaxDepth = 60.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ocean|Shore")
	TEnumAsByte<ECollisionChannel> ShoreTraceChannel = ECC_WorldStatic;
	/** (min X cm, min Y cm, span cm, resolution) of the baked field; resolution 0 = no shore field. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Ocean|Shore")
	FVector4 ShoreBounds = FVector4(0, 0, 1, 0);
	/** Per texel: signed distance to the waterline (m), depth (m), direction to the shore (X, Y). */
	UPROPERTY()
	TArray<float> ShoreData;

	/** Traces the level's ground round the actor (landscapes, meshes with collision) and bakes the shore field: depth,
	 *  distance to the waterline and the direction to it. Waves then shoal, break and wash up wherever the bed rises. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Ocean|Shore")
	void BakeShoreField();
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Ocean|Shore")
	void ClearShoreField();

	// ---------------------------------------------------------------- State
	/** The sea the wind has raised (read it, or set it with SetSeaCondition). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Ocean|State")
	FBiomeSeaCondition SeaCondition;

	// ---------------------------------------------------------------- Queries
	/** Absolute Z of the water surface above (or below) a location. */
	UFUNCTION(BlueprintPure, Category = "Ocean")
	float GetWaterHeightAt(const FVector& Location) const;
	/** Surface height, upward normal and the water's velocity (cm/s) there: for buoyancy, swimming and spray. */
	UFUNCTION(BlueprintCallable, Category = "Ocean")
	void GetWaterSurfaceAt(const FVector& Location, float& Height, FVector& Normal, FVector& Velocity) const;
	/** True below the surface; Depth (cm) is how far under it (negative above). */
	UFUNCTION(BlueprintPure, Category = "Ocean")
	bool IsUnderwater(const FVector& Location, float& Depth) const;
	/** Significant wave height Hs (m) of the whole sea, swells included. */
	UFUNCTION(BlueprintPure, Category = "Ocean")
	float GetSignificantWaveHeight() const;
	/** Displacement of the water particle resting under Location (cm, relative to sea level): what the GPU draws there. */
	UFUNCTION(BlueprintPure, Category = "Ocean")
	FVector GetWaveDisplacementAt(const FVector& Location) const;
	/** The wind the ocean is using now (m/s, towards). */
	UFUNCTION(BlueprintPure, Category = "Ocean")
	FVector GetWindVelocity() const;
	/** Sets the sea at once (no growth), e.g. from a save game. */
	UFUNCTION(BlueprintCallable, Category = "Ocean")
	void SetSeaCondition(const FBiomeSeaCondition& Condition);
	/** The ocean in this world (the first one), or null. */
	UFUNCTION(BlueprintPure, Category = "Ocean", meta = (WorldContext = "WorldContextObject"))
	static ABiomeOcean* FindOcean(const UObject* WorldContextObject);

	/** C++: heights of many points at one time (e.g. a hull's sample points). */
	void GetWaterHeights(TArrayView<const FVector2D> PointsXY, TArrayView<float> OutZ) const;
	float GetOceanTime() const;
	BiomeOcean::FShore SampleShore(const FVector2D& XYcm) const;
	const BiomeOcean::FSeaState& GetSeaState() const { return Sea; }
	UMaterialInstanceDynamic* GetMaterialInstance() const { return MID; }
	/** Blocks until the wind sea's update in flight is done (tests). */
	void FlushWindSea();

	virtual void Tick(float DeltaSeconds) override;
	virtual bool ShouldTickIfViewportsOnly() const override;
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif

private:
	struct FTier { int32 Level; int32 HalfRes; float FirstStep; int32 Cascades; };
	FTier CurrentTier() const;
	bool BuildGrid(const FTier& Tier);
	void EnsureMaterial();
	void UpdateWind(float DeltaSeconds);
	void UpdateSea(float DeltaSeconds);
	void UpdateVisuals();
	void RebuildShoreTexture();
	FVector2D WindVector() const;
	bool GetViewLocation(FVector& Out) const;

	UPROPERTY(VisibleAnywhere, Category = "Ocean")
	TObjectPtr<UStaticMeshComponent> Surface;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MID;
	UPROPERTY(VisibleAnywhere, Category = "Ocean")
	TObjectPtr<class UPostProcessComponent> Underwater;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> UnderwaterMID;
	TWeakObjectPtr<class UDirectionalLightComponent> SunForUnderwater;
	void UpdateUnderwater(const FVector& View);
	UPROPERTY(Transient) TObjectPtr<UBiomeWindSea> WindSea;
	UPROPERTY(Transient) TObjectPtr<UTexture2D> ShoreTexture;
	UPROPERTY(Transient) TObjectPtr<AActor> FoundWindSource;

	BiomeOcean::FSeaState Sea;
	FVector2D CurrentWind = FVector2D(8.0, 0.0);
	bool bWindReady = false;
	bool bConditionReady = false;
	int32 GridTier = -1;
	int32 GridHalfRes = 256;
	float GridFirstStep = 30.f;
	float GridGrowth = 1.03f;
	int32 SeaCascades = -1;
	float SearchCooldown = 0.f;
	FBiomeSeaCondition LastTarget;
};
