#pragma once

#include "CoreMinimal.h"

/**
 * Low-precision ephemeris of the sun and the moon (the US Naval Observatory / Astronomical Almanac formulas, good to
 * about a hundredth of a degree for the sun and a few tenths for the moon over centuries around J2000), plus the
 * conversions between the sky's frames. Everything is plain maths: no world, no actor.
 *
 * Frames:
 *  - Equatorial (J2000-ish): X towards right ascension 0 on the celestial equator, Y towards RA 6 h, Z the north
 *    celestial pole.
 *  - Local horizon: X north, Y east, Z up (the same handedness as Unreal's X forward, Y right, Z up, so a level whose
 *    +X is north needs no conversion).
 */
namespace BiomeSkyAstronomy
{
	/** Days since J2000.0 (2000-01-01 12:00 TT, ~UTC for our purposes) from a Julian date. */
	inline double DaysSinceJ2000(double JulianDate) { return JulianDate - 2451545.0; }

	/** Ecliptic longitude and latitude (radians) of a body. */
	struct FEcliptic { double Longitude = 0.0; double Latitude = 0.0; };
	/** Right ascension (radians, 0..2pi) and declination (radians). */
	struct FEquatorial { double RightAscension = 0.0; double Declination = 0.0; };

	/** Obliquity of the ecliptic (radians) at a date. */
	BIOMESKY_API double Obliquity(double Days);
	/** The sun's apparent ecliptic position. */
	BIOMESKY_API FEcliptic Sun(double Days);
	/** The moon's ecliptic position (main periodic terms: equation of the centre, evection, variation, annual equation). */
	BIOMESKY_API FEcliptic Moon(double Days);
	BIOMESKY_API FEquatorial ToEquatorial(const FEcliptic& Ecliptic, double Days);
	/** Greenwich mean sidereal time (radians, 0..2pi). */
	BIOMESKY_API double GreenwichSiderealTime(double Days);
	/** Unit vector in the local horizon frame (X north, Y east, Z up) for a body at an hour angle and declination. */
	BIOMESKY_API FVector HorizonDirection(double HourAngle, double Declination, double Latitude);
	/** The lunar phase as the fraction of the synodic month since new moon (0 new, 0.25 first quarter, 0.5 full). */
	BIOMESKY_API double MoonPhase(const FEcliptic& Sun, const FEcliptic& Moon);
	/** Illuminated fraction of the moon's disc (0..1) for a phase. */
	BIOMESKY_API double MoonIllumination(double Phase);
	/** Julian date of a civil date and clock time (hours, may be outside 0..24) at a UTC offset (hours). */
	BIOMESKY_API double JulianDate(int32 Year, int32 Month, int32 Day, double Hours, double UtcOffsetHours);
}
