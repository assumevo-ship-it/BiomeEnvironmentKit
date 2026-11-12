#include "BiomeOceanModel.h"
#include "Async/ParallelFor.h"
#include <cmath>

// Keep in step with Tools/ocean/hlsl/BiomeOceanCommon.hlsl (the GPU half of this model).

namespace BiomeOcean
{
	namespace
	{
		constexpr double G = 9.81;
		constexpr double MinFetch = 40.0;
		constexpr double OldLife = 180.0;

		double Smooth(double A, double B, double X)
		{
			const double T = FMath::Clamp((X - A) / (B - A), 0.0, 1.0);
			return T * T * (3.0 - 2.0 * T);
		}

		FVector2f DirDeg(float Deg)
		{
			const float R = FMath::DegreesToRadians(Deg);
			return FVector2f(FMath::Cos(R), FMath::Sin(R));
		}

		/** Mitsuyasu's spreading exponent s of cos^2s(dtheta/2): narrowest at the peak, broad for shorter and longer waves. */
		double SpreadingS(double Omega, double Peak, double U)
		{
			const double SMax = 11.5 * FMath::Pow(FMath::Max(Peak * U / G, 0.5), -2.5);
			const double Ratio = Omega / Peak;
			return FMath::Clamp(SMax * (Ratio < 1.0 ? FMath::Pow(Ratio, 5.0) : FMath::Pow(Ratio, -2.5)), 1.0, 25.0);
		}

		/** Normalisation of cos^2s(dtheta/2) over the circle: 2^(2s-1) Gamma(s+1)^2 / (pi Gamma(2s+1)). */
		double SpreadingNorm(double S)
		{
			return std::exp((2.0 * S - 1.0) * std::log(2.0) + 2.0 * std::lgamma(S + 1.0) - std::lgamma(2.0 * S + 1.0)) / PI;
		}

		/** JONSWAP shape (gamma 3.3) with unit alpha: the old sea's spectrum before scaling to its variance. */
		double SwellShape(double Omega, double Peak)
		{
			const double Sigma = Omega <= Peak ? 0.07 : 0.09;
			const double R = FMath::Exp(-FMath::Square(Omega - Peak) / (2.0 * FMath::Square(Sigma * Peak)));
			return FMath::Pow(Omega, -5.0) * FMath::Exp(-1.25 * FMath::Pow(Peak / Omega, 4.0)) * FMath::Pow(3.3, R);
		}

		double FetchForVariance(double Target, double U, double FetchM)
		{
			double Lo = MinFetch, Hi = MaxFetch(U, FetchM);
			if (Variance(U, Hi) <= Target) return Hi;
			if (Variance(U, Lo) >= Target) return Lo;
			for (int32 It = 0; It < 32; ++It)
			{
				const double Mid = FMath::Sqrt(Lo * Hi);
				(Variance(U, Mid) < Target ? Lo : Hi) = Mid;
			}
			return FMath::Sqrt(Lo * Hi);
		}

		void AddOldSea(FBiomeSeaCondition& C, double Var, double Period, double HeadingDeg)
		{
			if (Var <= 1e-6) return;
			const double Total = C.OldVariance + Var;
			const double A = Var / Total;
			const FVector2D Mean = FVector2D(DirDeg(C.OldHeadingDeg)) * (1.0 - A) + FVector2D(DirDeg(float(HeadingDeg))) * A;
			C.OldPeriod = float(C.OldVariance > 0.f ? FMath::Lerp(double(C.OldPeriod), Period, A) : Period);
			C.OldHeadingDeg = float(FMath::RadiansToDegrees(FMath::Atan2(Mean.Y, Mean.X)));
			C.OldVariance = float(Total);
		}

		// Radix-2 complex FFT with precomputed twiddles; inverse (e^{+i}), unscaled.
		struct FPlan
		{
			int32 N = 0;
			TArray<int32> Reverse;
			TArray<FVector2f> Twiddle;
			explicit FPlan(int32 InN) : N(InN)
			{
				int32 Bits = 0;
				while ((1 << Bits) < N) ++Bits;
				Reverse.SetNumUninitialized(N);
				for (int32 I = 0; I < N; ++I)
				{
					int32 R = 0;
					for (int32 B = 0; B < Bits; ++B) R |= ((I >> B) & 1) << (Bits - 1 - B);
					Reverse[I] = R;
				}
				Twiddle.SetNumUninitialized(N / 2);
				for (int32 K = 0; K < N / 2; ++K) Twiddle[K] = FVector2f(FMath::Cos(2.0 * PI * K / N), FMath::Sin(2.0 * PI * K / N));
			}
			void Run(FVector2f* Data) const
			{
				for (int32 I = 0; I < N; ++I) if (I < Reverse[I]) Swap(Data[I], Data[Reverse[I]]);
				for (int32 Length = 2; Length <= N; Length <<= 1)
				{
					const int32 Half = Length / 2, Stride = N / Length;
					for (int32 Start = 0; Start < N; Start += Length)
					{
						for (int32 K = 0; K < Half; ++K)
						{
							const FVector2f W = Twiddle[K * Stride];
							const FVector2f U = Data[Start + K], V0 = Data[Start + K + Half];
							const FVector2f V(V0.X * W.X - V0.Y * W.Y, V0.X * W.Y + V0.Y * W.X);
							Data[Start + K] = U + V;
							Data[Start + K + Half] = U - V;
						}
					}
				}
			}
		};

		const FPlan& Plan()
		{
			static const FPlan P(FFTSize);
			return P;
		}

