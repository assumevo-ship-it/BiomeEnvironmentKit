
struct WeatherField
{
    float Hash(int2 p, int seed)
    {
        uint h = uint(p.x) * 374761393u + uint(p.y) * 668265263u + uint(seed) * 2246822519u;
        h = (h ^ (h >> 13)) * 1274126177u;
        return float((h ^ (h >> 16)) & 0x00ffffffu) / 16777215.0;
    }
    float Noise(float2 p, int seed)
    {
        int2 cell = int2(floor(p));
        float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(cell, seed), Hash(cell + int2(1,0), seed), f.x),
                    lerp(Hash(cell + int2(0,1), seed), Hash(cell + int2(1,1), seed), f.x), f.y);
    }
};
WeatherField field;
float2 wp = (Pos.xy - Wind.xy) / 100.0 / 5000.0;
int seed = int(State.y);
float front = saturate(0.7 * field.Noise(wp, seed) + 0.3 * field.Noise(wp * 2.31 + float2(7.1,-3.7), seed + 17));
float cell = field.Noise(wp * 3.17 + float2(-2.4,8.3), seed + 53);
// The host air mass can cover the map uniformly or organize into moving dry/wet sectors.
float contrast = smoothstep(0.32,0.68,field.Noise(float2(State.z/720.0,0.0),seed+613));
float moisture = smoothstep(0.30,0.64,front);
float cloudFraction = lerp(1.0+(front-0.5)*0.12,moisture,contrast);
float cellHere = 1.0;
float cover = State.w > 0.5 ? Coverage : clamp((Climate.x*cloudFraction+0.0*Climate.x)*lerp(0.72,1.0,cellHere),0.0,0.99);
float conv = Climate.y * lerp(0.90+0.10*moisture,moisture,contrast) * lerp(0.4,1.0,cellHere);
float precip = Climate.z * cellHere;
float storm = smoothstep(0.36,0.95,conv) * (0.65 + 0.35 * smoothstep(0.28,0.68,cell));
float anvilAmount = smoothstep(0.48,0.95,conv);
float highCover = saturate(Climate.w*lerp(1.0,smoothstep(0.28,0.62,front),contrast));
float h = saturate(Alt);
float z = h * 11200.0;                     // height above the 800 m shell base
float2 drift = (Pos.xy - Wind.xy) / 100.0;
float2 flow = length(Wind.zw) > 0.01 ? normalize(Wind.zw) : float2(1.0, 0.0);
float2 crossFlow = float2(-flow.y,flow.x);
// A distant cloud cannot resolve the same metre-scale detail as a nearby cloud.
// Filter the volume before integration rather than letting temporal reconstruction
// turn undersampled extinction into a noisy surface at the horizon.
float cameraRange = length(Pos.xyz-CameraWorld.xyz)/100.0;
float footprint = max(2.0,4.0*cameraRange/max(1.0,abs(View.ViewToClip[0][0])*View.ViewSizeAndInvSize.x));
float detailVisibility = 1.0-smoothstep(12.0,60.0,footprint);
uint shapeWidth, shapeHeight, shapeDepth, shapeLevels;
uint detailWidth, detailHeight, detailDepth, detailLevels;
Shape.GetDimensions(0,shapeWidth,shapeHeight,shapeDepth,shapeLevels);
Detail.GetDimensions(0,detailWidth,detailHeight,detailDepth,detailLevels);
float shapeMip = clamp(log2(max(1.0,footprint*float(shapeWidth)/3600.0)),0.0,float(shapeLevels-1));
float lobeMip = clamp(log2(max(1.0,footprint*float(shapeWidth)/1400.0)),0.0,float(shapeLevels-1));
float erosionMip = clamp(log2(max(1.0,footprint*float(detailWidth)/350.0)),0.0,float(detailLevels-1));
float microMip = clamp(log2(max(1.0,footprint*float(detailWidth)/160.0)),0.0,float(detailLevels-1));

// Wind shear bends rising towers and advects ice at a different speed to the low cloud field.
float2 shear = flow * z * (0.10 + conv * 0.22) + crossFlow * z * 0.06;
float2 xy = drift - shear;
float lowDensity = 0.0, scud = 0.0, fine = 0.5, normalizedHeight = 1.0;
// How much of a rain-laden storm deck is overhead (gloom) and how heavy the deck is at this spot (heavy); see below.
float gloom = 0.0, heavy = 0.5;
// Skip the entire low-cloud model in the upper ice band. The bound includes the
// maximum cell height, outline displacement and base-height variation.
float lowCeiling = lerp(650.0,120.0,smoothstep(0.45,0.9,cover)) + 275.0
    + lerp(1600.0,9800.0,conv)*1.5 + 400.0;
