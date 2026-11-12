"""The brightest stars of the night sky for M_BiomeSky (Tools/sky/build_sky_assets.py).

Each entry: name, right ascension (hours, J2000), declination (degrees), visual magnitude, B-V colour index (None: white).
Positions and magnitudes are public astronomical data (Yale Bright Star Catalogue / Hipparcos values). The shader turns the
view ray into right ascension and declination for the actor's latitude and local sidereal time, so the same table is
right at any place, date and hour.
"""
import math

STARS = [
    # Orion
    ("Betelgeuse", 5.919, 7.41, 0.45, 1.85), ("Rigel", 5.242, -8.20, 0.13, -0.03), ("Bellatrix", 5.419, 6.35, 1.64, -0.22),
    ("Saiph", 5.796, -9.67, 2.06, -0.17), ("Alnitak", 5.679, -1.94, 1.77, -0.21), ("Alnilam", 5.604, -1.20, 1.69, -0.18),
    ("Mintaka", 5.533, -0.30, 2.23, -0.22), ("Meissa", 5.585, 9.93, 3.39, -0.16),
    # Canis Major, Canis Minor
    ("Sirius", 6.752, -16.72, -1.46, 0.00), ("Adhara", 6.977, -28.97, 1.50, -0.21), ("Wezen", 7.140, -26.39, 1.83, 0.68),
    ("Mirzam", 6.378, -17.96, 1.98, -0.24), ("Aludra", 7.402, -29.30, 2.45, -0.08), ("Procyon", 7.655, 5.22, 0.34, 0.42),
    ("Gomeisa", 7.453, 8.29, 2.89, -0.10),
    # Gemini
    ("Pollux", 7.755, 28.03, 1.14, 1.00), ("Castor", 7.577, 31.89, 1.58, 0.03), ("Alhena", 6.629, 16.40, 1.93, 0.00),
    ("Mebsuta", 6.732, 25.13, 3.06, 1.40), ("Tejat", 6.383, 22.51, 2.87, 1.60), ("Wasat", 7.335, 21.98, 3.53, 0.34),
    # Taurus, the Pleiades and the Hyades
    ("Aldebaran", 4.599, 16.51, 0.87, 1.54), ("Elnath", 5.438, 28.61, 1.65, -0.13), ("Alcyone", 3.791, 24.11, 2.87, -0.09),
    ("Atlas", 3.819, 24.05, 3.62, -0.07), ("Electra", 3.747, 24.11, 3.70, -0.11), ("Maia", 3.763, 24.37, 3.87, -0.07),
    ("Merope", 3.772, 23.95, 4.18, -0.06), ("Taygeta", 3.754, 24.47, 4.30, -0.11), ("Theta2 Tauri", 4.478, 15.87, 3.40, 0.18),
    ("Gamma Tauri", 4.330, 15.63, 3.65, 0.99), ("Delta Tauri", 4.382, 17.54, 3.76, 0.98), ("Ain", 4.477, 19.18, 3.53, 1.01),
    ("Zeta Tauri", 5.627, 21.14, 3.00, -0.19),
    # Auriga, Perseus
    ("Capella", 5.278, 46.00, 0.08, 0.80), ("Menkalinan", 5.992, 44.95, 1.90, 0.08), ("Mahasim", 5.995, 37.21, 2.65, -0.08),
    ("Hassaleh", 4.950, 33.17, 2.69, 1.53), ("Mirfak", 3.405, 49.86, 1.79, 0.48), ("Algol", 3.136, 40.96, 2.12, -0.05),
    # Ursa Major, Ursa Minor, Draco
    ("Dubhe", 11.062, 61.75, 1.79, 1.07), ("Merak", 11.031, 56.38, 2.37, 0.03), ("Phecda", 11.897, 53.69, 2.44, 0.00),
    ("Megrez", 12.257, 57.03, 3.31, 0.08), ("Alioth", 12.900, 55.96, 1.77, -0.02), ("Mizar", 13.399, 54.93, 2.27, 0.02),
    ("Alkaid", 13.792, 49.31, 1.86, -0.19), ("Polaris", 2.530, 89.26, 1.98, 0.60), ("Kochab", 14.845, 74.16, 2.08, 1.47),
    ("Pherkad", 15.345, 71.83, 3.05, 0.05), ("Eltanin", 17.943, 51.49, 2.24, 1.52), ("Rastaban", 17.507, 52.30, 2.79, 0.98),
    ("Thuban", 14.073, 64.38, 3.65, -0.05),
    # Cassiopeia, Andromeda, Pegasus
    ("Schedar", 0.675, 56.54, 2.24, 1.17), ("Caph", 0.153, 59.15, 2.28, 0.34), ("Gamma Cassiopeiae", 0.945, 60.72, 2.47, -0.15),
    ("Ruchbah", 1.430, 60.24, 2.68, 0.13), ("Segin", 1.907, 63.67, 3.37, -0.15), ("Alpheratz", 0.140, 29.09, 2.06, -0.11),
    ("Mirach", 1.162, 35.62, 2.05, 1.58), ("Almach", 2.065, 42.33, 2.10, 1.37), ("Markab", 23.079, 15.21, 2.49, -0.04),
    ("Scheat", 23.063, 28.08, 2.42, 1.67), ("Algenib", 0.221, 15.18, 2.83, -0.23), ("Enif", 21.736, 9.88, 2.38, 1.52),
    ("Hamal", 2.120, 23.46, 2.00, 1.15), ("Diphda", 0.727, -17.99, 2.04, 1.02),
    # Leo, Virgo, Bootes, Corona Borealis
    ("Regulus", 10.140, 11.97, 1.36, -0.11), ("Denebola", 11.818, 14.57, 2.14, 0.09), ("Algieba", 10.333, 19.84, 2.08, 1.13),
    ("Zosma", 11.235, 20.52, 2.56, 0.12), ("Chertan", 11.237, 15.43, 3.33, 0.00), ("Adhafera", 10.278, 23.42, 3.44, 0.31),
    ("Ras Elased", 9.764, 23.77, 2.98, 0.81), ("Eta Leonis", 10.122, 16.76, 3.48, -0.03), ("Spica", 13.420, -11.16, 0.97, -0.23),
    ("Porrima", 12.694, -1.45, 2.74, 0.36), ("Vindemiatrix", 13.036, 10.96, 2.83, 0.94), ("Arcturus", 14.261, 19.18, -0.05, 1.23),
    ("Izar", 14.750, 27.07, 2.37, 0.97), ("Muphrid", 13.911, 18.40, 2.68, 0.58), ("Seginus", 14.535, 38.31, 3.03, 0.19),
    ("Alphecca", 15.578, 26.71, 2.22, -0.02), ("Alphard", 9.460, -8.66, 1.98, 1.44),
    # The southern sky: Crux, Centaurus, Carina, Vela, Puppis
    ("Acrux", 12.443, -63.10, 0.76, -0.24), ("Mimosa", 12.795, -59.69, 1.25, -0.23), ("Gacrux", 12.519, -57.11, 1.59, 1.60),
    ("Delta Crucis", 12.252, -58.75, 2.79, -0.23), ("Rigil Kentaurus", 14.660, -60.83, -0.27, 0.71), ("Hadar", 14.064, -60.37, 0.61, -0.23),
    ("Menkent", 14.111, -36.37, 2.06, 1.01), ("Canopus", 6.399, -52.70, -0.74, 0.15), ("Miaplacidus", 9.220, -69.72, 1.67, 0.07),
    ("Avior", 8.375, -59.51, 1.86, 1.28), ("Suhail", 9.133, -43.43, 2.21, 1.66), ("Alsephina", 8.745, -54.71, 1.96, 0.04),
    ("Naos", 8.060, -40.00, 2.25, -0.27), ("Regor", 8.159, -47.34, 1.83, -0.22), ("Achernar", 1.629, -57.24, 0.46, -0.16),
    ("Atria", 16.811, -69.03, 1.91, 1.44), ("Peacock", 20.427, -56.74, 1.94, -0.20), ("Alnair", 22.137, -46.96, 1.74, -0.13),
    ("Fomalhaut", 22.961, -29.62, 1.16, 0.09),
    # Scorpius, Sagittarius, Ophiuchus
    ("Antares", 16.490, -26.43, 1.06, 1.83), ("Shaula", 17.560, -37.10, 1.62, -0.22), ("Sargas", 17.622, -42.99, 1.86, 0.40),
    ("Dschubba", 16.006, -22.62, 2.29, -0.12), ("Acrab", 16.091, -19.81, 2.56, -0.07), ("Pi Scorpii", 15.981, -26.11, 2.89, -0.19),
    ("Tau Scorpii", 16.598, -28.22, 2.82, -0.25), ("Larawag", 16.836, -34.29, 2.29, 1.15), ("Mu Scorpii", 16.864, -38.05, 3.00, -0.20),
    ("Lesath", 17.512, -37.30, 2.70, -0.22), ("Kappa Scorpii", 17.708, -39.03, 2.39, -0.17), ("Iota Scorpii", 17.793, -40.13, 3.03, 0.51),
    ("Kaus Australis", 18.403, -34.38, 1.85, -0.03), ("Nunki", 18.921, -26.30, 2.05, -0.13), ("Ascella", 19.044, -29.88, 2.60, 0.06),
    ("Kaus Media", 18.350, -29.83, 2.70, 1.38), ("Kaus Borealis", 18.466, -25.42, 2.81, 1.04), ("Alnasl", 18.097, -30.42, 2.98, 1.00),
    ("Phi Sagittarii", 18.761, -26.99, 3.17, -0.11), ("Tau Sagittarii", 19.115, -27.67, 3.32, 1.19), ("Rasalhague", 17.582, 12.56, 2.08, 0.15),
    # The summer triangle: Lyra, Cygnus, Aquila
    ("Vega", 18.616, 38.78, 0.03, 0.00), ("Sheliak", 18.835, 33.36, 3.52, 0.00), ("Sulafat", 18.982, 32.69, 3.24, -0.05),
    ("Deneb", 20.690, 45.28, 1.25, 0.09), ("Sadr", 20.370, 40.26, 2.23, 0.67), ("Gienah", 20.770, 33.97, 2.48, 1.03),
    ("Albireo", 19.512, 27.96, 3.08, 1.09), ("Delta Cygni", 19.750, 45.13, 2.87, -0.03), ("Altair", 19.846, 8.87, 0.76, 0.22),
    ("Tarazed", 19.771, 10.61, 2.72, 1.52), ("Alshain", 19.922, 6.41, 3.71, 0.86),
]


