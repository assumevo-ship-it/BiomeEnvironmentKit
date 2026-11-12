#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BiomeSkyEnvironment.generated.h"

class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UVolumetricCloudComponent;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UPostProcessComponent;
class UPointLightComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMaterialParameterCollection;
class UStaticMesh;

/** Weather presets. Each sets cloud cover, convection, rain, high ice cloud, visibility and precipitation. */
UENUM(BlueprintType)
enum class EBiomeSkyWeather : uint8
{
	Clear,
	Fair       UMETA(ToolTip = "Fair-weather cumulus with blue sky between them."),
	Overcast,
	Rain,
	Storm      UMETA(ToolTip = "Thunderstorm: towering cloud, a dark rain deck, heavy rain and lightning."),
	Snow,
	Fog
};

UENUM(BlueprintType)
enum class EBiomeSkyPrecipitation : uint8
{
	None,
	Rain,
	Snow
};

/** The air mass a weather preset stands for. Blended over WeatherBlendSeconds when the weather changes. */
USTRUCT(BlueprintType)
struct BIOMESKY_API FBiomeSkyWeatherState
{
	GENERATED_BODY()

	/** Fraction of the sky under low cloud, 0-1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float CloudCover = 0.36f;
	/** How tall the clouds grow, 0 (flat fair-weather cumulus) to 1 (cumulonimbus with an anvil). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float Convection = 0.12f;
	/** How much the low cloud is a raining stratiform deck, 0-1; also how hard it rains or snows. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float Precipitation = 0.f;
	/** Cirrus / high ice cloud, 0-1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float HighCloud = 0.22f;
	/** Visibility along the ground in kilometres (sets the height fog by Koschmieder's law). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0.05))
	float VisibilityKm = 25.f;
	/** 0-1 thunderstorm: darker cloud bases, exposure, lightning. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float Storm = 0.f;
	/** 0 rain, 1 snow (blends the falling particles). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = 0, ClampMax = 1))
	float Snow = 0.f;

	static FBiomeSkyWeatherState Lerp(const FBiomeSkyWeatherState& A, const FBiomeSkyWeatherState& B, float T);
};

/**
 * A complete physical sky in one actor: the sun and the moon where they really stand for a latitude, date and time,
 * the stars and the Milky Way turning about the celestial pole, auroras and shooting stars, volumetric clouds and
 * fog that follow the weather, rain and snow round the camera, lightning in storms, and an exposure floor that keeps
 * nights and storms dark.
 *
 * Drop it into a level that has no other sun, sky light, atmosphere, height fog or volumetric cloud. Every component
 * it needs is its own; nothing is spawned or found elsewhere. It does not replicate: a networked game sets the same
 * time, date and weather on every machine (SetTimeOfDay, SetWeather...).
 *
 * Other systems can read it without linking this module:
 *  - the material parameter collection MPC_BiomeSky (SunDirection, MoonDirection, Wind, SkyState: see Docs/Sky.md),
 *  - or the actor's read-only properties by name (SunDirection, MoonDirection, MoonPhase, WindVelocity, CloudCoverNow,
 *    DayLight, ...), found on the first actor tagged "BiomeSky", through UObject reflection.
 */
UCLASS(Blueprintable, HideCategories = (Collision, Physics, Input, HLOD, Cooking, Replication, Networking, LOD, Navigation))
class BIOMESKY_API ABiomeSkyEnvironment : public AActor
{
	GENERATED_BODY()

public:
	ABiomeSkyEnvironment();

	// ---- Place and time ------------------------------------------------------------------------------------------

