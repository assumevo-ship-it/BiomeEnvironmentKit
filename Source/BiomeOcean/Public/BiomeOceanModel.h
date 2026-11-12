#pragma once

#include "CoreMinimal.h"
#include "BiomeOceanModel.generated.h"

/**
 * What the wind has made of the sea so far: the state the wind sea's spectrum is shaped from.
 *
 *  - A wind sea grows with the time the wind has blown and the open water it blows over (JONSWAP, duration- and
 *    fetch-limited growth from the Shore Protection Manual). Fetch is kept as the dimensionless g X / U^2
 *    (about 20000 means fully developed): a young sea is short, steep chop; a mature one long, heavy waves.
 *  - When the wind drops, or swings round by more than 50 degrees, the sea it raised carries on as old sea (swell) in its
 *    own direction and dies away over a few minutes, while a new wind sea starts under it (a crossed sea after a front).
 *  - Swell scales the five long ocean swells (storms far away).
 */
USTRUCT(BlueprintType)
struct BIOMEOCEAN_API FBiomeSeaCondition
{
	GENERATED_BODY()

	/** Wind speed (m/s at 10 m) the wind sea is growing in. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float WindU = 10.f;
	/** Dimensionless fetch g X / U^2 (JONSWAP); about 20000 is a fully developed sea. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float Fetch = 20000.f;
	/** Heading the wind sea runs towards, degrees (Unreal yaw: 0 = +X, 90 = +Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float HeadingDeg = 0.f;
	/** Old sea left by a dropping or turning wind: variance (m^2), peak period (s), heading (degrees). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float OldVariance = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float OldPeriod = 8.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float OldHeadingDeg = 0.f;
	/** Scale of the long ocean swells. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sea") float Swell = 1.f;
	/** Bumped when the sea is set at once instead of grown (the wind sea is reshaped immediately). */
	UPROPERTY() uint8 Generation = 0;
};

/**
 * The ocean's wave model, shared by the GPU (M_BiomeOcean, HLSL in Tools/ocean/hlsl) and gameplay queries.
 * Everything is a pure function of time, the sea condition and the optional shore field, so the CPU floats a boat on the
 * crest the player sees. Units: centimetres and seconds (k in rad/cm, g = 981 cm/s^2) unless a name says metres.
 *
 *  - Five Gerstner swells (fixed wavelengths 61-150 m, one a cross swell), energy-normalised wave groups so crests grow and
 *    subside in sets.
 *  - The wind sea: FFT cascades holding the JONSWAP spectrum with Mitsuyasu spreading (BiomeWindSea), from about 1.5 km
 *    down to 30 cm.
 *  - Shallows: finite-depth shoaling, a depth cap, and three swells continuing as individually sized breakers with swash.
 */
namespace BiomeOcean
{
	constexpr int32 NumSwells = 5;
	/** The first NumTrains swells become shore breakers. */
	constexpr int32 NumTrains = 3;
	constexpr int32 MaxCascades = 3;
	constexpr int32 FFTSize = 256;
	constexpr float Gravity = 981.f;

	BIOMEOCEAN_API float SmoothStep01(float A, float B, float X);

	// ----- spectrum and sea growth (metres, seconds) -----
	/** Fully developed or fetch-limited dimensionless fetch for wind U over FetchM metres of open water. */
	BIOMEOCEAN_API double MaxFetch(double U, double FetchM);
	/** Duration-limited dimensionless fetch after the wind has blown Hours. */
	BIOMEOCEAN_API double DurationFetch(double U, double Hours);
	/** JONSWAP frequency spectrum (m^2 s) and its peak (rad/s). */
	BIOMEOCEAN_API double Spectrum(double Omega, double U, double Fetch, double& OutPeak);
	/** Wind-sea variance (m^2): Hs = 4 sqrt(variance). */
	BIOMEOCEAN_API double Variance(double U, double Fetch);
	BIOMEOCEAN_API double PeakPeriod(double U, double Fetch);
	BIOMEOCEAN_API double TotalVariance(const FBiomeSeaCondition& Condition);
	/** Horizontal displacement scale of the wind sea (sharper crests in a strong wind). */
	BIOMEOCEAN_API float Choppiness(float WindU);
	/** Fraction of the sea under whitecap foam for a wind (Monahan-style, none below ~4.5 m/s, at most 30%). */
	BIOMEOCEAN_API float WhitecapCover(float WindU);
	/** Grows, turns and ages the sea for DeltaSeconds of this wind (TimeScale: sea seconds per game second). */
	BIOMEOCEAN_API void Advance(FBiomeSeaCondition& Condition, float HeadingDeg, float WindU, double FetchM, float DeltaSeconds, float TimeScale);

	// ----- FFT cascades -----
	struct FCascadeSpec { double PatchM, RotationDeg, MaxLengthM, MinLengthM; float FoamShare; };
	/** Tiles 1543 m, 251 m, 41 m (turned against each other so their repeats never line up). */
	BIOMEOCEAN_API const FCascadeSpec& CascadeSpec(int32 Index);

