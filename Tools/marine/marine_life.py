"""Sea life meshes, procedural: reef corals, sponges, weed, kelp, sea grass, reef rock, urchins, floating sargassum and a
fish. Written as GLB to Build/Marine, imported by Tools/marine/build_marine_assets.py into /BiomeAutoMaterials/Marine.

Vertex colour (read by M_SeaLife): R how far the sea sways it (0 at the root, 1 at a free tip), G cavity (dark in grooves),
B share of the species' second colour, A polyp pattern strength. Sizes are real, in metres, Z up, the root at the origin.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Build/Marine'


def noise(p, f, seed=0.0):
    """Cheap smooth value noise from sines: only has to be irregular, and is a pure function of the position."""
    p = p*f+seed
    return (np.sin(p[:, 0]*1.7+np.sin(p[:, 1]*2.3))+np.sin(p[:, 1]*1.9+np.sin(p[:, 2]*2.1))+np.sin(p[:, 2]*2.2+np.sin(p[:, 0]*1.6)))/3


class Mesh:
    def __init__(self):
        self.p, self.c, self.t, self.n = [], [], [], 0

    def add(self, pos, col, tris):
        self.p.append(pos.astype('f4'))
        self.c.append(col.astype('f4'))
        self.t.append(np.asarray(tris, 'u4')+self.n)
        self.n += len(pos)

    def arrays(self):
        p, c, t = np.concatenate(self.p), np.concatenate(self.c), np.concatenate(self.t)
        # Smooth normals, area weighted, then shared by position so that a tube's seam does not show.
        a, b, d = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
        fn = np.cross(b-a, d-a)
        n = np.zeros_like(p)
        for i in range(3):
            np.add.at(n, t[:, i], fn)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        # Where it meets the bed the light is shut out: without this everything looks stood on the sand, not grown from it.
        size = max(float(p[:, 2].max()-p[:, 2].min()), .02)
        c = c.copy()
        c[:, 1] *= .5+.5*np.clip((p[:, 2]-p[:, 2].min())/min(size*.3, .35), 0, 1)
        return p, n, c, t


def grid_tris(rows, cols, wrap=True):
    t = []
    for i in range(rows-1):
        for j in range(cols if wrap else cols-1):
            a, b = i*cols+j, i*cols+(j+1) % cols
            d, e = a+cols, b+cols
            t += [(a, d, b), (b, d, e)]
    return t


def dome(res=48):
    """A unit half dome, bottom open: (x, y, z) with z >= 0, and the same for the base skirt that goes into the ground."""
    th = np.linspace(0, np.pi*.62, res)      # a little past the equator: the base curls under, into the sand
    ph = np.linspace(0, np.pi*2, res*2, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    return np.stack([np.sin(T)*np.cos(P), np.sin(T)*np.sin(P), np.cos(T)], -1).reshape(-1, 3), res, res*2


def col(n, sway=0.0, cav=1.0, second=0.0, pattern=0.0):
    c = np.zeros((n, 4), 'f4')
    c[:, 0], c[:, 1], c[:, 2], c[:, 3] = sway, cav, second, pattern
    return c


def tube(m, path, radii, sides=6, sway=None, second=0.0, pattern=0.0, cap=True):
    """A tapering tube along a polyline, with a frame carried along it. Tip closed, foot open (it is in the rock)."""
    path = np.asarray(path, 'f4')
    radii = np.asarray(radii, 'f4')
    n = len(path)
    tan = np.gradient(path, axis=0)
    tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-6)
    ref = np.array((.31, .77, .55), 'f4')
    a = np.cross(tan[0], ref)
    a /= np.linalg.norm(a)
    pos = []
    for i in range(n):
        a = a-tan[i]*(a @ tan[i])
        a /= max(np.linalg.norm(a), 1e-6)
        b = np.cross(tan[i], a)
        for s in range(sides):
            q = s/sides*np.pi*2
            pos.append(path[i]+(a*np.cos(q)+b*np.sin(q))*radii[i])
    pos = np.array(pos, 'f4')
    tris = grid_tris(n, sides)
    w = np.repeat(np.asarray(sway if sway is not None else np.zeros(n), 'f4'), sides)
    c = col(len(pos), 0, 1, second, pattern)
    c[:, 0] = w
    # Darker low down, where little light gets in among the branches.
    c[:, 1] = np.repeat(np.linspace(.6, 1, n), sides)
    if cap:
        tip = len(pos)
        pos = np.vstack([pos, path[-1]+tan[-1]*radii[-1]*.8])
        c = np.vstack([c, c[-1:]])
        for s in range(sides):
            tris.append(((n-1)*sides+s, tip, (n-1)*sides+(s+1) % sides))
    m.add(pos, c, tris)


def blade(m, path, width, sway, second=0.0, rows=None):
    """A ribbon: a flat leaf with some thickness of shape from its midrib crease. Two-sided in the material."""
    path = np.asarray(path, 'f4')
    n = len(path)
    tan = np.gradient(path, axis=0)
    tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-6)
    side = np.cross(tan, np.array((.3, .9, .1), 'f4')+.4*np.sin(np.arange(n)*.9)[:, None]*np.array((1, 0, 0), 'f4'))
    side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-6)
    nor = np.cross(side, tan)
    width = np.asarray(width, 'f4')[:, None]
    pos = np.stack([path-side*width, path+nor*width*.25, path+side*width], 1).reshape(-1, 3)
    c = col(len(pos), 0, 1, second)
    c[:, 0] = np.repeat(np.asarray(sway, 'f4'), 3)
    c[:, 1] = np.repeat(np.linspace(.65, 1, n), 3)
    m.add(pos, c, grid_tris(n, 3, wrap=False))


# ------------------------------------------------------------------------------- hard corals

def brain_coral(rng):
    """A boulder of Diploria: meandering ridges a couple of centimetres across, real relief, dark in the valleys."""
    m = Mesh()
    p, r, c = dome(96)
    q = p*np.array((.62, .55, .46))
    q += p*(.07*noise(p, 2.1, 3.0)[:, None])
    # A meander from the interference of warped sines: ridges that wander and fork.
    warp = 1.4*noise(p, 3.4, 7.0)
    ridge = np.sin(p[:, 0]*23+warp*5)+np.sin(p[:, 1]*23-warp*4)+np.sin(p[:, 2]*23+warp*6)
    h = np.abs(ridge)
    h = 1-np.clip(h/1.3, 0, 1)
    q += p*(.018*h)[:, None]
    cc = col(len(q), 0, .45+.55*h, np.clip(.5+noise(p, 1.5, 11.0), 0, 1), .2)
    m.add(q, cc, grid_tris(r, c))
    return m


def boulder_coral(rng):
    """Porites: a lumpy mound of knobs, the commonest thing on a reef and what most of it is built on."""
    m = Mesh()
    p, r, c = dome(72)
    knob = noise(p, 7.3, 2.0)*.5+.5*noise(p, 15.0, 9.0)
    big = noise(p, 2.2, 5.0)
    q = p*np.array((.9, .8, .62))
    q += p*(.16*big+.075*knob)[:, None]
    m.add(q, col(len(q), 0, np.clip(.45+knob*1.2, 0, 1), np.clip(.5+big, 0, 1), .9), grid_tris(r, c))
    return m


def table_coral(rng):
    """Acropora table, as photographed: one stout foot, a flat plate a metre or so across made of fused radiating branches,
    thick in the middle and thin at the rim, its top furred with short upright branchlets, the rim of free branch tips a
    little upturned, the underside showing the radiating branches. A second, smaller tier sometimes. The plate surface
    and the branchlets come from one function, so every branchlet stands in it. (The old plate was a rippled sheet with
    sticks above it, 45 of them floating; the 2026-11-11 review saw a spiky white sheet.)"""
    m = Mesh()
    tiers = [(0.0, 0.0, .42, rng.uniform(.6, .85))]
    if rng.random() < .55:
        tiers.append((rng.uniform(.2, .32), rng.uniform(-.2, .2), .26, rng.uniform(.3, .45)))
    for ti, (cx, cy, z0, R) in enumerate(tiers):
        tube(m, [(cx*.6, cy*.6, -.12), (cx*.85+.01, cy*.85, z0*.55), (cx, cy, z0-.02)], [.15*R/.7, .1*R/.7, .085*R/.7], 10, second=.15)
        lob = rng.uniform(0, 6.3, 3)

        def edge(a):
            return 1+.12*np.sin(a*5+lob[0])+.07*np.sin(a*9+lob[1])+.04*np.sin(a*17+lob[2])

        def top(rad, a):
            # Nearly flat, a gentle rise towards the rim (they grow up into the light at the edge).
            return z0+.05*R*(rad/R)**2+.012*np.sin(a*7+lob[1])*(rad/R)

        def thick(rad):
            return .07*R*np.clip(1-rad/(R*1.25), 0, 1)**1.5+.014
        # One closed surface: top from the middle to the rim, round the rim, then the underside back to the foot.
        nr, na = 16, 64
        u = np.linspace(0, 1, nr)
        A = np.linspace(0, np.pi*2, na, endpoint=False)
        rows = []
        for half in (0, 1):
            for uu in (u if half == 0 else u[::-1]):
                rad = uu*R*edge(A)
                zt = top(rad, A)
                z = zt if half == 0 else zt-thick(rad)-.008*np.clip(np.sin(A*38+lob[0]), 0, 1)*uu
                rows.append(np.stack([cx+rad*np.cos(A), cy+rad*np.sin(A), z], 1))
        q = np.concatenate(rows)
        cc = col(len(q), 0, 1, 0, .9)
        rr = np.concatenate([np.full(na, uu) for uu in list(u)+list(u[::-1])])
        cc[:, 2] = rr**2          # paler, younger at the growing edge
        cc[:, 1] = np.concatenate([np.full(na, .95 if k < nr else .55) for k in range(2*nr)])
        m.add(q, cc, grid_tris(2*nr, na))
        # Branchlets: short, stout, upright, crowded (corymbose); stood in the top surface.
        count = int(520*(R/.75)**2)
        for _ in range(count):
            a = rng.uniform(0, np.pi*2)
            t = np.sqrt(rng.uniform(.01, .97))
            rad = t*R*edge(np.array([a]))[0]
            bz = float(top(np.array([rad]), np.array([a]))[0])
            L = rng.uniform(.018, .045)*(.7+.5*t)
            bx, by = cx+rad*np.cos(a), cy+rad*np.sin(a)
            out = .25*t
            tube(m, [(bx, by, bz-.008), (bx+np.cos(a)*out*L, by+np.sin(a)*out*L, bz+L)], [.0075, .0055], 4, second=float(t), pattern=.8)
        # The rim: free branch tips reaching out and a little up.
        nrim = int(70*R/.75)
        for k in range(nrim):
            a = (k+rng.uniform(-.3, .3))/nrim*np.pi*2
            rad = R*edge(np.array([a]))[0]*.9
            bz = float(top(np.array([rad]), np.array([a]))[0])-.01
            L = rng.uniform(.03, .06)
            bx, by = cx+rad*np.cos(a), cy+rad*np.sin(a)
            tube(m, [(bx, by, bz), (bx+np.cos(a)*L, by+np.sin(a)*L, bz+L*.35)], [.007, .004], 4, second=1.0, pattern=.6)
    return m


def staghorn(rng):
    """Acropora cervicornis: forked antlers, pale at the growing tips."""
    m = Mesh()

    def grow(at, d, r, depth):
        L = rng.uniform(.18, .34)
        n = 5
        pts, rr = [at], [r]
        for i in range(n):
            d = d+rng.normal(0, .11, 3)+np.array((0, 0, .05))
            d /= np.linalg.norm(d)
            pts.append(pts[-1]+d*L/n)
            rr.append(r*(1-.28*(i+1)/n))
        tube(m, pts, rr, 5, second=float(np.clip(1-depth/5, 0, 1)), pattern=.9, cap=depth > 3)
        if depth <= 0:
            return
        for k in range(2 if rng.random() < .75 else 3):
            s = rng.normal(0, .6, 3)
            grow(pts[-1], d+s, rr[-1]*.86, depth-1)

    for _ in range(6):
        a = rng.uniform(0, np.pi*2)
        grow(np.array((np.cos(a)*.08, np.sin(a)*.08, -.05)), np.array((np.cos(a)*.6, np.sin(a)*.6, 1.0)), .03, 4)
    return m


def sea_fan(rng):
    """Gorgonia: a flat purple net fanning from one foot, set across the current, the whole of it swaying."""
    m = Mesh()

    def grow(at, heading, r, depth, h):
        L = rng.uniform(.1, .2)
        pts, rr, w = [at], [r], [h]
        for i in range(4):
            heading = heading+rng.normal(0, .12)
            pts.append(pts[-1]+np.array((np.sin(heading), rng.normal(0, .006), np.cos(heading)))*L/4)
            rr.append(rr[-1]*.93)
            w.append(min(1.0, pts[-1][2]/1.1))
        tube(m, pts, rr, 4, sway=w, second=float(1-depth/6), pattern=.25, cap=depth == 0)
        if depth > 0:
            for s in (-1, 1):
                grow(pts[-1], heading+s*rng.uniform(.18, .5), rr[-1]*.9, depth-1, w[-1])

    for a in (-.55, -.18, .2, .6):
        grow(np.array((0, 0, -.03)), a, .014, 6, 0.0)
    return m


def sponges(rng):
    """Barrel and tube sponges: hollow, thick-walled, open at the top, the rim rounded."""
    m = Mesh()
    for k in range(int(rng.integers(3, 6))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(.05, .22)
        bx, by = np.cos(a)*d, np.sin(a)*d
        H, R = rng.uniform(.35, .85), rng.uniform(.07, .13)
        lean = rng.normal(0, .05, 2)
        s = np.linspace(0, 1, 18)
        ph = np.linspace(0, np.pi*2, 18, endpoint=False)
        S, P = np.meshgrid(s, ph, indexing='ij')
        # Outside up, over the rim, down into the hollow.
        out = S < .72
        v = np.where(out, S/.72, 1-(S-.72)/.28*.8)
        rad = np.where(out, R*(.75+.45*v**.5), R*(1.2-.5*(S-.72)/.28))
        rad = rad*(1+.05*np.sin(P*7+S*9))
        z = H*v-.04
        x = bx+lean[0]*z+rad*np.cos(P)
        y = by+lean[1]*z+rad*np.sin(P)
        q = np.stack([x, y, z], -1).reshape(-1, 3)
        cc = col(len(q), 0, 1, float(k % 2), .5)
        cc[:, 1] = np.where(out, 1, np.clip(1-(S-.72)/.28*1.2, .1, 1)).reshape(-1)
        m.add(q, cc, grid_tris(18, 18))
    return m


# ------------------------------------------------------------------------------- plants

def _frond(at, d, L, n, rng, curl=.12, up=.06):
    pts = [np.array(at, 'f4')]
    d = np.array(d, 'f4')
    for _ in range(n):
        d = d+rng.normal(0, curl, 3)+np.array((0, 0, up))
        d /= np.linalg.norm(d)
        pts.append(pts[-1]+d*L/n)
    return np.array(pts)


def sea_grass(rng):
    """Turtle grass: a tuft of flat strap leaves a hand wide at most, bending over at the tips."""
    m = Mesh()
    for _ in range(26):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, .22)
        L = rng.uniform(.22, .5)
        pts = _frond((np.cos(a)*d, np.sin(a)*d, -.03), (np.cos(a)*.2, np.sin(a)*.2, 1), L, 6, rng, curl=.1, up=-.02)
        t = np.linspace(0, 1, len(pts))
        blade(m, pts, .0065*(1.1-.5*t), t**1.4, second=float(rng.random() < .25))
    return m


def weed_bush(rng):
    """Brown Sargassum on a rock: thin wiry stems with narrow leaves and air bladders, a low swaying bush."""
    m = Mesh()
    for _ in range(9):
        a = rng.uniform(0, np.pi*2)
        L = rng.uniform(.5, 1.25)
        pts = _frond((np.cos(a)*.05, np.sin(a)*.05, -.03), (np.cos(a)*.3, np.sin(a)*.3, 1), L, 9, rng, curl=.14)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .005*(1.2-.7*t), 3, sway=t**1.3, second=.0, cap=False)
        for i in range(2, len(pts)):
            for _ in range(3):
                d = np.array((rng.normal(), rng.normal(), rng.uniform(-.2, .8)))
                d /= np.linalg.norm(d)
                leaf = pts[i]+np.linspace(0, 1, 4)[:, None]*d*rng.uniform(.05, .1)
                blade(m, leaf, np.array((.002, .009, .009, .001)), np.full(4, t[i]), second=float(rng.random()*.6))
            if rng.random() < .3:
                tube(m, [pts[i], pts[i]+(.018, 0, .004)], [.006, .007], 4, sway=[t[i], t[i]], second=1.0)
    return m


def kelp(rng):
    """Giant kelp for cold water: a long stipe with a blade at each joint, reaching for the light. Metres tall."""
    m = Mesh()
    for k in range(4):
        a = rng.uniform(0, np.pi*2)
        L = rng.uniform(3.8, 7.5)
        n = 20
        pts = _frond((np.cos(a)*.12, np.sin(a)*.12, -.05), (np.cos(a)*.1, np.sin(a)*.1, 1), L, n, rng, curl=.04, up=.05)
        t = np.linspace(0, 1, n+1)
        tube(m, pts, .012*(1.3-.7*t), 4, sway=t, second=0, cap=False)
        for i in range(2, n+1):
            side = 1 if i % 2 else -1
            az = a+i*1.9
            root = pts[i]
            L2 = rng.uniform(.5, .95)
            d = np.array((np.cos(az)*side, np.sin(az)*side, .35))
            leaf = _frond(root, d, L2, 6, rng, curl=.14, up=.1)
            lt = np.linspace(0, 1, 7)
            wave = .036*np.sin(lt*np.pi)**.6+.005
            blade(m, leaf, wave, t[i]+(1-t[i])*lt*.4, second=float(rng.random()))
    return m


def raft(rng):
    """A floating mat of sargassum: leaves and bladders in a flat tangle a couple of metres across, riding at the surface."""
    m = Mesh()
    for _ in range(46):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, 1.0)**.6*1.15
        at = (np.cos(a)*d, np.sin(a)*d*.75, rng.uniform(-.06, .03))
        h = rng.uniform(0, np.pi*2)
        pts = _frond(at, (np.cos(h), np.sin(h), 0), rng.uniform(.4, .8), 6, rng, curl=.3, up=0)
        pts[:, 2] = np.clip(pts[:, 2], -.1, .05)
        tube(m, pts, np.full(len(pts), .005), 3, sway=np.zeros(len(pts)), cap=False)
        for i in range(1, len(pts)):
            for _ in range(2):
                q = rng.uniform(0, np.pi*2)
                d2 = np.array((np.cos(q), np.sin(q), rng.uniform(-.15, .15)))
                leaf = pts[i]+np.linspace(0, 1, 4)[:, None]*d2*rng.uniform(.05, .11)
                blade(m, leaf, np.array((.002, .012, .011, .001)), np.zeros(4), second=float(rng.random()*.7))
            if rng.random() < .45:
                tube(m, [pts[i], pts[i]+(.016, 0, .004)], [.007, .008], 4, sway=[0, 0], second=1.0)
    return m


# ------------------------------------------------------------------------------- the rest

def reef_rock(rng):
    """Dead coral rock, the reef's skeleton: pitted and crusted, for hiding things behind."""
    m = Mesh()
    p, r, c = dome(64)
    q = p*np.array((1.0, .8, .72))
    big = noise(p, 1.9, 13.0)
    pits = noise(p, 8.5, 21.0)
    q += p*(.25*big+.07*pits+.03*noise(p, 21.0, 2.0))[:, None]
    m.add(q, col(len(q), 0, np.clip(.4+pits*1.1, 0, 1), np.clip(.5+big*1.3, 0, 1), .45), grid_tris(r, c))
    return m