	/** Geographic latitude in degrees (+ north). Sets the sun's path, the pole the stars turn about and the aurora side. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = -89.9, ClampMax = 89.9))
	float Latitude = 17.f;
	/** Geographic longitude in degrees (+ east). Only matters for the moon and stars when TimeOfDay is a zone time. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = -180, ClampMax = 180))
	float Longitude = -64.f;
	/** Compass heading of world +X, in degrees clockwise from north (0: +X is north, +Y east). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = -360, ClampMax = 360))
	float NorthOffset = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = 1, ClampMax = 9998))
	int32 Year = 2026;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = 1, ClampMax = 12))
	int32 Month = 4;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = 1, ClampMax = 31))
	int32 Day = 1;
	/** Clock time in hours (0-24). With bSolarTime the sun is highest near 12. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Interp, Category = "Sky|Place and Time", meta = (ClampMin = 0, ClampMax = 24, UIMin = 0, UIMax = 24))
	float TimeOfDay = 10.f;
	/** TimeOfDay is local mean solar time (UTC offset = longitude / 15). Off: it is a zone time at UtcOffsetHours. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time")
	bool bSolarTime = true;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (EditCondition = "!bSolarTime", ClampMin = -14, ClampMax = 14))
	float UtcOffsetHours = -4.f;
	/** Real seconds per game hour while the clock runs (60: a 24-minute day; 3600: real time). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time", meta = (ClampMin = 0.01))
	float SecondsPerGameHour = 60.f;
	/** The clock runs during play (the date rolls over at midnight). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time")
	bool bTimeRunning = true;
	/** The clock also runs in the editor viewport (for previewing a day). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Place and Time")
	bool bRunInEditor = false;

	// ---- Weather -------------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather")
	EBiomeSkyWeather Weather = EBiomeSkyWeather::Fair;
	/** Use CloudCover instead of the preset's cover. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (InlineEditConditionToggle))
	bool bOverrideCloudCover = false;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (EditCondition = "bOverrideCloudCover", ClampMin = 0, ClampMax = 1))
	float CloudCover = 0.4f;
	/** Compass direction the wind blows towards, degrees clockwise from north. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = -360, ClampMax = 360))
	float WindDirection = 250.f;
	/** Surface wind in metres per second (the clouds drift faster, rain slants with it). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = 0, ClampMax = 60))
	float WindSpeed = 7.f;
	/** Seconds a weather change takes during play (the editor applies it at once). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = 0))
	float WeatherBlendSeconds = 90.f;
	/** Seed of the cloud field (the same seed and time give the same clouds on every machine). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather")
	int32 CloudSeed = 104729;
	/** Multiplies the clouds' extinction. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = 0, UIMax = 3))
	float CloudDensityScale = 1.f;
	/** Rain and snow particles round the camera. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather")
	bool bPrecipitationParticles = true;
	/** Most particles in the precipitation box (a downpour shows all of them). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = 0, ClampMax = 100000))
	int32 MaxPrecipitationParticles = 16000;
	/** Lightning flashes inside the storm cloud while Storm > 0. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather")
	bool bLightning = true;
	/** Flashes a minute at full storm. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Weather", meta = (ClampMin = 0, UIMax = 60))
	float LightningPerMinute = 9.f;
	/** Edit a preset's values (applied when that preset is chosen). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, AdvancedDisplay, Category = "Sky|Weather")
	TMap<EBiomeSkyWeather, FBiomeSkyWeatherState> WeatherPresets;

	// ---- Night sky -----------------------------------------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night")
	bool bAuroras = false;
	/** Aurora strength at night, 0-1 (stronger ones reach further towards the equator side of the sky). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (EditCondition = "bAuroras", ClampMin = 0, ClampMax = 1))
	float AuroraStrength = 0.7f;
	/** Sporadic meteors: on average one a minute somewhere in the sky. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night")
	bool bShootingStars = true;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (ClampMin = 0, UIMax = 4))
	float StarBrightness = 1.2f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (ClampMin = 0, UIMax = 2))
	float MilkyWayBrightness = 0.3f;
	/** The moon's drawn size as a multiple of its real 0.52 degrees (a wide game camera shows it smaller than the eye sees it). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (ClampMin = 0.25, UIMax = 12))
	float MoonDrawScale = 5.f;
	/** Luminance of the moon's lit face in the sky. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (ClampMin = 0, UIMax = 8))
	float MoonBrightness = 1.6f;
	/** Force the moon's phase instead of computing it from the date. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (InlineEditConditionToggle))
	bool bOverrideMoonPhase = false;
	/** 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Night", meta = (EditCondition = "bOverrideMoonPhase", ClampMin = 0, ClampMax = 1))
	float MoonPhaseOverride = 0.5f;

	// ---- Light and exposure ---------------------------------------------------------------------------------------

	/** Sun illuminance at full daylight (lux in the engine's default, non-physical light units). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (ClampMin = 0))
	float SunIntensity = 10.f;
	/** Moonlight of a full moon high in a clear sky. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (ClampMin = 0))
	float MoonIntensity = 0.35f;
	/** Limit how far auto exposure opens up, so nights and storms stay dark (the eye would brighten them to noon). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure")
	bool bExposureFloor = true;
	/** Night: the darkest scene brightness (EV100) exposure adapts to. Higher = darker nights. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (EditCondition = "bExposureFloor"))
	float NightExposureFloor = 0.5f;
	/** Under a storm deck by day (EV100). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (EditCondition = "bExposureFloor"))
	float StormExposureFloor = -4.f;
	/** In clear daylight (EV100). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (EditCondition = "bExposureFloor"))
	float DayExposureFloor = -4.f;
	/** Exposure compensation (stops) added in every weather. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure")
	float ExposureBias = 0.f;
	/** Clear-day visibility multiplier on the presets (1 = as the preset says). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (ClampMin = 0.01, UIMax = 4))
	float VisibilityScale = 1.f;
	/** The planet's surface is put this far under the actor (cm). Keeps sunlight on seabeds a little below the actor. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sky|Exposure", meta = (ClampMin = 0))
	float GroundDepth = 10000.f;

	// ---- Assets (made by Tools/sky/build_sky_assets.py) -------------------------------------------------------------

	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UMaterialInterface> SkyMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UMaterialInterface> CloudMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UMaterialInterface> PrecipitationMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UMaterialParameterCollection> ParameterCollection;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UStaticMesh> SkyDomeMesh;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, AdvancedDisplay, Category = "Sky|Assets")
	TSoftObjectPtr<UStaticMesh> ParticleMesh;

	// ---- Components ------------------------------------------------------------------------------------------------

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UDirectionalLightComponent> SunLight;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UDirectionalLightComponent> MoonLight;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<USkyAtmosphereComponent> Atmosphere;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UVolumetricCloudComponent> Clouds;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UStaticMeshComponent> SkyDome;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UPostProcessComponent> Exposure;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UInstancedStaticMeshComponent> Precipitation;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Sky|Components") TObjectPtr<UPointLightComponent> LightningLight;

	// ---- Live state (read-only; other systems may read these by name) ------------------------------------------------

	/** Unit vector towards the sun, world space. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") FVector SunDirection = FVector::UpVector;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") FVector MoonDirection = -FVector::UpVector;
	/** Degrees above the horizon. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float SunElevation = 45.f;
	/** 0 new, 0.5 full. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float MoonPhase = 0.5f;
	/** Lit fraction of the disc, 0-1. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float MoonIllumination = 1.f;
	/** Moonlight reaching the ground, 0-1 (phase, height, cloud). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float MoonLightAmount = 0.f;
	/** 0 night ... 1 full day. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float DayLight = 1.f;
	/** Wind at the surface, metres per second, world space (the direction it blows towards). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") FVector WindVelocity = FVector::ZeroVector;
	/** The weather as it stands now (blending towards the chosen preset). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") FBiomeSkyWeatherState CurrentWeather;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Transient, Category = "Sky|State") float CloudCoverNow = 0.36f;

	// ---- Blueprint API -------------------------------------------------------------------------------------------

	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetTimeOfDay(float Hours);
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetDate(int32 InYear, int32 InMonth, int32 InDay);
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetLocation(float InLatitude, float InLongitude);
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetTimeRunning(bool bRunning) { bTimeRunning = bRunning; }
	/** Change the weather. BlendSeconds < 0 uses WeatherBlendSeconds; 0 is instant. */
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetWeather(EBiomeSkyWeather NewWeather, float BlendSeconds = -1.f);
	/** Override the cloud cover (0-1); a negative value goes back to the preset's. */
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetCloudCover(float Cover);
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SetWind(float DirectionDegrees, float SpeedMetresPerSecond);
	/** Jump every eased value (weather, cover) straight to its target. */
	UFUNCTION(BlueprintCallable, Category = "Biome Sky") void SnapToTarget();