[branch] if (cover > 0.0 && z <= lowCeiling)
{
float2 rotatedXY = float2(xy.x*0.83-xy.y*0.56,xy.x*0.56+xy.y*0.83);
float weather = field.Noise(xy/6200.0,seed+631)*0.50
    + field.Noise(rotatedXY/2600.0+float2(4.1,-7.3),seed+683)*0.30
    + field.Noise(xy/1100.0+float2(-8.2,3.7),seed+719)*0.20;
float capNoise = field.Noise(xy/3200.0+float2(2.9,7.4),seed+757);
// Fair cumulus groups have blue-sky openings; rain air masses merge into a lower stratiform deck.
float deckAmount = smoothstep(0.55,0.9,cover) * (0.35 + 0.65 * precip);
// A storm's rain deck is not an even grey lid: seen from below it is dark, heavy and textured, broad rolls lying across
// the wind with thinner troughs between them and lumpy cells sagging out of its base. The heavy parts hang lower and
// are shaded darker (less light gets through them), the thin parts let the light through.
gloom = deckAmount * max(smoothstep(0.25,0.75,precip), smoothstep(0.2,0.6,conv));
// Cells a few hundred metres across, as seen in photographs of a storm base (kilometre-wide ones read as a smooth
// gradient overhead), in rolls across the wind.
float2 rollUV = float2(dot(xy,flow)/900.0, dot(xy,crossFlow)/3500.0);
float rolls = field.Noise(rollUV,seed+911)*0.6 + field.Noise(rollUV*2.7+float2(3.1,-1.7),seed+937)*0.4;
float lumps = field.Noise(xy/420.0+float2(-5.3,2.2),seed+953)*0.65 + field.Noise(xy/160.0+float2(1.9,-6.1),seed+971)*0.35;
heavy = saturate(rolls*0.65 + lumps*0.5 - 0.08);
// Far off an overcast ends: towards the horizon the low cloud thins away (whatever the rain) and the grey sky beyond
// it shows as a pale band under the clouds. (Left whole, the deck seen edge-on drew a dark wall along the horizon,
// with the far sea under it standing out as a bright line.) The fade starts beyond the archipelago (the same density
// casts the cloud shadows, and fading it nearer lit the far islands like a sunny day under the storm) and is over by
// 12 km: a long half-thinned stretch let the sun through and tinted the band warm, like a line of sunlit hills.
// (Under a storm's air mass too, outside its cell where the local cover is thinner: the far deck's base otherwise
// lay along the horizon as a hard dark band above a bright strip.)
float deckEdge = lerp(1.0, 0.0, smoothstep(6000.0, 12000.0, cameraRange) * smoothstep(0.6, 0.9, max(cover, Climate.x * 0.0)) * 1.0);
float baseHeight = lerp(650.0,120.0,smoothstep(0.45,0.9,cover));
baseHeight += (capNoise - 0.5) * lerp(160.0,550.0,storm);
baseHeight -= (heavy - 0.5) * 700.0 * gloom;
float lowTop = baseHeight + lerp(650.0,2000.0,saturate(cover + conv * 0.35));
float thickness = lerp(700.0+capNoise*1400.0,4500.0+capNoise*5300.0,smoothstep(0.14,0.95,conv));
float top = baseHeight+thickness;
float baseRamp = smoothstep(baseHeight,baseHeight + 180.0,z);

// The cloud is a continuous condensed volume, not a field of closed puff primitives.
// Seeded humidity banks supply the broad mass; warped 3D noise shapes the interior
// and silhouette together, allowing ridges, connected banks and unequal updrafts.
float3 p = float3(xy,z + 800.0);
float4 warp = Texture3DSampleLevel(Shape, ShapeSampler,p/float3(4800.0,4800.0,3600.0),shapeMip);
float3 warped = p+(warp.gba-0.5)*float3(1200.0,1200.0,550.0);
float4 shape = Texture3DSampleLevel(Shape, ShapeSampler,warped/float3(3300.0,3300.0,2100.0),shapeMip);
float4 lobes = Texture3DSampleLevel(Shape, ShapeSampler,warped/1400.0+float3(0.17,0.53,Time*0.00013),lobeMip);
// A third, finer billow octave (a few hundred metres) gives each tower the distinct lumpy cauliflower structure of real cumulus.
float4 bumps = Texture3DSampleLevel(Shape, ShapeSampler,warped/620.0+float3(0.41,0.09,Time*0.00021),lobeMip);
float billows = shape.r*0.60+lobes.r*0.26+bumps.r*0.14;
float threshold = lerp(0.82,0.18,cover);
float bankAmount = smoothstep(threshold-0.25,threshold+0.02,weather)*smoothstep(0.0,0.12,cover);
float heightProfile = baseRamp*(1.0-smoothstep(baseHeight+thickness*0.45,top,z));
float cloudMask = bankAmount*heightProfile;
float deckProfile = baseRamp * (1.0-smoothstep(lowTop-500.0,lowTop,z));
float deck = deckAmount * deckProfile * saturate((billows-0.32)/0.5) * (0.45+0.55*weather);
float cumulus = smoothstep(0.72-cloudMask*0.50,0.92-cloudMask*0.50,billows)*cloudMask;
float density = max(cumulus,deck);
// The storm texture applies to whatever cloud forms the base (stratiform deck or the storm cloud itself).
density *= lerp(1.0, lerp(0.15, 2.6, heavy), gloom);
// Condensed bases stay broad and solid. Towers have visibly changing cauliflower rims.
float4 erosion = 0.5, micro = 0.5;
[branch] if (detailVisibility > 0.001)
{
    erosion = Texture3DSampleLevel(Detail, DetailSampler,
        p / float3(450.0,450.0,350.0) + float3(Time * 0.0007,Time * -0.0003,0),erosionMip);
    float3 microUV = float3(dot(xy,flow)/360.0,dot(xy,crossFlow)/160.0,(z+800.0)/220.0);
    micro = Texture3DSampleLevel(Detail, DetailSampler,
        microUV + float3(Time*0.0009,Time*-0.0004,Time*0.0002),microMip);
}
fine = dot(erosion.rgb,float3(0.625,0.25,0.125));
float fineDetail = dot(micro.rgb,float3(0.625,0.25,0.125));
normalizedHeight = saturate((z-baseHeight)/max((deck > cumulus ? lowTop : top)-baseHeight,1.0));
float edgeErosion = lerp(fine,1.0-fine,smoothstep(0.3,0.95,normalizedHeight));
edgeErosion = edgeErosion*0.75 + fineDetail*0.25;
edgeErosion *= lerp(0.10,0.24,normalizedHeight) * (1.0 - saturate(density) * 0.86) * detailVisibility;
edgeErosion *= 0.35+0.65*sqrt(saturate(1.0-cloudMask));
density = saturate((density - edgeErosion) / max(1.0-edgeErosion,0.1));
// Real cumulus has a firm, bright body that thins to a translucent fringe: bend the profile so cores are solid and rims feather.
density = lerp(density, density*density*(3.0-2.0*density), 0.55 * (1.0 - gloom));
// Thin evaporating shreds soften a few outer edges; the dense body still has a
// readable rim. Anisotropic detail stretches the shreds along the wind.
float wisps = smoothstep(0.08,0.28,cloudMask)*(1.0-smoothstep(0.30,0.55,cloudMask))
    * smoothstep(0.60,0.82,lobes.r)*smoothstep(0.32,0.75,micro.r)
    * baseRamp*(1.0-deckAmount)*0.012*detailVisibility;
density += wisps;
// Convective water stays below the tropopause; the separate ice field forms the anvil.
density *= 1.0-smoothstep(10100.0,11200.0,z);
lowDensity = density * lerp(0.68,1.4,storm) * deckEdge;

// Ragged fragments underneath a storm's rain base.
float scudProfile = smoothstep(15.0,160.0,z) * (1.0 - smoothstep(450.0,900.0,z));
// Dark ragged scud hangs under any rain deck, thicker in a thunderstorm.
scud = scudProfile * max(storm, gloom) * deckAmount * smoothstep(0.55,0.85,lobes.r) * 0.35 * deckEdge;
}