		void InverseFFT2D(TArray<FVector2f>& Grid)
		{
			const FPlan& P = Plan();
			const int32 N = P.N;
			ParallelFor(N, [&Grid, &P, N](int32 Row) { P.Run(Grid.GetData() + Row * N); });
			ParallelFor(N, [&Grid, &P, N](int32 Column)
			{
				TArray<FVector2f, TInlineAllocator<FFTSize>> Line;
				Line.SetNumUninitialized(N);
				for (int32 Row = 0; Row < N; ++Row) Line[Row] = Grid[Row * N + Column];
				P.Run(Line.GetData());
				for (int32 Row = 0; Row < N; ++Row) Grid[Row * N + Column] = Line[Row];
			});
		}

		FVector2f Mul(const FVector2f& A, const FVector2f& B) { return FVector2f(A.X * B.X - A.Y * B.Y, A.X * B.Y + A.Y * B.X); }
		FVector2f Conj(const FVector2f& A) { return FVector2f(A.X, -A.Y); }
		FVector2f TimesI(const FVector2f& A) { return FVector2f(-A.Y, A.X); }

		void AppendMips(TArray<FFloat16Color>& Texels, const TArray<FLinearColor>& Top, int32 N)
		{
			Texels.Reset();
			Texels.Reserve(N * N * 4 / 3 + 1);
			for (const FLinearColor& C : Top) Texels.Add(FFloat16Color(C));
			TArray<FLinearColor> Level = Top, Next;
			int32 Width = N;
			while (Width > 1)
			{
				const int32 Half = Width / 2;
				Next.SetNumUninitialized(Half * Half);
				for (int32 Y = 0; Y < Half; ++Y) for (int32 X = 0; X < Half; ++X)
				{
					Next[Y * Half + X] = (Level[(2 * Y) * Width + 2 * X] + Level[(2 * Y) * Width + 2 * X + 1]
						+ Level[(2 * Y + 1) * Width + 2 * X] + Level[(2 * Y + 1) * Width + 2 * X + 1]) * 0.25f;
				}
				for (const FLinearColor& C : Next) Texels.Add(FFloat16Color(C));
				Swap(Level, Next);
				Width = Half;
			}
		}

		// Integer hash and value noise, bit-identical to the HLSL.
		float Hash01(int32 A, int32 B, uint32 Seed)
		{
			uint32 H = uint32(A) * 374761393u + uint32(B) * 668265263u + Seed * 2246822519u;
			H = (H ^ (H >> 13)) * 1274126177u;
			return float((H ^ (H >> 16)) & 0x00ffffffu) / 16777215.f;
		}

		float ValueNoise(const FVector2f& P, uint32 Seed)
		{
			const float CX = FMath::FloorToFloat(P.X), CY = FMath::FloorToFloat(P.Y);
			const int32 IX = int32(CX), IY = int32(CY);
			float FX = P.X - CX, FY = P.Y - CY;
			FX = FX * FX * (3.f - 2.f * FX);
			FY = FY * FY * (3.f - 2.f * FY);
			return FMath::Lerp(FMath::Lerp(Hash01(IX, IY, Seed), Hash01(IX + 1, IY, Seed), FX),
				FMath::Lerp(Hash01(IX, IY + 1, Seed), Hash01(IX + 1, IY + 1, Seed), FX), FY);
		}

		/** Height factor (mean about 1) of breaker N of a train: sets and lulls, wave-to-wave scatter and short crests. */
		float BreakerHeight(int32 N, int32 Train, const FVector2f& XY, uint32 EnvironmentSeed)
		{
			const uint32 Seed = uint32(Train) * 7919u + 17u + EnvironmentSeed;
			const float S = float(N) / 5.5f;
			const float SC = FMath::FloorToFloat(S);
			float SF = S - SC;
			SF = SF * SF * (3.f - 2.f * SF);
			const float SetMood = FMath::Lerp(Hash01(int32(SC), 0, Seed), Hash01(int32(SC) + 1, 0, Seed), SF);
			const float Set = 0.35f + 1.3f * SmoothStep01(0.2f, 0.8f, SetMood);
			const float Wave = 0.7f + 0.6f * Hash01(N, 1, Seed);
			const FVector2f Offset(Hash01(N, 2, Seed) * 97.f, Hash01(N, 3, Seed) * 97.f);
			const float Crest = 0.45f + 1.1f * ValueNoise(XY / 4500.f + Offset, Seed + 5u);
			return Set * Wave * Crest;
		}

		float SwellGroup(const FWave& W, float SpacePhase, float Time, int32 Index)
		{
			// Beat of neighbouring frequencies: sets travel at about half the crest speed; mean-square energy preserved.
			const float Beat = 0.16f * SpacePhase - 0.080259f * FMath::Sqrt(Gravity * W.K) * Time + Index * 1.713f;
			return (1.f + 0.28f * FMath::Cos(Beat)) * 0.980959f;
		}

		float SurfBlend(const FShore& Shore)
		{
			return (1.f - SmoothStep01(3.5f, 7.f, Shore.DepthM)) * (1.f - SmoothStep01(65.f, 120.f, Shore.SignedDistM));
		}
	}

	float SmoothStep01(float A, float B, float X)
	{
		const float T = FMath::Clamp((X - A) / (B - A), 0.f, 1.f);
		return T * T * (3.f - 2.f * T);
	}

	// ---------------------------------------------------------------------------------------------------------------
	// Spectrum and growth

	double MaxFetch(double U, double FetchM)
	{
		return FMath::Clamp(G * FMath::Max(FetchM, 100.0) / FMath::Square(FMath::Max(U, 0.5)), MinFetch, 20000.0);
	}

	double DurationFetch(double U, double Hours)
	{
		// Duration-limited growth (SPM): g t / U = 68.8 X^(2/3).
		const double T = FMath::Max(0.0, Hours) * 3600.0;
		return FMath::Clamp(FMath::Pow(G * T / FMath::Max(U, 0.5) / 68.8, 1.5), MinFetch, 20000.0);
	}