def urchin(rng):
    """A long-spined black urchin."""
    m = Mesh()
    p, r, c = dome(10)
    m.add(p*.035+(0, 0, .02), col(len(p), 0, .6), grid_tris(r, c))
    for _ in range(46):
        d = rng.normal(0, 1, 3)
        d[2] = abs(d[2])
        d /= np.linalg.norm(d)
        at = d*.03+np.array((0, 0, .02))
        tube(m, [at, at+d*rng.uniform(.07, .13)], [.0022, .0004], 3, second=.0)
    return m


def starfish(rng):
    m = Mesh()
    res, seg = 8, 50
    th = np.linspace(0, 1, res)
    ph = np.linspace(0, np.pi*2, seg, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    R = T*(.038+.075*(.5+.5*np.cos(P*5))**1.2)
    q = np.stack([R*np.cos(P), R*np.sin(P), .008+.022*(1-T**2)*(1-.5*(R/.11))], -1).reshape(-1, 3)
    m.add(q, col(len(q), 0, 1, 1, 1), grid_tris(res, seg))
    return m


# ------------------------------------------------------------------------------- more hard and soft corals

def elkhorn(rng):
    """Acropora palmata: thick flattened antlers reaching up and out, the great builder of the Caribbean reef crest."""
    m = Mesh()

    def grow(at, d, r, depth):
        n = 5
        L = rng.uniform(.28, .46)
        pts, rr = [at], [r]
        for i in range(n):
            d = d+rng.normal(0, .07, 3)+np.array((0, 0, .03))
            d /= np.linalg.norm(d)
            pts.append(pts[-1]+d*L/n)
            rr.append(r*(1-.14*(i+1)/n))
        path = np.array(pts)
        # A flattened branch: a tube squashed in height, wider towards its palm.
        k = len(m.p)
        tube(m, path, rr, 7, second=float(np.clip(1-depth/4, 0, 1)), pattern=.8, cap=depth == 0)
        centre = np.repeat(path, 7, axis=0)
        q = m.p[k]
        off = q[:7*len(path)]-centre
        off[:, 2] *= .55
        off[:, :2] *= 1.0+np.repeat(np.linspace(0, 1.25, len(path)), 7)[:, None]
        q[:7*len(path)] = (centre+off).astype('f4')
        if depth > 0:
            for _ in range(2 if rng.random() < .7 else 3):
                s = rng.normal(0, .55, 3)
                s[2] = abs(s[2])*.4
                grow(path[-1], d+s, rr[-1]*.86, depth-1)

    tube(m, [(0, 0, -.1), (.02, 0, .18), (.04, .02, .34)], [.16, .13, .1], 9, second=.1, pattern=.8)
    for _ in range(4):
        a = rng.uniform(0, np.pi*2)
        grow(np.array((.04, .02, .32)), np.array((np.cos(a), np.sin(a), .55)), .1, 3)
    return m


def pillar_coral(rng):
    """Dendrogyra: upright fingers from one mound, furred with polyps by day, a metre and a half at most."""
    m = Mesh()
    p, r, c = dome(30)
    m.add(p*np.array((.46, .42, .2)), col(len(p), 0, .8, .2, .9), grid_tris(r, c))
    for _ in range(int(rng.integers(9, 15))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(.03, .36)
        H = rng.uniform(.55, 1.45)*(1-.35*d/.36)
        R = rng.uniform(.045, .085)
        at = np.array((np.cos(a)*d, np.sin(a)*d, 0.0))
        n = 9
        lean = rng.normal(0, .03, 2)
        t = np.linspace(0, 1, n)
        path = at+np.stack([lean[0]*t*H*3+.012*np.sin(t*7+a), lean[1]*t*H*3+.012*np.cos(t*6+a), t*H], 1)
        tube(m, path, R*(1.08-.22*t)*(1+.05*np.sin(t*17+a)), 9, second=float(rng.random()*.4), pattern=1)
    return m


def lettuce_coral(rng):
    """Agaricia: thin overlapping leaves on edge, ruffled, in tiers: the reef's lettuce."""
    m = Mesh()
    for _ in range(int(rng.integers(7, 12))):
        cx, cy, z0 = rng.normal(0, .17), rng.normal(0, .17), rng.uniform(-.02, .18)
        head = rng.uniform(0, np.pi*2)
        R = rng.uniform(.14, .34)
        s = np.linspace(0, 1, 10)
        a = np.linspace(-1.5, 1.5, 34)
        S, A = np.meshgrid(s, a, indexing='ij')
        ruffle = .28*np.sin(A*7+head*5)*S**1.4+.1*np.sin(A*15)*S**2
        x = S*R*np.sin(A)
        y = S*R*np.cos(A)
        zz = z0+S*R*.38+ruffle*R*.42
        q = np.stack([cx+x*np.cos(head)-y*np.sin(head), cy+x*np.sin(head)+y*np.cos(head), zz], -1).reshape(-1, 3)
        cc = col(len(q), 0, 1, 0, .85)
        cc[:, 1] = (.55+.45*S).reshape(-1)
        cc[:, 2] = S.reshape(-1)**2
        m.add(q, cc, grid_tris(10, 34, wrap=False))
    return m


def sea_rods(rng):
    """Plexaura: soft bushy rods, a metre tall, furred with polyps, that bend all together with the surge."""
    m = Mesh()

    def grow(at, d, r, depth, h):
        n = 5
        L = rng.uniform(.14, .3)
        pts, rr, w = [at], [r], [h]
        for i in range(n):
            d = d+rng.normal(0, .08, 3)+np.array((0, 0, .08))
            d /= np.linalg.norm(d)
            pts.append(pts[-1]+d*L/n)
            rr.append(rr[-1]*.97)
            w.append(min(1.0, pts[-1][2]/1.05))
        tube(m, pts, rr, 5, sway=w, second=float(1-depth/4), pattern=1, cap=depth == 0)
        if depth > 0:
            for s in (-1, 1):
                grow(pts[-1], d+np.array((s*rng.uniform(.25, .6), rng.normal(0, .3), .2)), rr[-1]*.9, depth-1, w[-1])

    for a in rng.uniform(0, np.pi*2, 3):
        grow(np.array((np.cos(a)*.04, np.sin(a)*.04, -.03)), np.array((np.cos(a)*.3, np.sin(a)*.3, 1)), .017, 4, 0.0)
    return m


def sea_whips(rng):
    """Single unbranched whips springing from the rock, thin as a pencil and two metres long."""
    m = Mesh()
    for _ in range(int(rng.integers(4, 8))):
        a = rng.uniform(0, np.pi*2)
        L = rng.uniform(1.0, 2.1)
        pts = _frond((np.cos(a)*.1, np.sin(a)*.1, -.03), (np.cos(a)*.22, np.sin(a)*.22, 1), L, 13, rng, curl=.05, up=.0)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .011*(1.1-.8*t), 5, sway=t**1.2, second=float(rng.random()), pattern=.6)
    return m


def anemone(rng):
    """Condylactis: a soft column under a head of finger-thick, glass-pale tentacles with purple tips that wave."""
    m = Mesh()
    tube(m, [(0, 0, -.02), (0, 0, .05), (0, 0, .09)], [.055, .05, .06], 12, second=0, cap=True)
    for ring in range(3):
        n = 16+ring*7
        rr = .022+ring*.016
        for i in range(n):
            a = i/n*np.pi*2+rng.uniform(-.12, .12)
            d = np.array((np.cos(a)*(.55+ring*.2), np.sin(a)*(.55+ring*.2), .85-ring*.17))
            at = (np.cos(a)*rr, np.sin(a)*rr, .09)
            pts = _frond(at, d, rng.uniform(.09, .17), 6, rng, curl=.1, up=-.04)
            t = np.linspace(0, 1, len(pts))
            k = len(m.p)
            tube(m, pts, .0085*(1.1-.55*t), 5, sway=t, pattern=0)
            m.c[k][:, 2] = np.append(np.repeat(t**3, 5), 1.0)
    return m


# ------------------------------------------------------------------------------- more sponges and plants

def rope_sponge(rng):
    """Amphimedon: long crooked ropes, sprawling over the rock and rising in loops."""
    m = Mesh()
    for _ in range(int(rng.integers(4, 8))):
        a = rng.uniform(0, np.pi*2)
        pts = _frond((0, 0, -.03), (np.cos(a), np.sin(a), .7), rng.uniform(.6, 1.3), 12, rng, curl=.28, up=-.01)
        pts[:, 2] = np.maximum(pts[:, 2], .01)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .024*(1.05-.3*t)*(1+.14*np.sin(t*31)), 6, second=float(rng.random()), pattern=.7)
    return m