// Cumulonimbus ice spreads downwind into a broad, flatter anvil with frayed edges.
float anvil = 0.0;
float anvilHeight = lerp(6400.0,9600.0,conv);
[branch] if (anvilAmount > 0.0 && z > anvilHeight-1100.0 && z < anvilHeight+1000.0)
{
float2 iceXY = drift - flow * (Time * 3.5 + z * 0.5);
float2 iceUV = float2(dot(iceXY,flow) / 6500.0,dot(iceXY,crossFlow) / 2500.0);
float iceMap = field.Noise(iceUV + 4.7, seed + 89);
float4 iceShape = Texture3DSampleLevel(Shape, ShapeSampler, float3(iceUV,z / 750.0),0);
float anvilProfile = smoothstep(anvilHeight-1100.0,anvilHeight-200.0,z)
    * (1.0 - smoothstep(anvilHeight+300.0,anvilHeight+1000.0,z));
float anvilMask = smoothstep(0.36,0.64,iceMap + cell * 0.15);
anvil = anvilProfile * anvilAmount * anvilMask
    * saturate((iceShape.r - 0.32 - fine * 0.10) / 0.55) * 0.48;
}

// Optically thin, fibrous cirrus in its own high band, leaving the blue sky visible through it.
float cirrus = 0.0;
[branch] if (z > 8800.0 && z < 11100.0 && highCover > 0.0)
{
float2 cirrusXY = drift - flow * Time * 5.0;
// Non-periodic coverage gates the ice into separate banks. A uniformly tiled,
// stretched volume texture projects into conspicuous repeating sky streaks.
float2 patchXY = float2(cirrusXY.x*0.83-cirrusXY.y*0.56,cirrusXY.x*0.56+cirrusXY.y*0.83);
float patchNoise = field.Noise(cirrusXY/24000.0,seed+419)*0.65
    + field.Noise(patchXY/11300.0+float2(7.3,-2.9),seed+467)*0.35;
float iceBank = smoothstep(0.50-highCover*0.12,0.73-highCover*0.10,patchNoise);
float iceCenter = 9800.0+(patchNoise-0.5)*700.0;
float cirrusProfile = smoothstep(iceCenter-500.0,iceCenter-100.0,z)
    * (1.0-smoothstep(iceCenter+250.0,iceCenter+650.0,z));
[branch] if (iceBank > 0.001 && cirrusProfile > 0.0)
{
    float veer = field.Noise(cirrusXY/47000.0,seed+509)-0.5;
    float2 iceFlow = normalize(flow+crossFlow*veer*0.65);
    float2 iceAcross = float2(-iceFlow.y,iceFlow.x);
    float2 iceLocal = float2(dot(cirrusXY,iceFlow),dot(cirrusXY,iceAcross));
    float4 warp = Texture3DSampleLevel(Shape, ShapeSampler,float3(cirrusXY/8500.0,z/2200.0),0);
    iceLocal += (warp.gb-0.5)*float2(1500.0,700.0);
    float4 fiberA = Texture3DSampleLevel(Shape, ShapeSampler,float3(iceLocal/float2(11000.0,2500.0),z/900.0),0);
    float2 crossed = float2(iceLocal.x*0.94+iceLocal.y*0.34,iceLocal.y*0.94-iceLocal.x*0.34);
    float4 fiberB = Texture3DSampleLevel(Shape, ShapeSampler,
        float3(crossed/float2(6800.0,4300.0),z/1700.0)+float3(-0.53,0.27,0.82),0);
    float fibers = smoothstep(0.58,0.84,fiberA.r*0.60+fiberB.r*0.40)
        * smoothstep(0.30,0.72,fiberA.g*0.5+fiberB.b*0.5);
    cirrus = cirrusProfile*iceBank*fibers*highCover*(0.0012+highCover*0.0035);
}
}