	UFUNCTION(BlueprintPure, Category = "Biome Sky") FVector GetSunDirection() const { return SunDirection; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") FVector GetMoonDirection() const { return MoonDirection; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetSunElevation() const { return SunElevation; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetMoonPhase() const { return MoonPhase; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetMoonIllumination() const { return MoonIllumination; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetMoonLight() const { return MoonLightAmount; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetDayLight() const { return DayLight; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") bool IsNight() const { return SunElevation < -6.f; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") FVector GetWindVelocity() const { return WindVelocity; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetCloudCover() const { return CloudCoverNow; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") FBiomeSkyWeatherState GetCurrentWeather() const { return CurrentWeather; }
	UFUNCTION(BlueprintPure, Category = "Biome Sky") float GetTimeOfDay() const { return TimeOfDay; }
	/** Days since J2000 of the current instant (UTC). */
	UFUNCTION(BlueprintPure, Category = "Biome Sky") double GetDaysSinceJ2000() const;
	/** The preset's air mass (WeatherPresets entry, else the built-in values). */
	UFUNCTION(BlueprintPure, Category = "Biome Sky") FBiomeSkyWeatherState GetPreset(EBiomeSkyWeather Preset) const;
	UFUNCTION(BlueprintPure, Category = "Biome Sky") static FBiomeSkyWeatherState GetDefaultPreset(EBiomeSkyWeather Preset);

