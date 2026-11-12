#include "BiomeSkyAstronomy.h"

namespace BiomeSkyAstronomy
{
	namespace
	{
		constexpr double Deg = UE_DOUBLE_PI / 180.0;
		double Wrap(double Radians)
		{
			const double R = FMath::Fmod(Radians, 2.0 * UE_DOUBLE_PI);
			return R < 0.0 ? R + 2.0 * UE_DOUBLE_PI : R;
		}
	}

	double Obliquity(double Days)
	{
		return (23.439 - 0.0000004 * Days) * Deg;
	}

	FEcliptic Sun(double Days)
	{
		// Mean anomaly g and mean longitude q, then the equation of the centre (Astronomical Almanac, "low precision").
		const double G = Wrap((357.529 + 0.98560028 * Days) * Deg);
		const double Q = (280.459 + 0.98564736 * Days) * Deg;
		FEcliptic Out;
		Out.Longitude = Wrap(Q + (1.915 * FMath::Sin(G) + 0.020 * FMath::Sin(2.0 * G)) * Deg);
		Out.Latitude = 0.0;
		return Out;
	}

	FEcliptic Moon(double Days)
	{
		// Mean elements (Meeus, Astronomical Algorithms ch. 47, truncated): mean longitude L, mean anomaly M', the sun's
		// mean anomaly M, mean elongation D and argument of latitude F.
		const double L = (218.316 + 13.176396 * Days) * Deg;
		const double Mp = (134.963 + 13.064993 * Days) * Deg;
		const double M = (357.529 + 0.98560028 * Days) * Deg;
		const double D = (297.850 + 12.190749 * Days) * Deg;
		const double F = (93.272 + 13.229350 * Days) * Deg;
		FEcliptic Out;
		Out.Longitude = Wrap(L
			+ 6.289 * Deg * FMath::Sin(Mp)                // equation of the centre
			+ 1.274 * Deg * FMath::Sin(2.0 * D - Mp)      // evection
			+ 0.658 * Deg * FMath::Sin(2.0 * D)           // variation
			+ 0.214 * Deg * FMath::Sin(2.0 * Mp)
			- 0.186 * Deg * FMath::Sin(M)                 // annual equation
			- 0.114 * Deg * FMath::Sin(2.0 * F));
		Out.Latitude = 5.128 * Deg * FMath::Sin(F)
			+ 0.281 * Deg * FMath::Sin(Mp + F)
			+ 0.278 * Deg * FMath::Sin(Mp - F)
			+ 0.173 * Deg * FMath::Sin(2.0 * D - F);
		return Out;
	}

	FEquatorial ToEquatorial(const FEcliptic& E, double Days)
	{
		const double Eps = Obliquity(Days);
		FEquatorial Out;
		Out.RightAscension = Wrap(FMath::Atan2(FMath::Sin(E.Longitude) * FMath::Cos(Eps) - FMath::Tan(E.Latitude) * FMath::Sin(Eps), FMath::Cos(E.Longitude)));
		Out.Declination = FMath::Asin(FMath::Clamp(FMath::Sin(E.Latitude) * FMath::Cos(Eps) + FMath::Cos(E.Latitude) * FMath::Sin(Eps) * FMath::Sin(E.Longitude), -1.0, 1.0));
		return Out;
	}

	double GreenwichSiderealTime(double Days)
	{
		return Wrap((18.697374558 + 24.06570982441908 * Days) * 15.0 * Deg);
	}

	FVector HorizonDirection(double H, double Dec, double Lat)
	{
		const double East = -FMath::Cos(Dec) * FMath::Sin(H);
		const double North = FMath::Sin(Dec) * FMath::Cos(Lat) - FMath::Cos(Dec) * FMath::Cos(H) * FMath::Sin(Lat);
		const double Up = FMath::Sin(Dec) * FMath::Sin(Lat) + FMath::Cos(Dec) * FMath::Cos(H) * FMath::Cos(Lat);
		return FVector(North, East, Up).GetSafeNormal();
	}

	double MoonPhase(const FEcliptic& SunPos, const FEcliptic& MoonPos)
	{
		return Wrap(MoonPos.Longitude - SunPos.Longitude) / (2.0 * UE_DOUBLE_PI);
	}

	double MoonIllumination(double Phase)
	{
		return 0.5 - 0.5 * FMath::Cos(2.0 * UE_DOUBLE_PI * Phase);
	}

	double JulianDate(int32 Year, int32 Month, int32 Day, double Hours, double UtcOffsetHours)
	{
		Year = FMath::Clamp(Year, 1, 9998);
		Month = FMath::Clamp(Month, 1, 12);
		Day = FMath::Clamp(Day, 1, FDateTime::DaysInMonth(Year, Month));
		return FDateTime(Year, Month, Day).GetJulianDay() + (Hours - UtcOffsetHours) / 24.0;
	}
}