float total = max(lowDensity + scud,anvil) + cirrus;
float ao = lerp(0.50,1.0,smoothstep(0.03,0.75,normalizedHeight)) * (1.0 - storm * 0.32);
// The heavy parts of a storm deck are shaded darker from below, the thin troughs lighter.
ao *= lerp(1.0, lerp(1.3, 0.15, heavy), gloom);
ao = lerp(ao,0.93,saturate((anvil+cirrus)/max(total,0.0001)));
// A nearby strike illuminates the volume from within, including its occluded bases.
float flashDistance = length((Pos.xyz - Lightning.xyz) / float3(90000.0,90000.0,220000.0));
float flash = Lightning.w * exp(-flashDistance * flashDistance * 1.5) * total * 45.0;
// A storm base reads as texture because its heavy parts send back less light than the thin ones: under kilometres of
// cloud the base is lit almost only by light scattered through the whole mass (so density and ambient occlusion alone
// change nothing a camera can see), and the heavy cells, laden with rain and larger drops, return less of it.
// Under a deck the light is grey, not the clear sky's blue the sky light captures above it: a faintly warm albedo
// cancels that cast in a storm.
Albedo = lerp(float3(0.98,0.98,0.98), lerp(1.0, 0.4, heavy) * float3(1.0, 0.94, 0.84), gloom) ;
return float3(total,ao,flash);