	/** The first sky environment in a world (null if none). */
	UFUNCTION(BlueprintPure, Category = "Biome Sky", meta = (WorldContext = "WorldContext"))
	static ABiomeSkyEnvironment* FindSky(const UObject* WorldContext);

	// AActor
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual bool ShouldTickIfViewportsOnly() const override { return true; }
#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif

private:
	void EnsureMaterials();
	void UpdateClock(float DeltaSeconds);
	void UpdateWeather(float DeltaSeconds);
	void UpdateCelestial();
	void UpdateLights();
	void UpdateFogAndExposure();
	void UpdateClouds(float DeltaSeconds);
	void UpdateSkyMaterial();
	void UpdatePrecipitation(float DeltaSeconds);
	void UpdateLightning(float DeltaSeconds);
	void UpdateParameterCollection();
	void ApplyStaticSettings();
	FVector ViewLocation() const;
	FVector LocalToWorld(const FVector& NorthEastUp) const;
	float SkyClock() const;

	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SkyMID;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CloudMID;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PrecipitationMID;
	UPROPERTY(Transient) TObjectPtr<UMaterialInterface> PendingCloudMaterial;

	FBiomeSkyWeatherState BlendFrom;
	float BlendTime = 0.f;
	float BlendDuration = 0.f;
	EBiomeSkyWeather AppliedWeather = EBiomeSkyWeather::Fair;
	bool bWeatherInitialised = false;
	bool bSnap = true;
	float SmoothedCover = 0.36f;
	/** Cloud advection (cm) accumulated from the wind. */
	FVector2D CloudOffset = FVector2D::ZeroVector;
	/** Light directions last applied: a directional light that turns throws away its virtual shadow map cache. */
	FVector AppliedSunDir = FVector::ZeroVector;
	FVector AppliedMoonDir = FVector::ZeroVector;
	/** Local sidereal time (radians). */
	double LocalSiderealTime = 0.0;
	int32 ParticleCount = -1;
	float LightningTimer = 3.f;
	float FlashAge = -1.f, FlashLife = 0.f, FlashPower = 0.f;
	FVector FlashPosition = FVector::ZeroVector;
	float FlashLight = 0.f;
	FRandomStream LightningRandom;
	double ClockSeconds = 0.0;
};