	double Spectrum(double Omega, double U, double Fetch, double& OutPeak)
	{
		const double X = FMath::Clamp(Fetch, MinFetch, 20000.0);
		const double Alpha = 0.076 * FMath::Pow(X, -0.22);
		OutPeak = 22.0 * (G / U) * FMath::Pow(X, -0.33);
		// Peak enhancement 3.3 for a young sea, easing to Pierson-Moskowitz (1) as it becomes fully developed.
		const double Gamma = FMath::Lerp(3.3, 1.0, FMath::Clamp(FMath::Loge(X / 5000.0) / FMath::Loge(4.0), 0.0, 1.0));
		if (Omega <= 0.0) return 0.0;
		const double Sigma = Omega <= OutPeak ? 0.07 : 0.09;
		const double R = FMath::Exp(-FMath::Square(Omega - OutPeak) / (2.0 * FMath::Square(Sigma * OutPeak)));
		return Alpha * G * G * FMath::Pow(Omega, -5.0) * FMath::Exp(-1.25 * FMath::Pow(OutPeak / Omega, 4.0)) * FMath::Pow(Gamma, R);
	}

	double Variance(double U, double Fetch)
	{
		double Peak = 1.0;
		Spectrum(1.0, U, Fetch, Peak);
		constexpr int32 Steps = 96;
		const double Lo = FMath::Loge(Peak * 0.5), Hi = FMath::Loge(Peak * 8.0), Step = (Hi - Lo) / Steps;
		double Sum = 0.0, Unused = 0.0;
		for (int32 I = 0; I < Steps; ++I)
		{
			const double W = FMath::Exp(Lo + (I + 0.5) * Step);
			Sum += Spectrum(W, U, Fetch, Unused) * W * Step;
		}
		return Sum;
	}

	double PeakPeriod(double U, double Fetch)
	{
		double Peak = 1.0;
		Spectrum(1.0, U, Fetch, Peak);
		return 2.0 * PI / Peak;
	}

	double TotalVariance(const FBiomeSeaCondition& C)
	{
		return Variance(FMath::Max(0.5, double(C.WindU)), C.Fetch) + FMath::Max(0.f, C.OldVariance);
	}

	float Choppiness(float WindU)
	{
		return float(1.0 + 0.45 * Smooth(4.0, 19.0, WindU));
	}

	float WhitecapCover(float WindU)
	{
		return FMath::Min(0.30f, 7.68e-6f * FMath::Pow(FMath::Max(WindU, 0.f), 3.41f)) * SmoothStep01(4.4f, 6.f, WindU);
	}

	void Advance(FBiomeSeaCondition& C, float HeadingDeg, float WindU, double FetchM, float DeltaSeconds, float TimeScale)
	{
		const double Dt = FMath::Clamp(double(DeltaSeconds), 0.0, 1.0);
		const double U = FMath::Max(0.5, double(WindU));
		const double Turn = FMath::FindDeltaAngleDegrees(double(C.HeadingDeg), double(HeadingDeg));
		if (FMath::Abs(Turn) > 50.0)
		{
			AddOldSea(C, Variance(C.WindU, C.Fetch), PeakPeriod(C.WindU, C.Fetch), C.HeadingDeg);
			C.Fetch = float(MinFetch);
			C.HeadingDeg = HeadingDeg;
		}
		else
		{
			const double Tau = 6.0 + 4.0 * PeakPeriod(C.WindU, C.Fetch);
			C.HeadingDeg = float(FMath::UnwindDegrees(C.HeadingDeg + Turn * (1.0 - FMath::Exp(-Dt / Tau))));
		}
		if (!FMath::IsNearlyEqual(double(C.WindU), U, 1e-4))
		{
			const double Now = Variance(C.WindU, C.Fetch);
			const double Most = Variance(U, MaxFetch(U, FetchM));
			if (Now > Most)
			{
				AddOldSea(C, Now - Most, PeakPeriod(C.WindU, C.Fetch), C.HeadingDeg);
				C.Fetch = float(MaxFetch(U, FetchM));
			}
			else
			{
				C.Fetch = float(FetchForVariance(Now, U, FetchM));
			}
			C.WindU = float(U);
		}
		const double Limit = MaxFetch(U, FetchM);
		if (C.Fetch < Limit)
		{
			const double T = 68.8 * FMath::Pow(double(C.Fetch), 2.0 / 3.0) * U / G + Dt * TimeScale;
			C.Fetch = float(FMath::Min(Limit, FMath::Pow(G * T / U / 68.8, 1.5)));
		}
		else
		{
			C.Fetch = float(Limit);
		}
		C.OldVariance = float(C.OldVariance * FMath::Exp(-Dt * FMath::Max(TimeScale, 1.f) / 400.f / OldLife));
		if (C.OldVariance < 1e-4f) C.OldVariance = 0.f;
	}

	// ---------------------------------------------------------------------------------------------------------------
	// FFT cascades

	const FCascadeSpec& CascadeSpec(int32 Index)
	{
		// (tile m, turn deg, longest kept m, shortest kept m, share of the whitecaps). The splits keep every wave on at
		// least ten texels of its tile.
		static const FCascadeSpec Specs[MaxCascades] = {
			{ 1543.0, 11.0, 4000.0, 64.0, 0.25f },
			{ 251.0, 47.0, 64.0, 5.0, 0.75f },
			{ 41.0, 73.0, 5.0, 0.3, 0.f } };
		return Specs[FMath::Clamp(Index, 0, MaxCascades - 1)];
	}