def manatee_grass(rng):
    """Syringodium: round thin stalks, brighter than turtle grass, standing in loose stands over the sand."""
    m = Mesh()
    for _ in range(38):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, .32)
        L = rng.uniform(.2, .55)
        pts = _frond((np.cos(a)*d, np.sin(a)*d, -.02), (np.cos(a)*.12, np.sin(a)*.12, 1), L, 6, rng, curl=.08, up=-.02)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .0021*(1.15-.6*t), 3, sway=t**1.3, second=float(rng.random() < .2), cap=False)
    return m


def segment(m, at, d, R, sw, second, cup=.25, kidney=.18, sides=14):
    """One calcified segment: a small rounded plate, kidney shaped (a notch where the next joint grows), slightly cupped,
    with a rim of some thickness; two faces so it reads solid from the side."""
    side = np.cross(d, (.2, .9, .3))
    side /= np.linalg.norm(side)
    nrm = np.cross(d, side)
    a = np.linspace(0, np.pi*2, sides, endpoint=False)
    # Kidney: the outline pulled in at the top (where the chain goes on), wider than tall.
    r = R*(1-kidney*np.exp(-((a-np.pi/2)/.45)**2))
    ex, ey = np.cos(a)*r*1.15, np.sin(a)*r+R*.85
    pts, cs, tris = [], [], []
    for face in (1, -1):
        k0 = len(pts)
        c0 = at+d*R*.85+nrm*face*R*.06
        pts.append(c0+nrm*R*cup*face*0)
        for i in range(sides):
            rim = at+side*ex[i]+d*ey[i]+nrm*(R*cup*((ex[i]/R)**2)*.5+face*R*.04)
            pts.append(rim)
        for i in range(sides):
            j = (i+1) % sides
            tris.append((k0, k0+1+i, k0+1+j) if face > 0 else (k0, k0+1+j, k0+1+i))
    pts = np.array(pts, 'f4')
    c = col(len(pts), sw, .95, second, .2)
    m.add(pts, c, tris)