def colour(bv):
    """Approximate star colour from its B-V index: blue-white hot stars to orange-red giants."""
    if bv is None:
        return 1.0, 1.0, 1.0
    t = 4600.0 * (1.0 / (0.92 * bv + 1.7) + 1.0 / (0.92 * bv + 0.62))   # Ballesteros' formula, kelvin
    # Rough blackbody-to-sRGB for 2500-30000 K, normalised to the brightest channel.
    t100 = t / 100.0
    r = 1.0 if t100 <= 66 else min(1.0, 1.29293618 * (t100 - 60) ** -0.1332047592)
    g = (0.39008157 * math.log(t100) - 0.63184144) if t100 <= 66 else 1.12989086 * (t100 - 60) ** -0.0755148492
    b = 1.0 if t100 >= 66 else (0.0 if t100 <= 19 else 0.54320679 * math.log(t100 - 10) - 1.19625409)
    r, g, b = (max(0.0, min(1.0, c)) for c in (r, g, b))
    m = max(r, g, b)
    return r / m, g / m, b / m



def equatorial(ra_hours, dec_deg):
    """Unit vector in the equatorial frame: X towards RA 0 on the equator, Y towards RA 6 h, Z the north celestial pole."""
    a = math.radians(ra_hours * 15.0)
    d = math.radians(dec_deg)
    return math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)


def hlsl_table():
    """HLSL declarations: STAR_DIR[n] = (equatorial direction, flux relative to magnitude 0), STAR_COL[n]."""
    dirs, cols = [], []
    for name, ra, dec, mag, bv in STARS:
        x, y, z = equatorial(ra, dec)
        flux = 10.0 ** (-0.4 * mag)
        dirs.append(f"float4({x:.5f}, {y:.5f}, {z:.5f}, {flux:.4f})")
        r, g, b = colour(bv)
        cols.append(f"float3({r:.3f}, {g:.3f}, {b:.3f})")
    count = len(STARS)
    nl = "\n"
    return (f"static const int STAR_COUNT = {count};{nl}"
            f"static const float4 STAR_DIR[{count}] = {{ {', '.join(dirs)} }};{nl}"
            f"static const float3 STAR_COL[{count}] = {{ {', '.join(cols)} }};{nl}")


if __name__ == "__main__":
    print(len(STARS), "stars")