	void InitCascade(FCascade& Cascade, int32 Index, int32 Count, uint32 Seed)
	{
		const FCascadeSpec& S = CascadeSpec(Index);
		Cascade.PatchM = S.PatchM;
		Cascade.RotationRad = FMath::DegreesToRadians(S.RotationDeg);
		Cascade.SplitLowM = S.MinLengthM;
		Cascade.SplitHighM = S.MaxLengthM;
		Cascade.bFirst = Index == 0;
		Cascade.bLast = Index == Count - 1;
		Cascade.FoamShare = S.FoamShare;
		const int32 N = FFTSize;
		FRandomStream Random(int32(Seed * 2654435761u + uint32(S.PatchM * 10.0)));
		Cascade.Noise.SetNumUninitialized(N * N);
		for (FVector2f& Z : Cascade.Noise)
		{
			const double U1 = FMath::Max(1e-12, double(Random.GetFraction())), U2 = Random.GetFraction();
			const double R = FMath::Sqrt(-2.0 * FMath::Loge(U1));
			Z = FVector2f(float(R * FMath::Cos(2.0 * PI * U2)), float(R * FMath::Sin(2.0 * PI * U2)));
		}
		Cascade.H0.Init(FVector2f::ZeroVector, N * N);
		Cascade.Foam.Init(0.f, N * N);
		Cascade.K.SetNumUninitialized(N * N);
		Cascade.Omega.SetNumUninitialized(N * N);
		const double DK = 2.0 * PI / S.PatchM;
		for (int32 Y = 0; Y < N; ++Y) for (int32 X = 0; X < N; ++X)
		{
			const FVector2D K((X - N / 2) * DK, (Y - N / 2) * DK);
			Cascade.K[Y * N + X] = FVector2f(K);
			Cascade.Omega[Y * N + X] = float(FMath::Sqrt(G * K.Size()));
		}
	}

	void ShapeCascade(FCascade& Cascade, const FBiomeSeaCondition& C)
	{
		const int32 N = FFTSize;
		const double DK = 2.0 * PI / Cascade.PatchM;
		const double Texel = Cascade.PatchM / N;
		const double U = FMath::Max(0.5, double(C.WindU));
		double Peak = 1.0;
		Spectrum(1.0, U, C.Fetch, Peak);
		const double SeaHeading = FMath::DegreesToRadians(C.HeadingDeg);
		const double OldHeading = FMath::DegreesToRadians(C.OldHeadingDeg);
		const double OldPeak = 2.0 * PI / FMath::Max(2.0, double(C.OldPeriod));
		double OldScale = 0.0;
		if (C.OldVariance > 0.f)
		{
			double Sum = 0.0;
			const double Lo = FMath::Loge(OldPeak * 0.5), Hi = FMath::Loge(OldPeak * 6.0), Step = (Hi - Lo) / 96;
			for (int32 I = 0; I < 96; ++I)
			{
				const double W = FMath::Exp(Lo + (I + 0.5) * Step);
				Sum += SwellShape(W, OldPeak) * W * Step;
			}
			OldScale = Sum > 0.0 ? C.OldVariance / Sum : 0.0;
		}
		constexpr double OldS = 24.0;
		const double OldNorm = SpreadingNorm(OldS);
		const double KLow = 2.0 * PI / FMath::Max(Cascade.SplitHighM, 1e-3);
		const double KHigh = 2.0 * PI / FMath::Max(Cascade.SplitLowM, 1e-3);
		const bool bFirst = Cascade.bFirst, bLast = Cascade.bLast;
		struct FRow { double Expected = 0.0, Realised = 0.0, Slopes[4] = {}; };
		TArray<FRow> Rows;
		Rows.SetNum(N);
		ParallelFor(N, [&](int32 Y)
		{
			FRow& Row = Rows[Y];
			for (int32 X = 0; X < N; ++X)
			{
				const int32 Index = Y * N + X;
				const FVector2D K(Cascade.K[Index]);
				const double KL = K.Size();
				if (KL <= 0.0 || X == 0 || Y == 0)
				{
					Cascade.H0[Index] = FVector2f::ZeroVector;
					continue;
				}
				// Complementary band edges: a wave near a split is shared between neighbouring cascades.
				double Band = 1.0;
				if (!bFirst) Band *= FMath::SmoothStep(KLow * 0.8, KLow * 1.25, KL);
				Band *= bLast ? 1.0 - FMath::SmoothStep(KHigh * 0.8, KHigh, KL) : 1.0 - FMath::SmoothStep(KHigh * 0.8, KHigh * 1.25, KL);
				if (Band <= 0.0)
				{
					Cascade.H0[Index] = FVector2f::ZeroVector;
					continue;
				}
				const double W = FMath::Sqrt(G * KL);
				const double DWDK = 0.5 * G / W;
				const double Theta = FMath::Atan2(K.Y, K.X) + Cascade.RotationRad;
				const double S = SpreadingS(W, Peak, U);
				double Unused = 0.0;
				double F = Spectrum(W, U, C.Fetch, Unused) * SpreadingNorm(S) * FMath::Pow(FMath::Abs(FMath::Cos(0.5 * (Theta - SeaHeading))), 2.0 * S);
				if (OldScale > 0.0)
					F += OldScale * SwellShape(W, OldPeak) * OldNorm * FMath::Pow(FMath::Abs(FMath::Cos(0.5 * (Theta - OldHeading))), 2.0 * OldS);
				// Wavenumber spectrum per unit k^2: S(w) D(theta) dw/dk / k.
				F *= Band * DWDK / KL;
				const double Var = F * DK * DK;
				Row.Expected += Var;
				const FVector2f H = Cascade.Noise[Index] * float(FMath::Sqrt(0.25 * Var));
				Cascade.H0[Index] = H;
				Row.Realised += 2.0 * H.SizeSquared();
				for (int32 L = 0; L < 4; ++L)
				{
					double T = 1.0;
					if (L > 0)
					{
						const double Half = 0.5 * Texel * double(1 << L);
						const double AX = K.X * Half, AY = K.Y * Half;
						const double SX = FMath::Abs(AX) > 1e-6 ? FMath::Sin(AX) / AX : 1.0, SY = FMath::Abs(AY) > 1e-6 ? FMath::Sin(AY) / AY : 1.0;
						T = FMath::Square(SX * SY);
					}
					Row.Slopes[L] += KL * KL * Var * T;
				}
			}
		});
		double Expected = 0.0, Realised = 0.0, Slopes[4] = {};
		for (const FRow& Row : Rows)
		{
			Expected += Row.Expected;
			Realised += Row.Realised;
			for (int32 L = 0; L < 4; ++L) Slopes[L] += Row.Slopes[L];
		}
		// Exactly the expected variance, not the luck of the draw.
		const float Scale = Realised > 0.0 ? float(FMath::Sqrt(Expected / Realised)) : 0.f;
		for (FVector2f& H : Cascade.H0) H *= Scale;
		Cascade.HeightVariance = Expected;
		for (int32 L = 0; L < 4; ++L) Cascade.SlopeVariance[L] = Slopes[L];
	}