def halimeda(rng):
    """Halimeda (H. opuntia/incrassata), as photographed: a dense low bush of chains of small, stiff, rounded segments, each
    a centimetre or so, kidney shaped and slightly cupped, branching at almost every joint; pale chalky green, whitish
    where old. (It was seven sparse chains of big flat nine-sided discs: read as pentagons stuck together.)"""
    m = Mesh()

    def chain(at, d, n, sw, depth):
        for i in range(n):
            R = rng.uniform(.006, .009)*(1-.25*i/max(n, 1))
            segment(m, at, d, R, min(1, sw), float(np.clip(rng.normal(.25, .2)+.1*depth, 0, 1)))
            at = at+d*R*1.75
            d = d+rng.normal(0, .22, 3)+np.array((0, 0, .06))
            d = d/np.linalg.norm(d)
            sw += .07
            if depth < 3 and rng.random() < .42:
                spl = np.cross(d, rng.normal(0, 1, 3))
                spl /= np.linalg.norm(spl)
                nd = d*.75+spl*.66
                chain(at, nd/np.linalg.norm(nd), max(2, n-i-1), sw, depth+1)

    for _ in range(int(rng.integers(9, 15))):
        a = rng.uniform(0, np.pi*2)
        r0 = rng.uniform(0, .05)
        d = np.array((np.cos(a)*rng.uniform(.2, .7), np.sin(a)*rng.uniform(.2, .7), 1))
        chain(np.array((np.cos(a)*r0, np.sin(a)*r0, -.004)), d/np.linalg.norm(d), int(rng.integers(4, 8)), .05, 0)
    return m


def padina(rng):
    """Padina (peacock's tail): brown fans a hand across, rolled at the outer edge, with fine concentric bands of
    white chalk; in clumps on rock and rubble in the shallows."""
    m = Mesh()
    for k in range(int(rng.integers(4, 9))):
        a = rng.uniform(0, np.pi*2)
        R = rng.uniform(.04, .08)
        base = np.array((np.cos(a)*rng.uniform(0, .05), np.sin(a)*rng.uniform(0, .05), 0.0))
        face = rng.uniform(0, np.pi*2)
        tilt = rng.uniform(.0, .5)
        nr, na = 8, 16
        u = np.linspace(0, 1, nr)
        th = np.linspace(-1.2, 1.2, na)
        U, T = np.meshgrid(u, th, indexing='ij')
        # A fan: radius out from the stalk, a spread of 140 degrees, a funnel's cup, the outer rim rolled inwards.
        rr = U*R
        x = rr*np.sin(T)
        z = rr*np.cos(T)*.9+.012
        y = .35*rr*(np.abs(T)/1.2)**2+.4*R*np.clip((U-.8)/.2, 0, 1)**2
        # Turn it to face out, and lean it.
        c, sn = np.cos(face), np.sin(face)
        X = x*c-y*sn
        Y = x*sn+y*c
        Z = z*np.cos(tilt)+y*np.sin(tilt)*.3
        q = np.stack([base[0]+X, base[1]+Y, Z], -1).reshape(-1, 3)
        cc = col(len(q), 0, .95, 0, .1)
        cc[:, 0] = U.reshape(-1)**1.5
        # Concentric chalk bands across the fan.
        cc[:, 2] = (np.sin(U*R*900) > .55).astype('f4').reshape(-1)*.8
        m.add(q, cc, grid_tris(nr, na, wrap=False))
    return m


def caulerpa(rng):
    """Caulerpa (green feather alga): runners creeping over sand and rubble, rooted every few centimetres, with upright
    fronds like little green feathers or ferns, a hand high."""
    m = Mesh()
    for k in range(int(rng.integers(2, 4))):
        a = rng.uniform(0, np.pi*2)
        n = 10
        t = np.linspace(0, 1, n)
        L = rng.uniform(.35, .6)
        wig = rng.normal(0, .5, 2)
        path = np.stack([np.cos(a)*t*L+.04*np.sin(t*6+wig[0]), np.sin(a)*t*L+.04*np.cos(t*5+wig[1]), np.full(n, .003)], 1)
        tube(m, path, np.full(n, .0025), 4, second=0.0, cap=False)
        for i in range(1, n):
            if rng.random() < .25:
                continue
            H = rng.uniform(.04, .1)
            root = path[i]
            stem = np.stack([root, root+np.array((rng.normal(0, .01), rng.normal(0, .01), H*.5)), root+np.array((rng.normal(0, .015), rng.normal(0, .015), H))])
            tube(m, stem, [.0022, .0018, .0012], 3, sway=[0, .5, 1], second=.2, cap=True)
            # Pinnules either side, in one plane, shorter to the tip: the feather.
            pl = np.array((np.cos(a+np.pi/2), np.sin(a+np.pi/2), 0))
            for j in range(1, 8):
                f = j/8
                at = root+(stem[2]-root)*f
                ln = .016*(1-f*.7)
                for sd in (-1, 1):
                    tube(m, [at, at+pl*sd*ln+np.array((0, 0, ln*.45))], [.0012, .0006], 3, sway=[f, min(1, f+.1)], second=.3, cap=False)
    return m


def dictyota(rng):
    """Dictyota: flat brown ribbons a few millimetres wide, forked again and again into a loose tuft, with a blue-green
    sheen on the young tips."""
    m = Mesh()

    def ribbon(at, d, L, w, depth, sw):
        n = 5
        t = np.linspace(0, 1, n)
        bend = rng.normal(0, .3, 3)
        path = np.array([at+d*L*tt+bend*L*tt*tt*.3 for tt in t])
        blade(m, path, np.full(n, w), np.clip(sw+t*.25, 0, 1), second=float(depth >= 2))
        if depth < 4:
            tip = path[-1]
            dd = path[-1]-path[-2]
            dd /= np.linalg.norm(dd)
            spl = np.cross(dd, (0, 0, 1.0)+rng.normal(0, .3, 3))
            spl /= max(np.linalg.norm(spl), 1e-6)
            for sd in (-1, 1):
                nd = dd*.85+spl*sd*.5
                ribbon(tip, nd/np.linalg.norm(nd), L*rng.uniform(.75, .95), w*.92, depth+1, sw+.25)

    for _ in range(int(rng.integers(3, 6))):
        a = rng.uniform(0, np.pi*2)
        d = np.array((np.cos(a)*.4, np.sin(a)*.4, 1))
        ribbon(np.array((np.cos(a)*.02, np.sin(a)*.02, -.005)), d/np.linalg.norm(d), rng.uniform(.025, .04), .0035, 0, 0.0)
    return m