	struct FCascade
	{
		double PatchM = 1000.0, RotationRad = 0.0, SplitLowM = 0.0, SplitHighM = 0.0;
		bool bFirst = true, bLast = true;
		float FoamShare = 0.f;
		TArray<FVector2f> Noise;    // complex standard normal per k texel
		TArray<FVector2f> H0;       // h0(k), m
		TArray<FVector2f> K;        // rad/m, patch axes
		TArray<float> Omega;        // rad/s
		TArray<float> Foam;         // persistent whitecap foam per texel (0-1), lives with the water
		double HeightVariance = 0.0;          // m^2
		double SlopeVariance[4] = {};         // as mips 0-3 of its textures resolve it
		float FoamThreshold = 1.f;            // compression where foam starts (from the measured distribution)
	};

	BIOMEOCEAN_API void InitCascade(FCascade& Cascade, int32 Index, int32 Count, uint32 Seed);
	BIOMEOCEAN_API void ShapeCascade(FCascade& Cascade, const FBiomeSeaCondition& Condition);
	/** The cascade at a time: displacement (Dx, Dy, H cm) and, when the outputs are given, its texture texels with mips:
	 *  A (Dx, Dy, H, foam), B (Sx, Sy, Sx^2, Sy^2), C (Dxx, Dyy, Dxy, 0). Cover is the wanted whitecap fraction; old foam
	 *  is multiplied by FoamKeep (its decay over this update). */
	BIOMEOCEAN_API void EvaluateCascade(FCascade& Cascade, double When, float Lambda, float Cover, float FoamKeep,
		TSharedPtr<TArray<FVector3f>, ESPMode::ThreadSafe>& OutDisp, TArray<FFloat16Color>* OutA, TArray<FFloat16Color>* OutB, TArray<FFloat16Color>* OutC);

	struct FPatch
	{
		double PatchCm = 1.0;
		float Cos = 1.f, Sin = 0.f;
		TSharedPtr<const TArray<FVector3f>, ESPMode::ThreadSafe> Now, Before;
	};

	/** One evaluated wind sea, shared read-only with gameplay. */
	struct BIOMEOCEAN_API FField
	{
		double Time = 0.0, BeforeTime = 0.0;
		int32 Count = 0;
		FPatch Patches[MaxCascades];
		/** Displacement (cm) of the water particle resting at XY (cm) at a time close to Time (extrapolated linearly). */
		FVector Sample(const FVector2D& XYcm, double At) const;
	};

	// ----- swells, shore, displacement (centimetres) -----
	struct FWave
	{
		FVector2f Dir = FVector2f(1.f, 0.f);
		float K = 0.f, Amp = 0.f, Phase = 0.f;
	};

	/** The sea bed under a point, from the baked shore field (open deep sea without one). */
	struct FShore
	{
		float SignedDistM = 300.f;   // metres to the waterline, negative on land
		float DepthM = 40.f;         // water depth, eased into a 40 m reference sea
		FVector2f ToShore = FVector2f(1.f, 0.f);
	};

	struct BIOMEOCEAN_API FSeaState
	{
		FWave Waves[NumSwells];
		uint32 Seed = 0;
		float Choppiness = 0.6f;     // swells' Gerstner Q
		float Strength = 0.6f;       // 0 calm .. 2.5 storm (from the wind speed)
		float RunUp = 35.f;          // swash height on the beach, cm
		TSharedPtr<const FField, ESPMode::ThreadSafe> WindSea;
		FVector2f SeaHeading = FVector2f(1.f, 0.f);
		float WindSeaVariance = 0.f;  // cm^2
		float MaxRise = 1000.f;       // cm above sea level no wave can reach
	};

	/** Swells for a condition: SwellHeadingDeg is where they run to, Amount scales them. */
	BIOMEOCEAN_API void BuildSeaState(const FBiomeSeaCondition& Condition, float SwellHeadingDeg, float SwellAmount, int32 Seed, FSeaState& Out);
	BIOMEOCEAN_API float ShoalingScale(float DeepK, float DepthM);
	BIOMEOCEAN_API FVector CoastalSurf(const FSeaState& Sea, const FShore& Shore, const FVector2D& XY, float Time);
	/** Displacement (cm) of the water particle that rests at XY (cm), relative to sea level, at Time (s). */
	BIOMEOCEAN_API FVector Displacement(const FSeaState& Sea, const FShore& Shore, const FVector2D& XY, float Time);

	struct FSurfaceSample
	{
		float Height = 0.f;
		FVector Normal = FVector::UpVector;
		FVector Velocity = FVector::ZeroVector;
	};
	/** Eulerian height at XY: finds the particle whose displaced position lands on XY. */
	BIOMEOCEAN_API float SurfaceHeight(const FSeaState& Sea, TFunctionRef<FShore(const FVector2D&)> ShoreAt, const FVector2D& XY, float Time);
	BIOMEOCEAN_API FSurfaceSample SurfaceKinematics(const FSeaState& Sea, TFunctionRef<FShore(const FVector2D&)> ShoreAt, const FVector2D& XY, float Time);
}