	void EvaluateCascade(FCascade& Cascade, double When, float Lambda, float Cover, float FoamKeep,
		TSharedPtr<TArray<FVector3f>, ESPMode::ThreadSafe>& OutDisp, TArray<FFloat16Color>* OutA, TArray<FFloat16Color>* OutB, TArray<FFloat16Color>* OutC)
	{
		const int32 N = FFTSize;
		const bool bGPU = OutA && OutB && OutC;
		// Packed real fields: X1 = H + i Dx, X2 = Dy + i Sx, X3 = Sy + i Dxx, X4 = Dyy + i Dxy (gameplay alone needs X1, X2).
		TArray<FVector2f> X1, X2, X3, X4;
		X1.SetNumUninitialized(N * N); X2.SetNumUninitialized(N * N);
		if (bGPU) { X3.SetNumUninitialized(N * N); X4.SetNumUninitialized(N * N); }
		ParallelFor(N, [&](int32 Y)
		{
			for (int32 X = 0; X < N; ++X)
			{
				const int32 I = Y * N + X;
				const int32 Mirror = ((N - Y) % N) * N + (N - X) % N;
				const double Angle = double(Cascade.Omega[I]) * When;
				const FVector2f Phase(float(FMath::Cos(Angle)), float(FMath::Sin(Angle)));
				// h(k,t) = h0(k) e^{iwt} + conj(h0(-k)) e^{-iwt}
				const FVector2f H = Mul(Cascade.H0[I], Phase) + Mul(Conj(Cascade.H0[Mirror]), Conj(Phase));
				const FVector2f K = Cascade.K[I];
				const float KL = K.Size();
				const FVector2f KHat = KL > 0.f ? K / KL : FVector2f::ZeroVector;
				// D = i khat h: water gathers under the crests, as in a Gerstner wave.
				const FVector2f Dx = TimesI(H) * KHat.X * Lambda, Dy = TimesI(H) * KHat.Y * Lambda;
				const FVector2f Sx = TimesI(H) * K.X;
				X1[I] = H + TimesI(Dx);
				X2[I] = Dy + TimesI(Sx);
				if (bGPU)
				{
					const FVector2f Sy = TimesI(H) * K.Y;
					const FVector2f Dxx = H * (-K.X * KHat.X * Lambda), Dyy = H * (-K.Y * KHat.Y * Lambda), Dxy = H * (-K.X * KHat.Y * Lambda);
					X3[I] = Sy + TimesI(Dxx);
					X4[I] = Dyy + TimesI(Dxy);
				}
			}
		});
		InverseFFT2D(X1); InverseFFT2D(X2);
		if (bGPU) { InverseFFT2D(X3); InverseFFT2D(X4); }
		TSharedPtr<TArray<FVector3f>, ESPMode::ThreadSafe> Disp = MakeShared<TArray<FVector3f>, ESPMode::ThreadSafe>();
		Disp->SetNumUninitialized(N * N);
		TArray<FLinearColor> A, B, C;
		TArray<float> Compression;
		if (bGPU) { A.SetNumUninitialized(N * N); B.SetNumUninitialized(N * N); C.SetNumUninitialized(N * N); Compression.SetNumUninitialized(N * N); }
		for (int32 Y = 0; Y < N; ++Y) for (int32 X = 0; X < N; ++X)
		{
			const int32 I = Y * N + X;
			// Grid frequencies run from -N/2: undo that shift with (-1)^(x+y). Lengths in cm.
			const float Sign = ((X + Y) & 1) ? -1.f : 1.f;
			const float H = X1[I].X * Sign * 100.f, Dx = X1[I].Y * Sign * 100.f, Dy = X2[I].X * Sign * 100.f;
			(*Disp)[I] = FVector3f(Dx, Dy, H);
			if (bGPU)
			{
				const float Sx = X2[I].Y * Sign, Sy = X3[I].X * Sign;
				const float Dxx = X3[I].Y * Sign, Dyy = X4[I].X * Sign, Dxy = X4[I].Y * Sign;
				A[I] = FLinearColor(Dx, Dy, H, 0.f);
				B[I] = FLinearColor(Sx, Sy, Sx * Sx, Sy * Sy);
				C[I] = FLinearColor(Dxx, Dyy, Dxy, 0.f);
				// How far the water is squeezed together (1 - Jacobian of rest -> displaced): high on steep crests.
				Compression[I] = 1.f - ((1.f + Dxx) * (1.f + Dyy) - Dxy * Dxy);
			}
		}
		if (bGPU && Cascade.FoamShare > 0.f)
		{
			// Whitecaps where the crests are most compressed: the level that leaves the wanted share of the sea breaking
			// right now, measured on this very field (so the cover follows the wind, not a hand-set threshold). Foam then
			// stays with the water it was laid on and fades, so a patch outlives its breaking crest.
			const float Breaking = FMath::Clamp(Cover * Cascade.FoamShare * 0.3f, 0.f, 0.2f);
			if (Breaking > 1e-4f)
			{
				TArray<float> Probe;
				Probe.Reserve(N * N / 16);
				for (int32 I = 0; I < N * N; I += 16) Probe.Add(Compression[I]);
				const int32 At = FMath::Clamp(int32((1.f - Breaking) * Probe.Num()), 0, Probe.Num() - 1);
				std::nth_element(Probe.GetData(), Probe.GetData() + At, Probe.GetData() + Probe.Num());
				Cascade.FoamThreshold = FMath::Max(Probe[At], 0.02f);
			}
			else
			{
				Cascade.FoamThreshold = 10.f;
			}
			const float T0 = Cascade.FoamThreshold, T1 = Cascade.FoamThreshold * 1.6f + 0.05f;
			for (int32 I = 0; I < N * N; ++I)
			{
				const float Fresh = SmoothStep01(T0, T1, Compression[I]);
				Cascade.Foam[I] = FMath::Max(Cascade.Foam[I] * FoamKeep, Fresh);
				A[I].A = Cascade.Foam[I];
			}
		}
		OutDisp = Disp;
		if (bGPU)
		{
			AppendMips(*OutA, A, N);
			AppendMips(*OutB, B, N);
			AppendMips(*OutC, C, N);
		}
	}