def udotea(rng):
    """Udotea (mermaid's fan): a short stalk carrying a thin, stiff, fan-shaped blade with faint concentric zones, green
    and a little chalky, growing from sand."""
    m = Mesh()
    for k in range(int(rng.integers(1, 4))):
        a = rng.uniform(0, np.pi*2)
        base = np.array((np.cos(a)*rng.uniform(0, .04), np.sin(a)*rng.uniform(0, .04), -.01))
        stalk_h = rng.uniform(.025, .05)
        top = base+np.array((rng.normal(0, .006), rng.normal(0, .006), stalk_h))
        tube(m, [base, (base+top)/2, top], [.004, .0035, .003], 5, sway=[0, .1, .2], second=.0, cap=False)
        R = rng.uniform(.04, .07)
        face = rng.uniform(0, np.pi*2)
        nr, na = 7, 14
        u = np.linspace(0, 1, nr)
        th = np.linspace(-.85, .85, na)
        U, T = np.meshgrid(u, th, indexing='ij')
        rr = U*R*(1+.06*np.sin(T*9+k))
        x = rr*np.sin(T)
        z = rr*np.cos(T)
        y = .12*rr*np.sin(T*2.0)+.004*np.sin(U*30)
        c, sn = np.cos(face), np.sin(face)
        q = np.stack([top[0]+x*c-y*sn, top[1]+x*sn+y*c, top[2]+z], -1).reshape(-1, 3)
        cc = col(len(q), 0, .95, 0, .15)
        cc[:, 0] = .2+.8*U.reshape(-1)**1.4
        cc[:, 2] = (np.sin(U*R*500) > .7).astype('f4').reshape(-1)*.6
        m.add(q, cc, grid_tris(nr, na, wrap=False))
    return m


def shaving_brush(rng):
    """Penicillus: a chalky stalk under a tight tuft of filaments, standing in the sand like a shaving brush."""
    m = Mesh()
    for _ in range(int(rng.integers(3, 7))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, .15)
        H = rng.uniform(.07, .13)
        at = np.array((np.cos(a)*d, np.sin(a)*d, -.02))
        top = at+(rng.normal(0, .01), rng.normal(0, .01), H)
        tube(m, [at, (at+top)/2, top], [.0045, .004, .005], 4, sway=[0, .2, .4], second=1, cap=False)
        for _ in range(26):
            q = rng.uniform(0, np.pi*2)
            sp = rng.uniform(.1, .5)
            leaf = _frond(top, (np.cos(q)*sp, np.sin(q)*sp, 1), rng.uniform(.03, .06), 3, rng, curl=.14, up=.0)
            tube(m, leaf, [.0016, .0013, .001, .0007], 3, sway=[.4, .55, .7, .9], second=float(rng.random()*.3), cap=False)
    return m


def sea_lettuce(rng):
    """Ulva: thin ruffled bright green sheets, torn at the edges, on rocks where the sea is shallow and rich."""
    m = Mesh()
    for _ in range(int(rng.integers(8, 15))):
        head = rng.uniform(0, np.pi*2)
        L = rng.uniform(.12, .32)
        s, a = np.linspace(0, 1, 9), np.linspace(-1, 1, 11)
        S, A = np.meshgrid(s, a, indexing='ij')
        wid = L*.48*np.sin(S*np.pi*.92+.12)*(1+.12*np.sin(A*7+head))
        x = A*wid
        y = .1*L*np.sin(A*5+S*6+head)*S+S*L*.45
        zz = S*L*.8-.15*L*S*S
        q = np.stack([x*np.cos(head)-y*np.sin(head)+rng.normal(0, .05), x*np.sin(head)+y*np.cos(head)+rng.normal(0, .05), zz], -1).reshape(-1, 3)
        cc = col(len(q), 0, 1, float(rng.random()*.6), 0)
        cc[:, 0] = S.reshape(-1)**1.2
        cc[:, 1] = (.6+.4*S).reshape(-1)
        m.add(q, cc, grid_tris(9, 11, wrap=False))
    return m


def red_algae(rng):
    """Bushy wine-red algae, fine branching tufts a hand high: what makes old rock look furred from close to."""
    m = Mesh()

    def grow(at, d, r, depth, w):
        pts = _frond(at, d, rng.uniform(.03, .07), 3, rng, curl=.2, up=.05)
        ww = np.linspace(w, min(1, w+.2), len(pts))
        tube(m, pts, np.linspace(r, r*.8, len(pts)), 3, sway=ww, second=float(rng.random()), cap=False)
        if depth > 0:
            for _ in range(2):
                grow(pts[-1], d+rng.normal(0, .65, 3), r*.82, depth-1, ww[-1])

    for _ in range(12):
        a, dd = rng.uniform(0, np.pi*2), rng.uniform(0, .14)
        grow(np.array((np.cos(a)*dd, np.sin(a)*dd, -.01)), np.array((np.cos(a)*.3, np.sin(a)*.3, 1)), .0024, 3, 0.0)
    return m


def bull_kelp(rng):
    """Nereocystis of the cold seas: one whip of a stipe with a float at the top and a mop of long ribbons in the current."""
    m = Mesh()
    for _ in range(3):
        a = rng.uniform(0, np.pi*2)
        L = rng.uniform(4.5, 9.0)
        pts = _frond((np.cos(a)*.2, np.sin(a)*.2, -.04), (np.cos(a)*.08, np.sin(a)*.08, 1), L, 16, rng, curl=.035, up=.02)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .008+.016*t**3, 5, sway=t, cap=False)
        top = pts[-1]
        tube(m, [top, top+(0, 0, .09), top+(0, 0, .17)], [.03, .055, .03], 7, sway=[1, 1, 1], second=1)
        for k in range(9):
            q = k/9*np.pi*2
            leaf = _frond(top+(0, 0, .15), (np.cos(q), np.sin(q), -.1), rng.uniform(.9, 1.8), 7, rng, curl=.12, up=-.03)
            lt = np.linspace(0, 1, len(leaf))
            blade(m, leaf, .028*np.sin(lt*np.pi)**.5+.004, np.full(len(leaf), 1.0), second=float(rng.random()))
    return m


# ------------------------------------------------------------------------------- creatures that stay put

def sea_cucumber(rng):
    """Holothuria: a dark soft sausage with warts, lying on the sand."""
    m = Mesh()
    s, ph = np.linspace(0, 1, 16), np.linspace(0, np.pi*2, 12, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    R = .032*np.sin(S*np.pi)**.45
    bend = .02*np.sin(S*5)
    x, y, z = (S-.5)*.3, R*np.cos(P)+bend, R*np.sin(P)*.8+.024
    q = np.stack([x, y, z], -1).reshape(-1, 3)
    wart = noise(q, 180.0, 3.0)
    q += np.stack([0*wart, 0*wart, .0035*np.clip(wart, 0, 1)], 1)
    m.add(q, col(len(q), 0, np.clip(.6+wart, 0, 1), np.clip(.5+wart, 0, 1), .4), grid_tris(16, 12))
    return m


def conch(rng):
    """A queen conch: a heavy spiralled shell with blunt knobs and a flared pink lip."""
    m = Mesh()
    n, sides = 42, 10
    t = np.linspace(0, 1, n)
    turns = t*np.pi*2*4.2
    rad = .058*np.exp(-3.1*(1-t))
    h = .105*(1-t)
    knob = 1+.3*np.maximum(np.sin(turns*3.5), 0)**2*t
    pts = np.stack([rad*np.cos(turns), rad*np.sin(turns), h+.03], 1)
    tube(m, pts, .62*rad*knob+.0012, sides, second=0, cap=True)
    # The flared lip, a thin sheet from the last whorl, in the second colour.
    u, v = np.linspace(0, 1, 7), np.linspace(0, 1, 12)
    U, V = np.meshgrid(u, v, indexing='ij')
    a = np.pi*.2+V*1.7
    rr = .07+.075*U*np.sin(V*np.pi)
    q = np.stack([rr*np.cos(a), rr*np.sin(a), .016+.035*U*V+.01*np.sin(V*9)*U], -1).reshape(-1, 3)
    m.add(q, col(len(q), 0, 1, 1, 0), grid_tris(7, 12, wrap=False))
    # It lies on its side on the sand, spire up and back.
    a = np.radians(62)
    for k, part in enumerate(m.p):
        x, z = part[:, 0].copy(), part[:, 2].copy()-.03
        m.p[k][:, 0], m.p[k][:, 2] = x*np.cos(a)+z*np.sin(a), -x*np.sin(a)+z*np.cos(a)+.05
    return m


def mussels(rng):
    """Mussels, oysters and barnacles crowded on a rock: the crust of everything at the tide line."""
    m = Mesh()
    p, r, c = dome(26)
    m.add(p*np.array((.25, .2, .08)), col(len(p), 0, .5, 1, .3), grid_tris(r, c))
    for _ in range(95):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, 1)**.5*.24
        at = np.array((np.cos(a)*d, np.sin(a)*d*.8, .05*(1-(d/.25)**2)))
        if rng.random() < .6:
            L, W = rng.uniform(.05, .09), rng.uniform(.018, .03)      # a mussel, on end
            q = rng.uniform(0, np.pi*2)
            dirn = np.array((np.cos(q)*.6, np.sin(q)*.6, .8))
            tube(m, [at, at+dirn*L*.45, at+dirn*L], [W*.45, W, W*.5], 6, second=.0, cap=True)
        else:
            p2, r2, c2 = dome(7)                                       # a barnacle: a little ridged volcano
            R = rng.uniform(.008, .016)
            ring = 1+.12*np.sin(np.arctan2(p2[:, 1], p2[:, 0])*6)
            q2 = at+p2*np.stack([R*ring, R*ring, R*.9*np.ones(len(p2))], 1)
            m.add(q2, col(len(q2), 0, np.clip(p2[:, 2]*1.2, .35, 1), 1, .2), grid_tris(r2, c2))
    return m


def feather_worms(rng):
    """Christmas-tree and feather duster worms: fine spiral fans sprouting from a rock, a hand high at most."""
    m = Mesh()
    for _ in range(int(rng.integers(5, 10))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, .12)
        at = np.array((np.cos(a)*d, np.sin(a)*d, 0))
        H = rng.uniform(.035, .06)
        tube(m, [at-(0, 0, .01), at+(0, 0, H)], [.003, .0028], 4, sway=[0, .2], second=0, cap=False)
        sec = float(rng.random())
        for k in range(16):
            q = k/16*np.pi*2
            tip = at+(np.cos(q)*.026, np.sin(q)*.026, H+.038)
            mid = at+(np.cos(q)*.011, np.sin(q)*.011, H+.018)
            tube(m, [at+(0, 0, H), mid, tip], [.0012, .0009, .0005], 3, sway=[.2, .55, 1], second=sec, cap=False)
    return m


def sand_dollar(rng):
    m = Mesh()
    s, ph = np.linspace(0, 1, 7), np.linspace(0, np.pi*2, 24, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    R = .042*S
    petal = np.maximum(np.cos(P*5), 0)*np.sin(S*np.pi)**2
    q = np.stack([R*np.cos(P), R*np.sin(P), .006*(1-S**2)+.0015*petal+.002], -1).reshape(-1, 3)
    m.add(q, col(len(q), 0, (1-.4*petal).reshape(-1), .5, 0), grid_tris(7, 24))
    return m


def shells(rng):
    """Dead shells and broken coral thrown together: the litter of any sea bed."""
    m = Mesh()
    for _ in range(24):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, 1)**.6*.5
        at = np.array((np.cos(a)*d, np.sin(a)*d, 0))
        k = rng.random()
        if k < .55:                                                    # half a clam, ribbed, cup up or down
            R = rng.uniform(.012, .035)
            u, v = np.linspace(0, 1, 5), np.linspace(-1.1, 1.1, 11)
            U, V = np.meshgrid(u, v, indexing='ij')
            yaw = rng.uniform(0, np.pi*2)
            sgn = 1 if rng.random() < .35 else -1
            x, y = U*R*np.sin(V), U*R*np.cos(V)
            z = .002+.45*R*(1-U*U if sgn < 0 else U*U)
            q = np.stack([x*np.cos(yaw)-y*np.sin(yaw), x*np.sin(yaw)+y*np.cos(yaw), z*(1+.05*np.sin(V*19))], -1).reshape(-1, 3)+at
            m.add(q, col(len(q), 0, 1, float(rng.random()), 0), grid_tris(5, 11, wrap=False))
        else:                                                          # a stub of broken branch coral
            q = rng.uniform(0, np.pi*2)
            dirn = np.array((np.cos(q), np.sin(q), rng.uniform(-.05, .15)))
            tube(m, [at+(0, 0, .007), at+dirn*rng.uniform(.03, .08)+(0, 0, .007)], [.007, .005], 4, second=float(rng.random()), pattern=.5)
    return m


def crab(rng):
    """A land-and-tide crab: a wide flat shell, two claws, eight jointed legs. R on the legs twitches them in the material."""
    m = Mesh()
    p, r, c = dome(12)
    m.add(p*np.array((.042, .058, .026))+(0, 0, .022), col(len(p), 0, .85, 0, .1), grid_tris(r, c))
    for s in (-1, 1):
        for i in range(4):
            x = .022-.016*i
            a = (x, s*.05, .026)
            b = (x+rng.normal(0, .004)-.005*i, s*.09, .04)
            d = (x-.008*i, s*.118, .001)
            tube(m, [a, b, d], [.0055, .004, .0015], 4, sway=[0, .5, 1], second=.6)
        tube(m, [(.034, s*.045, .024), (.062, s*.062, .03), (.08, s*.03, .025)], [.007, .011, .006], 6, second=1)
    return m


def _ghost_legs(m, side, rng):
    """Four walking legs of one side of a ghost crab: long, thin, jointed, standing it 4 cm off the sand, their tips on
    the ground. Pivot at the body's centre, so the game can swing them as a set."""
    for i in range(4):
        x = .016-.012*i
        sp = (i-1.5)*.012
        a = (x, side*.02, .03)
        b = (x+sp*.6, side*.055, .052)
        c_ = (x+sp, side*.088, .03)
        d = (x+sp*1.3, side*.104, .001)
        tube(m, [a, b, c_, d], [.0035, .003, .0022, .0009], 4, second=0.0, pattern=.1)


def ghost_crab(rng):
    """Atlantic ghost crab (Ocypode quadrata), the body: a squarish pale carapace the colour of dry sand, club-shaped eyes on
    long stalks, claws unequal (one larger, white-tipped). Legs are separate meshes (GhostCrabLegL/R) the game moves."""
    m = Mesh()
    p, r, c = dome(16)
    shell = p*np.array((.024, .027, .016))
    # Squarer than round: push the outline towards a rounded rectangle.
    k = np.maximum(np.abs(shell[:, 0])/.024, np.abs(shell[:, 1])/.027)+1e-6
    shell[:, :2] *= (1+.22*(1-k))[:, None]
    m.add(shell+(0, 0, .03), col(len(p), 0, .9, 0, .05), grid_tris(r, c))
    for sd in (-1, 1):
        # Eye stalk and its dark club.
        tube(m, [(.02, sd*.012, .04), (.024, sd*.016, .056), (.025, sd*.017, .066)], [.0028, .0032, .004], 6, second=1.0, cap=True)
        big = sd > 0
        sc = 1.35 if big else .9
        tube(m, [(.022, sd*.022, .03), (.036, sd*.034, .038), (.05, sd*.03, .034)], [.005*sc, .008*sc, .006*sc], 6, second=0.0)
        tube(m, [(.05, sd*.03, .034), (.064, sd*.022, .03)], [.006*sc, .002], 5, second=.35)
    return m


def ghost_crab_legs_l(rng):
    m = Mesh()
    _ghost_legs(m, -1, rng)
    return m


def ghost_crab_legs_r(rng):
    m = Mesh()
    _ghost_legs(m, 1, rng)
    return m


def lobster(rng):
    """A Caribbean spiny lobster as photographed: a spiny round carapace with two curved horns over the eyes, long thick
    antennae spiny at the base sweeping forward and out, a segmented tail ending in a fan of five lobes, five pairs of
    jointed legs standing it on the sand. Body about 30 cm, no claws. (It was a striped spindle on stick legs: read as an
    insect.)"""
    m = Mesh()
    k, ring = 26, 12
    s_ = np.linspace(0, 1, k)
    ph = np.linspace(0, np.pi*2, ring, endpoint=False)
    S, P = np.meshgrid(s_, ph, indexing='ij')
    # carapace 0..0.42, tail 0.42..0.92
    R = np.interp(S, [0, .04, .15, .38, .44, .6, .8, .92, 1], [.012, .03, .045, .047, .041, .037, .03, .022, .018])
    R = R+(S > .44)*(np.abs(np.sin((S-.44)*np.pi/.0833)) > .9)*.004
    x = .14-S*.3
    zc = .055-.012*(S > .5)*(S-.5)/.5
    q = np.stack([x, R*np.cos(P)*1.08, zc+R*np.sin(P)*.85], -1).reshape(-1, 3)
    cc = col(len(q), 0, 1, (S > .44).astype('f4').reshape(-1)*.35, .25)
    m.add(q, cc, grid_tris(k, ring))
    # Spines on the carapace, short cones pointing forward and up.
    for _ in range(26):
        a, t = rng.uniform(.15, np.pi-.15), rng.uniform(.06, .38)
        r0 = float(np.interp(t, [0, .04, .15, .38], [.012, .03, .045, .047]))
        base = np.array((.14-t*.3, np.cos(a)*r0*1.08, .055+np.sin(a)*r0*.85))
        outv = np.array((0, np.cos(a), np.sin(a)))
        tube(m, [base-outv*.003, base+outv*.009+np.array((.006, 0, 0))], [.0035, .0006], 3, second=.6)
    # Horns over the eyes.
    for sd in (-1, 1):
        tube(m, [(.12, sd*.018, .075), (.145, sd*.022, .1), (.158, sd*.018, .113)], [.008, .005, .0012], 5, second=.7)
    # Tail fan: five rounded lobes spreading from the last segment.
    tail = np.array((.14-.92*.3, 0, .045))
    for a in np.linspace(-.7, .7, 5):
        d = np.array((-np.cos(a), np.sin(a), 0))
        blade(m, [tail, tail+d*.03, tail+d*.055], [.006, .016, .012], [0, .5, 1], second=.4)
    # Antennae: thick spiny bases, long whips sweeping forward and out, a little up.
    for sd in (-1, 1):
        t = np.linspace(0, 1, 9)
        pts = np.stack([.14+t*.42, sd*(.02+t*.2+t*t*.12), .065+t*.06-t*t*.05], 1)
        tube(m, pts, .011*(1-t)**1.3+.0012, 5, sway=t**1.5, second=.75)
    # Legs: five pairs, out from the underside, a knee up, the tip on the sand.
    for sd in (-1, 1):
        for i in range(5):
            x0 = .1-.06*i
            spread = .02*(i-2)
            pts = [(x0, sd*.03, .04), (x0+spread*.5, sd*.075, .06), (x0+spread, sd*.11, .028), (x0+spread*1.3, sd*.125, .002)]
            tube(m, pts, [.0045, .0038, .003, .0012], 4, sway=[0, .2, .4, .5], second=.9)
    return m