	FVector FField::Sample(const FVector2D& XYcm, double At) const
	{
		FVector Out(0.0);
		const double Span = Time - BeforeTime;
		const float Alpha = Span > 1e-4 ? float(FMath::Clamp((At - Time) / Span, -2.0, 2.0)) : 0.f;
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const FPatch& P = Patches[Index];
			if (!P.Now.IsValid()) continue;
			// The texture's convention: texel i is centred at (i + 0.5) / N of the tile, which wraps.
			const double U = (P.Cos * XYcm.X + P.Sin * XYcm.Y) / P.PatchCm * FFTSize - 0.5;
			const double V = (-P.Sin * XYcm.X + P.Cos * XYcm.Y) / P.PatchCm * FFTSize - 0.5;
			const double FU = FMath::Floor(U), FV = FMath::Floor(V);
			const int32 X0 = int32(int64(FU) & (FFTSize - 1)), Y0 = int32(int64(FV) & (FFTSize - 1));
			const int32 X1 = (X0 + 1) & (FFTSize - 1), Y1 = (Y0 + 1) & (FFTSize - 1);
			const float TX = float(U - FU), TY = float(V - FV);
			auto Bilinear = [&](const TArray<FVector3f>& D)
			{
				return FMath::Lerp(FMath::Lerp(D[Y0 * FFTSize + X0], D[Y0 * FFTSize + X1], TX), FMath::Lerp(D[Y1 * FFTSize + X0], D[Y1 * FFTSize + X1], TX), TY);
			};
			FVector3f D = Bilinear(*P.Now);
			if (Alpha != 0.f && P.Before.IsValid()) D += (D - Bilinear(*P.Before)) * Alpha;
			Out += FVector(P.Cos * D.X - P.Sin * D.Y, P.Sin * D.X + P.Cos * D.Y, D.Z);
		}
		return Out;
	}

	// ---------------------------------------------------------------------------------------------------------------
	// Swells, shore and displacement

	void BuildSeaState(const FBiomeSeaCondition& Condition, float SwellHeadingDeg, float SwellAmount, int32 Seed, FSeaState& Out)
	{
		struct FSwell { float TurnDeg; float LengthM; float BaseAmpM; };
		static const FSwell Swells[NumSwells] = {
			{ 0.f, 150.f, 0.36f }, { 17.f, 104.f, 0.27f }, { -23.f, 78.f, 0.20f },
			{ 52.f, 128.f, 0.13f },   // a cross swell from a distant storm
			{ -8.f, 61.f, 0.12f } };
		Out.Seed = uint32(Seed) & 0xffffu;
		const float S = FMath::Clamp((Condition.WindU - 2.f) / 8.f, 0.f, 2.5f);
		const float HeadingRad = FMath::DegreesToRadians(Condition.HeadingDeg);
		Out.SeaHeading = FVector2f(FMath::Cos(HeadingRad), FMath::Sin(HeadingRad));
		Out.WindSeaVariance = float(TotalVariance(Condition) * 1e4);
		const float Scale = FMath::Clamp(Condition.Swell * SwellAmount, 0.f, 4.f);
		float SumKA = 0.f, SlopeVariance = 0.f, SumAmp = 0.f;
		for (int32 i = 0; i < NumSwells; ++i)
		{
			FWave& W = Out.Waves[i];
			W.Dir = DirDeg(SwellHeadingDeg + Swells[i].TurnDeg);
			W.K = 2.f * PI / (Swells[i].LengthM * 100.f);
			W.Phase = i * 2.39996f + (Out.Seed ? Hash01(i, 0, Out.Seed) * (2.f * PI) : 0.f);
			W.Amp = Swells[i].BaseAmpM * 100.f * Scale;
			SumKA += W.K * W.Amp;
			SlopeVariance += 0.5f * FMath::Square(W.K * W.Amp);
			SumAmp += W.Amp;
		}
		const float Steepness = 0.45f + 0.47f * FMath::Clamp((S - 0.3f) / 1.8f, 0.f, 1.f);
		Out.Choppiness = FMath::Min(1.f, Steepness / FMath::Max(FMath::Min(SumKA, 5.6f * FMath::Sqrt(SlopeVariance)), 1e-4f));
		Out.RunUp = 20.f + 20.f * S;
		Out.Strength = S;
		Out.MaxRise = 1.25f * (1.65f * 1.26f * SumAmp + 6.f * FMath::Sqrt(Out.WindSeaVariance) + 420.f + Out.RunUp) + 50.f;
	}

	float ShoalingScale(float DeepK, float DepthM)
	{
		if (DeepK <= 0.f || DepthM >= 40.f) return 1.f;
		const float KH0 = DeepK * FMath::Max(30.f, DepthM * 100.f);
		float KH = FMath::Max(KH0, FMath::Sqrt(KH0));
		// Solve k h tanh(k h) = k0 h at fixed frequency.
		for (int32 Iteration = 0; Iteration < 3; ++Iteration)
		{
			const float T = FMath::Tanh(KH);
			KH -= (KH * T - KH0) / FMath::Max(T + KH * (1.f - T * T), 1e-5f);
		}
		const float T = FMath::Tanh(KH);
		// cg/cg0 = k0/k (1 + 2kh/sinh 2kh); amplitude goes as sqrt(cg0/cg).
		const float GroupRatio = KH0 / FMath::Max(KH, 1e-5f) * (1.f + KH * (1.f - T * T) / FMath::Max(T, 1e-5f));
		const float Scale = FMath::Clamp(1.f / FMath::Sqrt(FMath::Max(GroupRatio, 0.01f)), 0.7f, 1.65f);
		return FMath::Lerp(Scale, 1.f, SmoothStep01(15.f, 40.f, DepthM));
	}

	FVector CoastalSurf(const FSeaState& Sea, const FShore& Shore, const FVector2D& XY, float Time)
	{
		FVector Out(0.f);
		const float D = Shore.SignedDistM;
		const float Blend = SurfBlend(Shore);
		if (Blend <= 0.f || D < -10.f) return Out;
		const FVector2f P(XY);
		float Theta[NumTrains], Incoming[NumTrains];
		float SumIncoming = 0.f;
		for (int32 Train = 0; Train < NumTrains; ++Train)
		{
			const FWave& W = Sea.Waves[Train];
			const float SpacePhase = W.K * FVector2f::DotProduct(W.Dir, P);
			Theta[Train] = SpacePhase - FMath::Sqrt(Gravity * W.K) * Time + W.Phase;
			const float U = (Theta[Train] - HALF_PI) / (2.f * PI);
			const float N = FMath::FloorToFloat(U);
			const float Mood = FMath::Lerp(BreakerHeight(int32(N), Train, P, Sea.Seed), BreakerHeight(int32(N) + 1, Train, P, Sea.Seed),
				SmoothStep01(0.35f, 0.65f, U - N));
			Incoming[Train] = 2.f * W.Amp * ShoalingScale(W.K, Shore.DepthM) * Mood * SwellGroup(W, SpacePhase, Time, Train);
			SumIncoming += Incoming[Train];
		}
		const float Scale = FMath::Min(1.f, 0.78f * FMath::Max(0.f, Shore.DepthM) * 100.f / FMath::Max(1.f, SumIncoming));
		const float Breaking = SmoothStep01(0.42f, 0.9f, SumIncoming / FMath::Max(35.f, Shore.DepthM * 100.f));
		const float Water = SmoothStep01(-0.5f, 1.5f, D);
		const float WashZone = 1.f - SmoothStep01(1.f, 5.f, D);
		float Wetness = 0.f;
		for (int32 Train = 0; Train < NumTrains; ++Train)
		{
			const float Th = Theta[Train];
			const float H = Incoming[Train] * Scale * Blend * Water;
			const float Steep = 0.35f + 0.65f * Breaking;
			// Zero-mean harmonics raise a narrow crest and steepen its shoreward face.
			const float Profile = 0.5f * FMath::Sin(Th) - 0.16f * Steep * FMath::Cos(2.f * Th) + 0.10f * Breaking * FMath::Sin(2.f * Th);
			const float Peak = 0.5f + 0.5f * FMath::Sin(Th);
			const float LocalK = Sea.Waves[Train].K;
			const float Surge = FMath::Min(0.22f * H, 0.07f / FMath::Max(LocalK, 1e-7f));
			const float Ratio = (Incoming[Train] + 0.35f * FMath::Max(0.f, SumIncoming - Incoming[Train])) / FMath::Max(35.f, Shore.DepthM * 100.f);
			const float Pitch = SmoothStep01(0.32f, 0.5f, Ratio) * (1.f - SmoothStep01(0.75f, 1.1f, Ratio));
			const float Lean = FMath::Min(0.3f * H, 0.08f / FMath::Max(LocalK, 1e-7f)) * Pitch * FMath::Pow(Peak, 6.f);
			Out.Z += H * Profile;
			Out.X += Shore.ToShore.X * (Surge * Peak * Peak + Lean);
			Out.Y += Shore.ToShore.Y * (Surge * Peak * Peak + Lean);
			// Swash: a fast uprush and slower retreat moving across the beach.
			const float Age = (HALF_PI - Th) / (2.f * PI);
			const float Cycle = Age - FMath::FloorToFloat(Age);
			const float Pulse = SmoothStep01(0.02f, 0.20f, Cycle) * (1.f - SmoothStep01(0.32f, 0.90f, Cycle));
			const float Front = FMath::Clamp(1.5f + Incoming[Train] * 0.045f, 1.5f, 9.f) * Pulse;
			const float Wet = (1.f - SmoothStep01(Front - 0.7f, Front + 0.3f, FMath::Max(0.f, -D))) * SmoothStep01(0.f, 0.07f, Pulse) * Blend * WashZone;
			Wetness = FMath::Max(Wetness, Wet * SmoothStep01(5.f, 55.f, Incoming[Train]));
		}
		Out.Z += Sea.RunUp * Wetness * 0.55f;
		return Out;
	}

	FVector Displacement(const FSeaState& Sea, const FShore& Shore, const FVector2D& XY, float Time)
	{
		const float D = Shore.SignedDistM;
		// The swell feels the shelf and dies in the shallows; breakers take over near the beach.
		const float OpenAtt = SmoothStep01(0.15f, 1.2f, Shore.DepthM) * SmoothStep01(0.f, 5.f, D);
		float Variance = Sea.WindSeaVariance;
		for (const FWave& W : Sea.Waves) Variance += 0.5f * W.Amp * W.Amp;
		const float CrestBound = 5.2f * FMath::Sqrt(Variance);
		const float DepthLimit = FMath::Min(1.f, 0.39f * FMath::Max(0.f, Shore.DepthM) * 100.f / FMath::Max(1.f, CrestBound));
		const float Blend = SurfBlend(Shore);
		const FVector2f P(XY);
		FVector Out(0.f);
		for (int32 i = 0; i < NumSwells; ++i)
		{
			const FWave& W = Sea.Waves[i];
			if (W.Amp <= 0.01f) continue;
			const float SpacePhase = W.K * FVector2f::DotProduct(W.Dir, P);
			const float Theta = SpacePhase - FMath::Sqrt(Gravity * W.K) * Time + W.Phase;
			const float WaterType = i < NumTrains ? 1.f - Blend : 1.f;
			const float BaseA = W.Amp * OpenAtt * DepthLimit * WaterType;
			const float A = BaseA * ShoalingScale(W.K, Shore.DepthM) * SwellGroup(W, SpacePhase, Time, i);
			// Cap the horizontal strain so shoaling shelves never fold the surface.
			const float HorizontalA = Sea.Choppiness * FMath::Min(A, BaseA / 1.07f);
			const float C = FMath::Cos(Theta);
			Out.X += W.Dir.X * HorizontalA * C;
			Out.Y += W.Dir.Y * HorizontalA * C;
			Out.Z += A * FMath::Sin(Theta);
		}
		if (Sea.WindSea.IsValid())
		{
			// The wind sea calms on the shelf (the same factor as the material).
			const float Amp = OpenAtt * DepthLimit * FMath::Lerp(0.12f, 1.f, SmoothStep01(1.5f, 14.f, Shore.DepthM));
			if (Amp > 0.f) Out += Sea.WindSea->Sample(XY, Time) * Amp;
		}
		Out += CoastalSurf(Sea, Shore, XY, Time);
		return Out;
	}

	static FVector2D SurfaceParticle(const FSeaState& Sea, TFunctionRef<FShore(const FVector2D&)> ShoreAt, const FVector2D& XY, float Time, FVector& BestDisplacement)
	{
		FVector2D Rest = XY, BestRest = XY, BestStep = FVector2D::ZeroVector;
		float BestError = TNumericLimits<float>::Max();
		float Step = 1.f;
		BestDisplacement = FVector::ZeroVector;
		// Fixed-point inversion of the horizontal displacement, halving the step whenever an iterate gets worse.
		for (int32 Iteration = 0; Iteration < 24; ++Iteration)
		{
			const FVector D = Displacement(Sea, ShoreAt(Rest), Rest, Time);
			const FVector2D Error = Rest + FVector2D(D.X, D.Y) - XY;
			const float ErrorSq = float(Error.SizeSquared());
			if (ErrorSq < BestError)
			{
				BestError = ErrorSq;
				BestDisplacement = D;
				BestRest = Rest;
				BestStep = Error;
				Step = FMath::Min(1.f, Step * 1.5f);
			}
			else
			{
				Step = FMath::Max(0.05f, Step * 0.5f);
			}
			if (BestError < 0.01f) break;
			Rest = BestRest - BestStep * Step;
		}
		return BestRest;
	}

	float SurfaceHeight(const FSeaState& Sea, TFunctionRef<FShore(const FVector2D&)> ShoreAt, const FVector2D& XY, float Time)
	{
		FVector D;
		SurfaceParticle(Sea, ShoreAt, XY, Time, D);
		return float(D.Z);
	}

	FSurfaceSample SurfaceKinematics(const FSeaState& Sea, TFunctionRef<FShore(const FVector2D&)> ShoreAt, const FVector2D& XY, float Time)
	{
		FSurfaceSample Out;
		FVector D;
		const FVector2D Rest = SurfaceParticle(Sea, ShoreAt, XY, Time, D);
		const FShore Shore = ShoreAt(Rest);
		const FVector2D X(5, 0), Y(0, 5);
		const FVector DX = FVector(1, 0, 0) + (Displacement(Sea, ShoreAt(Rest + X), Rest + X, Time) - Displacement(Sea, ShoreAt(Rest - X), Rest - X, Time)) / 10.f;
		const FVector DY = FVector(0, 1, 0) + (Displacement(Sea, ShoreAt(Rest + Y), Rest + Y, Time) - Displacement(Sea, ShoreAt(Rest - Y), Rest - Y, Time)) / 10.f;
		Out.Height = float(D.Z);
		Out.Normal = FVector::CrossProduct(DX, DY).GetSafeNormal();
		Out.Velocity = (Displacement(Sea, Shore, Rest, Time + 0.025f) - Displacement(Sea, Shore, Rest, Time - 0.025f)) / 0.05f;
		return Out;
	}
}