# ------------------------------------------------------------------------------- stone

def _facet_rock(p, rng, planes=26, squash=(1, 1, 1)):
    """A rock broken by real fracture planes: each direction of p is cut back to the nearest of a set of random planes,
    so faces come out flat with hard edges and nothing like a noisy ball."""
    n = rng.normal(0, 1, (planes, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    off = rng.uniform(.62, 1.0, planes)
    d = p/np.maximum(np.linalg.norm(p, axis=1, keepdims=True), 1e-6)
    dots = d @ n.T
    t = np.where(dots > .02, off/np.maximum(dots, .02), 1e6).min(1)
    return d*np.minimum(t, 1.45)[:, None]*np.array(squash)


def boulder(rng):
    """A fallen block off a sea cliff, angular, its edges only a little worn."""
    m = Mesh()
    p, r, c = dome(64)
    q = _facet_rock(p, rng, 22, (1.05, .85, .78))
    q += p*(.022*noise(p, 11.0, 4.0)+.009*noise(p, 31.0, 8.0))[:, None]
    pit = noise(p, 7.0, 15.0)
    m.add(q, col(len(q), 0, np.clip(.55+pit, 0, 1), np.clip(.5+noise(p, 2.1, 7.0)*1.3, 0, 1), .25), grid_tris(r, c))
    return m


def cobbles(rng):
    """A spill of sea-rounded stones from fist to head size."""
    m = Mesh()
    for _ in range(26):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, 1)**.7*.95
        R = rng.uniform(.035, .13)
        p, r, c = dome(11)
        q = p*R*np.array((1, rng.uniform(.65, 1), rng.uniform(.5, .8)))
        q += p*(R*.08*noise(p, 3.5, rng.uniform(0, 9)))[:, None]
        q += (np.cos(a)*d, np.sin(a)*d, -R*.15)
        m.add(q, col(len(q), 0, .85, float(rng.random()), .05), grid_tris(r, c))
    return m


def pinnacle(rng):
    """A coral-grown rock tower standing off the reef: 8 m tall, wider at the foot, ledged, crusted all over."""
    m = Mesh()
    s, ph = np.linspace(0, 1, 90), np.linspace(0, np.pi*2, 90, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    dirs = np.stack([np.cos(P), np.sin(P), np.zeros_like(P)], -1).reshape(-1, 3)
    zz = S.reshape(-1)
    q3 = dirs+np.stack([0*zz, 0*zz, zz*5], 1)
    R = (3.0*(1-zz)**1.35+.75)*(1+.2*noise(q3, .9, 3.0)+.1*noise(q3, 2.6, 8.0))
    # Ledges that run out and come back, never a whole ring (a regular stack read as a pagoda).
    R *= 1+.09*noise(q3, .55, 5.0)*np.sign(np.sin(zz*19+noise(q3, .7, 2.0)*4))
    R *= np.minimum(1, (1.01-zz)*12)**.5                                # the top rounds off
    q = dirs*R[:, None]+np.stack([0*zz, 0*zz, zz*8-.5], 1)
    q += dirs*(.1*noise(q, 3.7, 2.0)+.05*noise(q, 11.0, 5.0))[:, None]
    m.add(q, col(len(q), 0, np.clip(.55+noise(q, 4.0, 9.0), 0, 1), np.clip(.5+noise(q, .8, 1.0)*1.4, 0, 1), .4), grid_tris(90, 90))
    return m


def skerry(rng):
    """A scoglio: a jagged reef rock breaking the surface, 7 m across, layered and tilted like a drowned stratum. The mesh's
    z = 0 is meant for the sea bed; the placer sizes it so that its top stands clear of the water."""
    m = Mesh()
    res = 110
    s, ph = np.linspace(0, 1, res), np.linspace(0, np.pi*2, res*2, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    T = S*np.pi*.72
    d = np.stack([np.sin(T)*np.cos(P), np.sin(T)*np.sin(P), np.cos(T)], -1).reshape(-1, 3)
    q = _facet_rock(d, rng, 34, (3.6, 2.6, 3.4))
    # Tilted strata: ledges along one dip, and a blown-out edge.
    dip = np.array((.46, .2, .86))
    band = q @ dip
    q += d*(.14*np.sign(np.sin(band*4.2))*np.abs(np.sin(band*4.2))**.25)[:, None]
    q += d*(.2*noise(q, .9, 3.0)+.09*noise(q, 2.7, 8.0)+.035*noise(q, 8.0, 1.0))[:, None]
    q[:, 2] -= q[:, 2].min()+.2
    cav = np.clip(.62+noise(q, 3.1, 6.0)*.9+.2*np.sin(band*4.2), 0, 1)
    m.add(q, col(len(q), 0, cav, np.clip(.5+noise(q, .7, 2.0)*1.3, 0, 1), .15), grid_tris(res, res*2))
    return m


def man_o_war(rng):
    """Physalia: a gas float the blue of a gas flame riding on the waves, with a trailing fringe. Flotsam carries it."""
    m = Mesh()
    s, ph = np.linspace(0, 1, 14), np.linspace(0, np.pi*2, 12, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    R = .075*np.sin(S*np.pi)**.6+.001
    crest = .06*np.sin(S*np.pi)**1.2*(1+.25*np.sin(S*22))
    q = np.stack([(S-.5)*.3, R*np.cos(P)*.9, R*np.sin(P)+.05+np.maximum(np.sin(P), 0)*crest], -1).reshape(-1, 3)
    m.add(q, col(len(q), 0, 1, np.clip(.5+np.sin(P)*.9, 0, 1).reshape(-1), .0), grid_tris(14, 12))
    for _ in range(26):
        a = rng.uniform(-.1, .1)
        at = np.array((rng.uniform(-.08, .1), a, .01))
        pts = _frond(at, (rng.normal(0, .2), rng.normal(0, .2), -1), rng.uniform(.35, 1.2), 7, rng, curl=.12, up=.01)
        t = np.linspace(0, 1, len(pts))
        tube(m, pts, .003*(1.1-.8*t), 3, sway=t, second=1, cap=False)
    return m


# ------------------------------------------------------------------------------- more of the Caribbean reef (2026-11-08)

def barrel_sponge(rng):
    """Xestospongia muta, the giant barrel sponge: a hard, ridged barrel up to a metre high, a deep hollow inside."""
    m = Mesh()
    H, R = rng.uniform(.55, 1.0), rng.uniform(.28, .42)
    rows, sides = 26, 40
    s = np.linspace(0, 1, rows)
    ph = np.linspace(0, np.pi*2, sides, endpoint=False)
    S, P = np.meshgrid(s, ph, indexing='ij')
    out = S < .74
    v = np.where(out, S/.74, 1-(S-.74)/.26*.85)
    # Flares from a narrow foot, widest near the rim; sharp vertical ridges, broken into knobs here and there.
    prof = np.where(out, R*(.62+.48*np.sin(np.pi*.5*v)**.8), R*(1.08-.42*(S-.74)/.26))
    ridge = .07*np.abs(np.sin(P*9+.6*np.sin(S*5)))**.6*(1+.4*np.sin(S*23+P*3))
    rad = prof*(1+np.where(out, ridge, .02*np.sin(P*9)))
    z = H*v-.05
    q = np.stack([rad*np.cos(P), rad*np.sin(P), z], -1).reshape(-1, 3)
    c = col(len(q), 0, 1, 0, .6)
    c[:, 1] = np.where(out, .75+.25*np.abs(np.sin(P*9)), np.clip(1-(S-.74)/.26*1.3, .08, 1)).reshape(-1)
    c[:, 2] = np.clip(z/H, 0, 1).reshape(-1)*.5
    m.add(q, c, grid_tris(rows, sides))
    return m


def tube_sponges(rng):
    """Yellow tube sponges and purple ones: a clump of slender chimneys, each open at the top."""
    m = Mesh()
    second = float(rng.integers(0, 2))
    for k in range(int(rng.integers(5, 10))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, .12)
        H, R = rng.uniform(.14, .48), rng.uniform(.022, .042)
        lean = rng.normal(0, .12, 2)
        n = 12
        s = np.linspace(0, 1, n)
        path = np.stack([np.cos(a)*d+lean[0]*s*H, np.sin(a)*d+lean[1]*s*H, s*H-.02], 1)
        radii = R*(1.1-.2*s+.08*np.sin(s*9+k))
        tube(m, path, radii, 8, second=second, pattern=.7, cap=False)
        # The hollow: a short tube turned inside the rim, dark.
        inner = np.stack([path[-1]+(path[-1]-path[-2])*0 - np.array((0, 0, t)) for t in (0, .03, .07)])
        tube(m, inner, [radii[-1]*.8, radii[-1]*.72, radii[-1]*.65], 8, second=second, pattern=0, cap=True)
    return m


def slab(m, path, height, thick, second_from=.75, pattern=.25):
    """A thin wavy plate standing on the ground: path (u, 2) its foot line, height (u) its top above the ground, thick its
    half thickness at the foot (thinner to the top). A closed loop round the section: up one face, over the rounded top,
    down the other; the foot is in the sand."""
    path = np.asarray(path, 'f4')
    nu = len(path)
    d = np.gradient(path, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    v = np.linspace(0, 1, 7)
    sec = [(1, vv) for vv in v]+[(-1, vv) for vv in v[::-1]]
    pts, cs = [], []
    for i in range(nu):
        h = height[i]
        for face, vv in sec:
            t = thick*(1-.65*vv)*(1-.85*max(0.0, vv-.85)/.15)
            xy = path[i]+nrm[i]*face*t
            pts.append((xy[0], xy[1], -.03+(h+.03)*vv))
            cs.append((0, .55+.45*vv, float(np.clip((vv-second_from)/(1-second_from), 0, 1)), pattern))
    m.add(np.array(pts, 'f4'), np.array(cs, 'f4'), grid_tris(nu, len(sec), wrap=True))


def fire_coral(rng):
    """Blade fire coral (Millepora complanata), as photographed: thin upright plates, a hand to two hands high, each a wavy
    blade with a lobed, rounded top edge, fused at their feet into one encrusting crust; mustard yellow with pale growing
    edges. (Before 2026-11-11: flat rectangles with sharp corners, standing apart.)"""
    m = Mesh()
    base_a = rng.uniform(0, np.pi)
    # The crust they grow from: a low, lumpy mound under all of them.
    p, r, c = dome(26)
    crust = p*np.array((.15, .11, .035))
    lump = noise(p, 3.0, rng.uniform(0, 9))+.4*noise(p, 7.0, rng.uniform(0, 9))
    crust *= (1+.16*lump)[:, None]
    crust[:, 2] = np.maximum(crust[:, 2], -.02)
    rot = np.array([[np.cos(base_a), -np.sin(base_a), 0], [np.sin(base_a), np.cos(base_a), 0], [0, 0, 1]])
    m.add(crust@rot.T, col(len(p), 0, .7, 0, .3), grid_tris(r, c))
    for k in range(int(rng.integers(5, 9))):
        # Each plate along the current, offset across it, a little curved, and wavy along its length.
        off = rng.normal(0, .07)
        along0 = rng.normal(0, .06)
        Lp = rng.uniform(.12, .26)
        hd = base_a+rng.normal(0, .3)
        u = np.linspace(0, 1, 18)
        bend = rng.normal(0, .5)
        x = along0+(u-.5)*Lp
        y = off+bend*(u-.5)**2*Lp+.012*np.sin(u*np.pi*3+k)
        path = np.stack([x*np.cos(hd)-y*np.sin(hd), x*np.sin(hd)+y*np.cos(hd)], 1)
        H = rng.uniform(.12, .3)
        lobes = rng.integers(2, 5)
        top = H*np.sin(np.pi*u)**.45*(.82+.18*np.abs(np.sin(u*np.pi*lobes+rng.uniform(0, 3))))
        slab(m, path, top, rng.uniform(.006, .009))
    return m


def finger_coral(rng):
    """Finger coral (Porites porites): a mound of short, blunt, thick fingers, packed close."""
    m = Mesh()
    second = float(rng.uniform() < .3)
    for k in range(int(rng.integers(18, 30))):
        a, d = rng.uniform(0, np.pi*2), rng.uniform(0, 1)**.6*.1
        L = rng.uniform(.08, .2)*(1-d*3.5)
        R = rng.uniform(.012, .022)
        out = np.array((np.cos(a)*d*2.4, np.sin(a)*d*2.4, 1.0))
        out /= np.linalg.norm(out)
        n = 5
        s = np.linspace(0, 1, n)[:, None]
        path = np.array((np.cos(a)*d, np.sin(a)*d, -.02))[None]+out[None]*s*max(L, .04)
        tube(m, path, R*(1.15-.1*s[:, 0]), 6, second=second, pattern=.8, cap=True)
    return m


def sea_plume(rng):
    """A sea plume (Antillogorgia): a tall feathery gorgonian, side branches all in one plane, swaying in the surge."""
    m = Mesh()
    for stem in range(int(rng.integers(2, 5))):
        heading = rng.normal(0, .25)
        H = rng.uniform(.5, 1.1)
        n = 10
        s = np.linspace(0, 1, n)
        base = rng.normal(0, .05, 2)
        bend = rng.normal(0, .12)
        main = np.stack([base[0]+np.sin(heading)*s*H*.3+bend*s*s*H, base[1]+np.cos(heading)*.02*s, s*H-.03], 1)
        tube(m, main, .009*(1.2-.8*s), 4, sway=s**1.2, second=0.0, pattern=.3, cap=True)
        for i in range(2, n-1):
            for side in (-1, 1):
                L = H*.22*(1-s[i])**.6*rng.uniform(.7, 1.1)
                root = main[i]
                d = np.array((side*np.cos(heading), side*np.sin(heading)*.2, .55))
                d /= np.linalg.norm(d)
                twig = np.stack([root, root+d*L*.5, root+d*L+np.array((0, 0, L*.15))])
                tube(m, twig, [.004, .003, .0015], 3, sway=np.array([s[i], (s[i]+.1)**1.1, min(1, s[i]+.2)]), second=1.0, pattern=.2, cap=False)
    return m


# name: maker. Fish, sharks and everything else that swims are in marine_fauna.py.
SPECIES = dict(BrainCoral=brain_coral, BoulderCoral=boulder_coral, TableCoral=table_coral, Staghorn=staghorn, SeaFan=sea_fan, Sponges=sponges,
               SeaGrass=sea_grass, WeedBush=weed_bush, Kelp=kelp, Raft=raft, ReefRock=reef_rock, Urchin=urchin, Starfish=starfish,
               Elkhorn=elkhorn, PillarCoral=pillar_coral, LettuceCoral=lettuce_coral, SeaRods=sea_rods, SeaWhips=sea_whips, Anemone=anemone,
               RopeSponge=rope_sponge, ManateeGrass=manatee_grass, Halimeda=halimeda, ShavingBrush=shaving_brush, SeaLettuce=sea_lettuce,
               RedAlgae=red_algae, BullKelp=bull_kelp, SeaCucumber=sea_cucumber, Conch=conch, Mussels=mussels, FeatherWorms=feather_worms,
               SandDollar=sand_dollar, Shells=shells, Crab=crab, Lobster=lobster,
               GhostCrab=ghost_crab, GhostCrabLegL=ghost_crab_legs_l, GhostCrabLegR=ghost_crab_legs_r,
               Padina=padina, Caulerpa=caulerpa, Dictyota=dictyota, Udotea=udotea,
               Boulder=boulder, Cobbles=cobbles, Pinnacle=pinnacle, Skerry=skerry, ManOWar=man_o_war,
               BarrelSponge=barrel_sponge, TubeSponge=tube_sponges, FireCoral=fire_coral, FingerCoral=finger_coral, SeaPlume=sea_plume)


def write_glb(path, pos, nor, col_, tris):
    """Interchange reads glTF (x, y, z) as Unreal (x, z, y): written that way round, in metres. Colour as UNORM8."""
    gp = np.stack([pos[:, 0], pos[:, 2], pos[:, 1]], 1).astype('f4')
    gn = np.stack([nor[:, 0], nor[:, 2], nor[:, 1]], 1).astype('f4')
    # Faces must wind with the normals after the swap.
    a, b, d = gp[tris[:, 0]], gp[tris[:, 1]], gp[tris[:, 2]]
    flip = (np.cross(b-a, d-a)*gn[tris[:, 0]]).sum(1) < 0
    tris = tris.copy()
    tris[flip] = tris[flip][:, ::-1]
    c8 = np.clip(col_*255, 0, 255).astype('u1')
    blobs = [gp.tobytes(), gn.tobytes(), c8.tobytes(), tris.astype('u4').tobytes()]
    views, off = [], 0
    for b_ in blobs:
        views.append(dict(buffer=0, byteOffset=off, byteLength=len(b_)))
        off += (len(b_)+3) & ~3
    n = len(gp)
    doc = dict(asset=dict(version='2.0'), buffers=[dict(byteLength=off)], bufferViews=views,
               accessors=[dict(bufferView=0, componentType=5126, count=n, type='VEC3', min=gp.min(0).tolist(), max=gp.max(0).tolist()),
                          dict(bufferView=1, componentType=5126, count=n, type='VEC3'),
                          dict(bufferView=2, componentType=5121, normalized=True, count=n, type='VEC4'),
                          dict(bufferView=3, componentType=5125, count=len(tris)*3, type='SCALAR')],
               materials=[dict(name='M_Sea', doubleSided=True)],
               meshes=[dict(name=path.stem, primitives=[dict(attributes=dict(POSITION=0, NORMAL=1, COLOR_0=2), indices=3, material=0)])],
               nodes=[dict(mesh=0, name=path.stem)], scenes=[dict(nodes=[0])], scene=0)
    js = json.dumps(doc, separators=(',', ':')).encode()
    js += b' '*(-len(js) % 4)
    body = b''.join(b_+b'\0'*(-len(b_) % 4) for b_ in blobs)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(body)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)+js)
        f.write(struct.pack('<II', len(body), 0x004E4942)+body)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:]
    manifest = {}
    for i, (name, make) in enumerate(SPECIES.items()):
        if only and name not in only:
            continue
        p, n, c, t = make(np.random.default_rng(1000+i)).arrays()
        write_glb(OUT/f'SM_Sea_{name}.glb', p, n, c, t)
        manifest[name] = dict(tris=int(len(t)), size=[round(float(v), 2) for v in p.max(0)-p.min(0)])
        print(name, manifest[name], flush=True)
    if not only:
        (OUT/'manifest.json').write_text(json.dumps(manifest, indent=1))
    print('MARINE MESHES DONE', sum(m['tris'] for m in manifest.values()), 'tris')


if __name__ == '__main__':
    main()
