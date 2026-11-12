"""Everything that swims, procedural, real sizes: reef fish, shoals, sharks, rays, turtles, jellyfish, dolphins, whales.
GLB in Build/Marine next to marine_life.py's; Tools/marine/build_marine_assets.py imports them with M_SeaCreature.

Nose at +X, up +Z, the origin in the middle of the body. No skeleton: the material bends the body (M_SeaCreature in
Tools/marine/build_marine_assets.py). Vertex colour: R how much the swimming motion moves this vertex (0 nose .. 1 tail,
or the flippers), G shade in folds, B fin (1) or body (0), A pale underside share of a fin.
UV0: U along the body (0 nose, 1 tail root), V round it (+1 back, 0 flank, -1 belly): what patterns and eyes are drawn from.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Build/Marine'


class Mesh:
    def __init__(self):
        self.p, self.c, self.u, self.t, self.n = [], [], [], [], 0

    def add(self, pos, col, uv, tris):
        self.p.append(np.asarray(pos, 'f4'))
        self.c.append(np.asarray(col, 'f4'))
        self.u.append(np.asarray(uv, 'f4'))
        self.t.append(np.asarray(tris, 'u4')+self.n)
        self.n += len(pos)


def grid(rows, cols, wrap):
    t = []
    for i in range(rows-1):
        for j in range(cols if wrap else cols-1):
            a, b = i*cols+j, i*cols+(j+1) % cols
            t += [(a, a+cols, b), (b, a+cols, b+cols)]
    return t


def curve(S, knots):
    """A smooth curve through (s, value) knots."""
    from scipy.interpolate import PchipInterpolator
    k = np.array(knots, 'f8')
    return PchipInterpolator(k[:, 0], k[:, 1])(S)


def body(m, L, H, W, zc=None, rows=26, sides=14, belly=1.0, flat=0.0):
    """H and W: half height and half width as curves of S (0 nose, 1 tail root), in fractions of L. flat squares the section
    off, for a shark's or a tuna's underside. The body stops at the tail root; the tail is a fin."""
    S = np.linspace(0, 1, rows)
    P = np.linspace(0, np.pi*2, sides, endpoint=False)
    SS, PP = np.meshgrid(S, P, indexing='ij')
    h, w = curve(SS, H)*L, curve(SS, W)*L
    c = curve(SS, zc)*L if zc else 0*SS
    sp, cp = np.sin(PP), np.cos(PP)
    z = np.where(sp >= 0, h*sp, h*sp*belly)+c
    if flat:
        z = np.where(sp < 0, c+h*sp*(1-flat*(1-np.abs(sp)**2)), z)
    pos = np.stack([L*(.5-SS), w*cp, z], -1).reshape(-1, 3)
    col = np.stack([SS**1.5, .85+.15*np.abs(cp), 0*SS, 1+0*SS], -1).reshape(-1, 4)
    uv = np.stack([SS, sp], -1).reshape(-1, 2)
    t = grid(rows, sides, True)
    tip = len(pos)
    pos = np.vstack([pos, pos[:sides].mean(0, keepdims=True)])
    col = np.vstack([col, col[:1]])
    uv = np.vstack([uv, (0, 0)])
    for j in range(sides):
        t.append((j, tip, (j+1) % sides))
    m.add(pos, col, uv, t)


FIN_ROWS = 3


def fin(m, L, outline, side=0.0, y=0.0, plane='xz', bend=None, up=0.0, row=False, root=None):
    """A flat fin from an outline in metres. Triangulated as a fan from the outline's middle, with rows between root and rim so
    that it bends. bend: R at the rim (default: follows the body at that length). root: the two outline indices whose edge is
    grown into the body (default: first and last for an upright fin, the first two for a paired one).

    Everything that moves the fin on its own (bend, rowing) grows with the distance from that root edge, and the root edge
    takes the body's own R at its length: the root moves exactly with the skin it sits on. (Until 2026-11-11 both grew from
    the fan's middle, so the edge on the body moved most and the fins came away from it while swimming.)"""
    o = np.asarray(outline, 'f4').copy()
    n = len(o)
    if root is None:
        root = (0, 1) if plane != 'xz' else (0, n-1)
    # Sink the root edge a little into the body, so that no gap opens when the skin and fin bend.
    for k in root:
        o[k, 1] *= .82 if plane != 'xz' else .9
    c = o.mean(0)
    rows = FIN_ROWS
    ts = np.linspace(0, 1, rows)
    pts = np.vstack([c+(o-c)*t for t in ts])
    if plane == 'xz':
        pos = np.stack([pts[:, 0], np.full(len(pts), y), pts[:, 1]], 1)
    else:                                                            # 'xy': sideways, for pectorals and flukes
        pos = np.stack([pts[:, 0], pts[:, 1]+y, np.full(len(pts), up)], 1)
        pos[:, 2] += side*np.abs(pts[:, 1])
    # Distance of every point from the root edge, in the outline's plane, 0 on it and 1 at the farthest point of the rim.
    a, b = o[root[0]], o[root[1]]
    ab = b-a
    tt = np.clip(((pts-a) @ ab)/max(float(ab @ ab), 1e-9), 0, 1)
    d = np.linalg.norm(pts-(a+tt[:, None]*ab), axis=1)
    w = d/max(float(d.max()), 1e-6)
    # The body's R at this length (body() records how its rows map onto x).
    BL, off = getattr(m, 'axis', (L, 0.0))
    S = np.clip(.5-(pos[:, 0]-off)/BL, 0, 1)
    body_r = S**1.5
    r = body_r if bend is None else body_r+(np.minimum(1.0, body_r+bend)-body_r)*w**1.3
    # A: how far this fin rows on its own (paired fins), nothing at the root.
    col = np.stack([r, .72+.28*w, np.ones(len(pts)), w if row else 0*r], 1)
    uv = np.stack([np.clip(.5-pos[:, 0]/L, 0, 1), w], 1)
    t = []
    for i in range(rows-1):
        for j in range(n):
            a_, b_ = i*n+j, i*n+(j+1) % n
            t += [(a_, a_+n, b_), (b_, a_+n, b_+n)]
    for j in range(1, n-1):
        t.append((0, j, j+1))
    m.add(pos, col, uv, t)


# ---- reef and shoal fish: a body from a shape, plus its fins

def fish(L, depth, girth, a=.7, b=.8, ped=.03, tail='fork', tail_h=.17, dorsal=(), anal=(), pect=.14, ventral=.08, hump=0.0,
         bill=None, spines=0, finlets=0, pect_long=False):
    """Generic teleost. depth, girth: the body's greatest height and width, in fractions of L. a < 1 keeps the deepest point
    forward. dorsal/anal: (s0, s1, height in L) per fin."""
    m = Mesh()
    knots = np.linspace(0, 1, 13)
    def prof(s, top):
        return top*np.sin(np.pi*s**a)**b*(1-s*.0)+ped*s**4
    bl = .82                                                      # body: 82 % of the length, the rest is tail
    H = [(s, float(prof(s, depth/2)+.002)) for s in knots]
    W = [(s, float(girth/2*np.sin(np.pi*s**a)**(b+.25)+.002+ped*.35*s**4)) for s in knots]
    if hump:
        H = [(s, h+hump*np.exp(-((s-.12)/.1)**2)) for s, h in H]
    # L is the whole fish; the body goes from +L/2 to -L/2+tail; body() needs its own length.
    BL = L*bl
    k0 = len(m.p)
    # Shoals are thousands of drawn fish and not Nanite (their swimming is per vertex): the small ones stay very light.
    small = L < .3
    body(m, BL, H, W, rows=10 if small else (22 if L >= 1 else 16), sides=8 if small else (16 if L >= 1 else 12))
    m.p[k0][:, 0] += (L-BL)/2
    m.axis = (BL, (L-BL)/2)
    rootx = -L/2+(L-BL)
    def S2x(s):
        return L/2-s*BL
    t = tail_h*L
    tl = L-BL
    if tail == 'fork':
        o = [(rootx, ped*L*.8), (rootx-tl, t), (rootx-tl*.52, 0), (rootx-tl, -t), (rootx, -ped*L*.8)]
    elif tail == 'lunate':
        o = [(rootx, ped*L*.8), (rootx-tl*.8, t*1.3), (rootx-tl*.32, 0), (rootx-tl*.8, -t*1.3), (rootx, -ped*L*.8)]
    elif tail == 'round':
        o = [(rootx, ped*L*.8), (rootx-tl*.62, t*.75), (rootx-tl, t*.25), (rootx-tl, -t*.25), (rootx-tl*.62, -t*.75), (rootx, -ped*L*.8)]
    else:                                                            # 'square'
        o = [(rootx, ped*L*.8), (rootx-tl, t*.82), (rootx-tl*.9, 0), (rootx-tl, -t*.82), (rootx, -ped*L*.8)]
    fin(m, L, o)
    for s0, s1, h in dorsal:
        x0, x1 = S2x(s0), S2x(s1)
        top0 = float(prof(s0, depth/2))*BL
        top1 = float(prof(s1, depth/2))*BL
        o = [(x0, top0*.92), (x0-(x0-x1)*.22, top0+h*L), (x0-(x0-x1)*.72, (top0+top1)/2+h*L*.84), (x1-.05*L, top1+h*L*.55), (x1, top1*.9)]
        fin(m, L, o)
    for s0, s1, h in anal:
        x0, x1 = S2x(s0), S2x(s1)
        bot0, bot1 = float(prof(s0, depth/2))*BL, float(prof(s1, depth/2))*BL
        o = [(x0, -bot0*.92), (x1, -bot1*.9), (x1-.05*L, -bot1-h*L*.55), (x0-(x0-x1)*.55, -(bot0+bot1)/2-h*L)]
        fin(m, L, o, root=(0, 1))
    if bill:
        # A billfish's rostrum: a sword flat and wide (swordfish), or a round spear (marlin), from the upper jaw.
        blen, brad, flat = bill
        n, sides = 8, 8
        t = np.linspace(0, 1, n)
        P = np.linspace(0, np.pi*2, sides, endpoint=False)
        TT, PP = np.meshgrid(t, P, indexing='ij')
        r = brad*L*(1-.92*TT**.8)
        wide, high = (1.9, .45) if flat else (1.0, 1.0)
        z0 = float(prof(.02, depth/2))*BL*.25
        q = np.stack([L/2-.01*L+TT*blen*L, r*wide*np.cos(PP), z0+r*high*np.sin(PP)], -1).reshape(-1, 3)
        c = np.stack([np.zeros(n*sides), np.full(n*sides, .8), np.zeros(n*sides), np.ones(n*sides)], 1)
        m.add(q, c, np.stack([np.zeros(n*sides), np.sin(PP).reshape(-1)], 1), grid(n, sides, True))
    if spines:
        # A porcupinefish's spines: lying back along the skin, they stand out when it blows up (B .5 marks them for the
        # material, A 1 at the tip).
        rng = np.random.default_rng(7)
        pts, cols, uvs, tris = [], [], [], []
        for i in range(spines):
            sv = rng.uniform(.12, .86)
            ph = rng.uniform(0, np.pi*2)
            h = float(curve(np.array([sv]), H)[0])*BL
            w = float(curve(np.array([sv]), W)[0])*BL
            x0 = L/2-sv*BL
            base = np.array([x0, w*np.cos(ph), h*np.sin(ph)])
            rad = np.array([0, np.cos(ph), np.sin(ph)])
            ln = L*rng.uniform(.07, .11)
            tip = base+np.array([-ln*.85, 0, 0])+rad*ln*.3
            side = np.array([0, -np.sin(ph), np.cos(ph)])*L*.006
            k = len(pts)
            pts += [base-side, base+side, tip]
            r_ = sv**1.5
            cols += [(r_, .8, .5, 0), (r_, .8, .5, 0), (r_, .8, .5, 1)]
            uvs += [(sv, np.sin(ph))]*3
            tris.append((k, k+1, k+2))
        m.add(np.array(pts), np.array(cols), np.array(uvs), tris)
    if finlets:
        # Tuna: a row of little yellow flags on the tail stock, above and below.
        for i in range(finlets):
            sv = .78+.17*i/max(finlets-1, 1)
            x0 = S2x(sv)
            for sgn in (1, -1):
                hh = float(prof(sv, depth/2))*BL+ped*L*.4
                fin(m, L, [(x0+.008*L, sgn*hh*.95), (x0-.012*L, sgn*(hh+.022*L)), (x0-.016*L, sgn*hh*.95)])
    x = S2x(.3)
    wy = girth/2*BL*.85
    for sd in (-1, 1):
        if pect and pect_long:
            # Long sickle pectorals held out stiff (tuna, marlin, the lionfish's fans).
            o = [(x, sd*wy), (x-.05*L, sd*wy), (x-pect*L*1.1, sd*(wy+pect*L*.35)), (x-pect*L*1.15, sd*(wy+pect*L*.42)), (x-pect*L*.3, sd*(wy+pect*L*.3))]
            fin(m, L, o, plane='xy', side=-.3, up=-depth*BL*.1, bend=.3, row=True)
        elif pect:
            o = [(x, sd*wy), (x-.09*L, sd*wy), (x-pect*L*1.05, sd*(wy+pect*L*.55)), (x-pect*L*.82, sd*(wy+pect*L*.72)), (x-pect*L*.45, sd*(wy+pect*L*.62))]
            fin(m, L, o, plane='xy', side=-.42, up=-depth*BL*.07, bend=.5, row=True)
        if ventral:
            xv = S2x(.42)
            o = [(xv, sd*wy*.4), (xv-.05*L, sd*wy*.4), (xv-ventral*L, sd*(wy*.4+ventral*L*.5))]
            fin(m, L, o, plane='xy', side=-.9, up=-depth*BL*.34)
    return m


def goatfish():
    """Yellow goatfish: a slim reef fish that ploughs the sand with two long barbels under its chin."""
    m = fish(.3, .2, .12, a=.6, b=.75, tail='fork', tail_h=.17, dorsal=[(.25, .38, .1), (.55, .68, .07)], anal=[(.62, .75, .06)], pect=.1, ventral=.07)
    L = .3
    for sd in (-1, 1):
        t = np.linspace(0, 1, 5)
        q = np.stack([L*.46-t*L*.14, sd*(.006+t*.012), -.018-t*.022], 1)
        P = np.linspace(0, np.pi*2, 4, endpoint=False)
        TT, PP = np.meshgrid(np.arange(5), P, indexing='ij')
        r = .0018*(1-.6*t)
        pos = np.stack([q[TT, 0], q[TT, 1]+r[TT]*np.cos(PP), q[TT, 2]+r[TT]*np.sin(PP)], -1).reshape(-1, 3)
        m.add(pos, np.stack([np.zeros(20), np.full(20, .8), np.ones(20), np.zeros(20)], 1), np.stack([np.zeros(20), np.full(20, -.5)], 1), grid(5, 4, True))
    return m


def cowfish():
    """Honeycomb cowfish: a bony box of a body, triangular in section with a flat belly and a ridge along the back, two
    horns over the eyes and two under the tail; it sculls with its small fins and a fan of a tail."""
    m = fish(.4, .5, .42, a=.5, b=.4, ped=.04, tail='round', tail_h=.13, dorsal=[(.72, .8, .07)], anal=[(.74, .82, .07)], pect=.09, ventral=0)
    p = m.p[0]
    h = np.abs(p[:, 2]).max()
    w = np.abs(p[:, 1]).max()
    s_ = np.clip(.5-(p[:, 0]-(.4-.4*.82)/2)/(.4*.82), 0, 1)
    box = np.clip((s_-.04)/.12, 0, 1)*np.clip((.86-s_)/.12, 0, 1)
    # Triangle in section: the back narrows to a ridge, the belly is flat and wide.
    up = np.clip(p[:, 2]/max(h, 1e-6), -1, 1)
    p[:, 1] *= 1+box*(.25-.55*np.clip(up, 0, 1))
    p[:, 2] = np.where(up < 0, p[:, 2]*(1-.55*box), p[:, 2])
    L = .4
    for sd in (-1, 1):
        for x0, z0, d in ((L*.42, h*.55, (1, .2, .45)), (-L*.18, -h*.4, (-1, .25, -.2))):
            d = np.array(d, 'f8')
            d[1] *= sd
            d /= np.linalg.norm(d)
            base = np.array((x0, sd*w*.25, z0))
            P = np.linspace(0, np.pi*2, 5, endpoint=False)
            t = np.linspace(0, 1, 4)
            TT, PP = np.meshgrid(np.arange(4), P, indexing='ij')
            ax = np.cross(d, (0, 0, 1.0))
            ax /= max(np.linalg.norm(ax), 1e-6)
            bx = np.cross(d, ax)
            r = .006*(1-t)
            cpos = base[None]+d[None]*(t*.035)[:, None]
            pos = cpos[TT]+(r[TT]*np.cos(PP))[..., None]*ax+(r[TT]*np.sin(PP))[..., None]*bx
            m.add(pos.reshape(-1, 3), np.tile([.0, .85, 0, 1], (20, 1)), np.tile([.05, .5], (20, 1)), grid(4, 5, True))
    return m


def flounder():
    """Peacock flounder: a flatfish lying on the sand on its blind side, both eyes on top. Made as a thin deep fish and laid
    on its side; the material draws the blue rings and spots."""
    m = fish(.4, .62, .07, a=.62, b=.55, ped=.02, tail='round', tail_h=.14, dorsal=[(.04, .93, .05)], anal=[(.24, .93, .05)], pect=.07, ventral=0)
    for k in range(len(m.p)):
        q = m.p[k]
        m.p[k] = np.stack([q[:, 0], -q[:, 2], q[:, 1]], 1)
    return m


SARDINE = lambda: fish(.14, .2, .1, a=.72, b=.75, tail='fork', tail_h=.13, dorsal=[(.42, .58, .06)], anal=[(.72, .88, .035)], pect=.09, ventral=.05)
HERRING = lambda: fish(.26, .2, .1, a=.72, b=.75, tail='fork', tail_h=.13, dorsal=[(.42, .58, .07)], anal=[(.72, .88, .035)], pect=.09, ventral=.05)
GRUNT = lambda: fish(.26, .36, .14, a=.72, b=.75, tail='fork', tail_h=.15, dorsal=[(.28, .78, .095)], anal=[(.72, .9, .08)])
SNAPPER = lambda: fish(.42, .3, .13, a=.68, b=.8, tail='fork', tail_h=.19, dorsal=[(.3, .78, .08)], anal=[(.73, .9, .07)])
TANG = lambda: fish(.24, .62, .1, a=.82, b=.5, ped=.022, tail='lunate', tail_h=.17, dorsal=[(.16, .93, .07)], anal=[(.46, .93, .07)], pect=.12)
ANGEL = lambda: fish(.34, .72, .11, a=.86, b=.48, ped=.02, tail='round', tail_h=.17, dorsal=[(.22, .95, .15)], anal=[(.45, .95, .15)], pect=.12)
BUTTERFLY = lambda: fish(.15, .68, .12, a=.92, b=.48, ped=.02, tail='square', tail_h=.14, dorsal=[(.25, .94, .08)], anal=[(.5, .94, .08)], pect=.11)
SERGEANT = lambda: fish(.17, .52, .15, a=.76, b=.6, ped=.022, tail='fork', tail_h=.15, dorsal=[(.26, .9, .08)], anal=[(.6, .9, .08)])
PARROT = lambda: fish(.55, .34, .2, a=.62, b=.68, ped=.04, tail='square', tail_h=.15, dorsal=[(.26, .92, .05)], anal=[(.7, .92, .05)], pect=.13, hump=.012)
GROUPER = lambda: fish(.95, .34, .24, a=.58, b=.72, ped=.045, tail='round', tail_h=.14, dorsal=[(.25, .88, .075)], anal=[(.72, .88, .08)], pect=.16, ventral=.11)
COD = lambda: fish(.8, .24, .19, a=.6, b=.72, ped=.03, tail='square', tail_h=.12, dorsal=[(.28, .47, .08), (.5, .68, .07), (.7, .9, .05)], anal=[(.5, .7, .05), (.72, .9, .05)], pect=.12, ventral=.09)
TUNA = lambda: fish(1.5, .27, .24, a=.58, b=.78, ped=.012, tail='lunate', tail_h=.22, dorsal=[(.3, .46, .1), (.54, .62, .2)], anal=[(.6, .67, .2)], pect=.2, ventral=.05,
                    finlets=7, pect_long=True)
PUFFER = lambda: fish(.35, .44, .38, a=.6, b=.55, ped=.03, tail='round', tail_h=.12, dorsal=[(.7, .8, .07)], anal=[(.72, .82, .07)], pect=.1, ventral=0, spines=110)
SWORDFISH = lambda: fish(2.4, .19, .16, a=.48, b=.85, ped=.014, tail='lunate', tail_h=.25, dorsal=[(.18, .3, .2)], anal=[(.62, .7, .07)], pect=.13, ventral=0,
                         bill=(.42, .022, True), pect_long=True)
MARLIN = lambda: fish(2.8, .22, .16, a=.48, b=.85, ped=.014, tail='lunate', tail_h=.26, dorsal=[(.16, .66, .14)], anal=[(.6, .7, .07)], pect=.16, ventral=.08,
                      bill=(.24, .018, False), finlets=0, pect_long=True)
MAHI = lambda: fish(1.2, .27, .1, a=.28, b=.95, ped=.02, tail='fork', tail_h=.2, dorsal=[(.04, .88, .065)], anal=[(.48, .88, .055)], pect=.1, ventral=.07, hump=.035)
LIONFISH = lambda: fish(.32, .34, .14, a=.7, b=.75, ped=.03, tail='round', tail_h=.14, dorsal=[(.14, .55, .3), (.56, .84, .12)], anal=[(.68, .86, .1)], pect=.32, ventral=.12,
                        pect_long=True)
TRIGGER = lambda: fish(.45, .52, .13, a=.7, b=.6, ped=.025, tail='lunate', tail_h=.24, dorsal=[(.16, .26, .1), (.5, .86, .12)], anal=[(.5, .86, .12)], pect=.09)
TARPON = lambda: fish(1.6, .24, .13, a=.6, b=.72, ped=.03, tail='fork', tail_h=.17, dorsal=[(.48, .58, .13)], anal=[(.72, .85, .09)], pect=.12, ventral=.09)
BARRACUDA = lambda: fish(1.3, .13, .1, a=.45, b=.95, ped=.02, tail='fork', tail_h=.1, dorsal=[(.48, .55, .06), (.74, .84, .055)], anal=[(.74, .84, .05)], pect=.07, ventral=.05)
YELLOWTAIL = lambda: fish(.4, .27, .12, a=.68, b=.8, tail='fork', tail_h=.23, dorsal=[(.3, .75, .07)], anal=[(.72, .88, .06)], pect=.12)
HOGFISH = lambda: fish(.6, .38, .13, a=.5, b=.62, ped=.03, tail='lunate', tail_h=.18, dorsal=[(.14, .28, .18), (.28, .88, .08)], anal=[(.6, .88, .08)], pect=.12, hump=.02)
SQUIRREL = lambda: fish(.28, .34, .16, a=.66, b=.75, tail='fork', tail_h=.2, dorsal=[(.2, .55, .12), (.6, .76, .1)], anal=[(.68, .84, .1)], pect=.12, ventral=.08)
SPADEFISH = lambda: fish(.5, .78, .1, a=.78, b=.42, ped=.02, tail='lunate', tail_h=.2, dorsal=[(.2, .42, .08), (.5, .9, .22)], anal=[(.52, .9, .2)], pect=.11, ventral=.08)
PORKFISH = lambda: fish(.25, .52, .14, a=.7, b=.55, ped=.02, tail='fork', tail_h=.17, dorsal=[(.25, .9, .1)], anal=[(.65, .9, .09)], pect=.11, ventral=.07)
JACK = lambda: fish(.65, .36, .12, a=.62, b=.7, ped=.008, tail='lunate', tail_h=.24, dorsal=[(.3, .4, .07), (.48, .85, .07)], anal=[(.56, .85, .07)], pect=.18, ventral=.05, pect_long=True)
TRUMPET = lambda: fish(.75, .06, .05, a=.38, b=.9, ped=.012, tail='round', tail_h=.04, dorsal=[(.76, .86, .03)], anal=[(.76, .86, .03)], pect=.04, ventral=0)


def rounded(outline, root, it=3):
    """The outline as a smooth curve (Chaikin corner cutting), the root edge kept straight and where it was. Returns the
    new outline and its root indices (first and last point)."""
    o = [np.asarray(q, 'f8') for q in outline]
    n = len(o)
    i, j = root
    # Put the root edge between the last and the first point: walk from j round to i.
    start = j if (i - j) % n == n-1 or (j == (i+1) % n) else i
    end = i if start == j else j
    chain = [o[(start+k) % n] for k in range(n)]
    if not np.allclose(chain[-1], o[end]):
        chain = chain[::-1]
    for _ in range(it):
        new = [chain[0]]
        for a, b in zip(chain[:-1], chain[1:]):
            new += [a*.75+b*.25, a*.25+b*.75]
        new.append(chain[-1])
        chain = new
    return chain, (0, len(chain)-1)


def sfin(m, L, outline, root=None, **k):
    """fin() through rounded(): real fins have no corners except a sharp tip, which the caller doubles to keep."""
    plane = k.get('plane', 'xz')
    n = len(outline)
    if root is None:
        root = (0, 1) if plane != 'xz' else (0, n-1)
    o, r = rounded(outline, root)
    fin(m, L, o, root=r, **k)


# Sharks from photographs and FAO identification sheets, per species: body depth (of the length), where the snout ends
# and how blunt it is, first dorsal (start, end along the body, height), pectoral length and how far back its tip sweeps,
# the tail's upper lobe and the lower lobe's share of it, body width (girth) to depth.
SHARKS = dict(
    reef=dict(L=2.4, depth=.19, blunt=.0, dorsal=(.3, .44, .1), pect=(.2, .55), tail=.28, lower=.42, girth=.95),
    blacktip=dict(L=1.7, depth=.17, blunt=-.03, dorsal=(.31, .44, .11), pect=(.19, .6), tail=.28, lower=.45, girth=.9),
    bull=dict(L=2.6, depth=.25, blunt=.18, dorsal=(.29, .42, .09), pect=(.21, .5), tail=.25, lower=.45, girth=1.05),
    whitetip=dict(L=2.8, depth=.2, blunt=.12, dorsal=(.27, .45, .15), pect=(.33, .45), tail=.27, lower=.45, girth=.95, round_tips=True),
    tiger=dict(L=3.8, depth=.21, blunt=.3, dorsal=(.3, .42, .09), pect=(.17, .55), tail=.3, lower=.38, girth=1.0),
    white=dict(L=4.6, depth=.28, blunt=-.02, dorsal=(.33, .45, .11), pect=(.2, .4), tail=.24, lower=.85, girth=1.1, keel=True),
    hammer=dict(L=3.6, depth=.16, blunt=.0, dorsal=(.27, .38, .2), pect=(.14, .55), tail=.3, lower=.4, girth=.9, hammer=True),
)


def shark(kind='reef'):
    """A shark as a fish of cartilage: a spindle body flat underneath, the snout (conical, blunt or the hammer), five gill
    slits (the material draws them), sickle-shaped pectorals set low behind the gills, a tall first dorsal with a concave
    rear edge, small second dorsal, pelvic and anal fins, and the tail's long upper lobe with its notch near the tip.
    (Until 2026-11-12 one generic shark with angular, straight-edged fins served every species.)"""
    sp = SHARKS[kind]
    L, depth = sp['L'], sp['depth']
    m = Mesh()
    BL = L*.74
    b = sp['blunt']
    knots = [(0, .002+.01*b), (.025, .02+.05*b), (.07, depth*(.24+.25*b)), (.16, depth*.4), (.33, depth*.5), (.5, depth*.44), (.68, depth*.3),
             (.85, depth*.15), (.96, depth*.08), (1, depth*.065)]
    g = sp['girth']
    wid = [(0, .002+.012*b), (.025, .024+.07*b), (.07, depth*(.3+.3*b)*g), (.16, depth*.44*g), (.33, depth*.48*g), (.5, depth*.4*g), (.68, depth*.26*g),
           (.85, depth*.12*g), (.96, depth*.07*g), (1, depth*.06*g)]
    if sp.get('hammer'):
        # The head behind the hammer is narrow and flat.
        wid = [(0, .01), (.03, .03), (.07, depth*.28), (.16, depth*.38)]+wid[4:]
        knots = [(0, .006), (.03, .02), (.07, depth*.2), (.16, depth*.36)]+knots[4:]
    k0 = len(m.p)
    body(m, BL, knots, wid, flat=.5, sides=20, rows=40)
    m.p[k0][:, 0] += (L-BL)/2
    m.axis = (BL, (L-BL)/2)
    rx = L/2-BL
    S = lambda s_: L/2-s_*BL
    H = lambda s_: float(curve(np.array([s_]), knots)[0])*BL
    stock = H(1.0)
    # Tail: the upper lobe long and swept up at about 35 degrees, the notch below its tip (the terminal lobe), the lower
    # lobe shorter; the shark's own trailing edge between them concave.
    t = sp['tail']*L
    lo = sp['lower']
    o = [(rx+.02*L, stock*.85), (rx-.12*t, stock+.12*t), (rx-.55*t, .42*t), (rx-.86*t, .6*t), (rx-.95*t, .58*t),
         (rx-.9*t, .5*t), (rx-.8*t, .47*t), (rx-.74*t, .38*t),
         (rx-.42*t, .08*t), (rx-.4*t*lo-.12*t, -.55*t*lo), (rx-.36*t*lo-.08*t, -.6*t*lo), (rx-.12*t, -.12*t*lo), (rx+.02*L, -stock*.85)]
    if lo > .7:
        # The great white's tail is a crescent: both lobes long, the notch small.
        o = [(rx+.02*L, stock*.85), (rx-.1*t, stock+.1*t), (rx-.55*t, .5*t), (rx-.82*t, .78*t), (rx-.86*t, .72*t), (rx-.55*t, .2*t),
             (rx-.45*t, 0), (rx-.55*t, -.2*t), (rx-.8*t, -.64*t), (rx-.76*t, -.68*t), (rx-.5*t, -.42*t), (rx-.1*t, -.1*t), (rx+.02*L, -stock*.85)]
    sfin(m, L, o)
    if sp.get('keel'):
        for sd in (-1, 1):
            fin(m, L, [(rx+.08*L, sd*stock*.5), (rx+.02*L, sd*stock*1.1), (rx-.02*L, sd*stock*.5)], plane='xy', root=(0, 2))
    # First dorsal: a triangle with a curved front edge, a sharp tip and a concave rear edge with a free rear tip.
    d0, d1, dh = sp['dorsal']
    top0, top1 = H(d0), H(d1)
    hh = dh*L
    base = (S(d0)-S(d1))
    tip = (S(d0)-base*.62, top0+hh)
    if sp.get('round_tips'):
        o = [(S(d0), top0*.9), (S(d0)-base*.15, top0+hh*.55), (S(d0)-base*.4, top0+hh*.95), (S(d0)-base*.62, top0+hh*1.0), (S(d0)-base*.78, top0+hh*.85),
             (S(d0)-base*.82, top0+hh*.45), (S(d1)-base*.1, top1+hh*.06), (S(d1), top1*.9)]
    else:
        o = [(S(d0), top0*.9), (S(d0)-base*.2, top0+hh*.55), (S(d0)-base*.45, top0+hh*.9), tip, tip, (S(d0)-base*.66, top0+hh*.6),
             (S(d0)-base*.75, top0+hh*.25), (S(d1)-base*.15, top1+hh*.05), (S(d1), top1*.9)]
    sfin(m, L, o)
    # Second dorsal and anal: small, near the tail.
    for s0, s1, sgn, h2 in ((.72, .78, 1, .035), (.74, .8, -1, .03)):
        z0, z1 = H(s0)*sgn*.9, H(s1)*sgn*.9
        o = [(S(s0), z0), (S(s0)-.01*L, z0+sgn*h2*L), (S(s1)-.03*L, z1+sgn*h2*L*.6), (S(s1), z1)]
        sfin(m, L, o)
    # Pectorals: long sickles from low on the flank behind the gills, swept back; the tips rounded on a whitetip.
    pl, sweep = sp['pect']
    sx = S(.27)
    wy = float(curve(np.array([.27]), wid)[0])*BL*.8
    zlow = -H(.27)*.45
    for sd in (-1, 1):
        span_ = pl*L
        if sp.get('round_tips'):
            o = [(sx, sd*wy), (sx-.1*L, sd*wy), (sx-.12*L-sweep*span_*.5, sd*(wy+span_*.6)), (sx-.04*L-sweep*span_, sd*(wy+span_*.97)),
                 (sx-sweep*span_*.85, sd*(wy+span_)), (sx-sweep*span_*.5, sd*(wy+span_*.8)), (sx+.01*L, sd*(wy+span_*.25))]
        else:
            tipp = (sx-.02*L-sweep*span_, sd*(wy+span_))
            o = [(sx, sd*wy), (sx-.1*L, sd*wy), (sx-.12*L-sweep*span_*.45, sd*(wy+span_*.55)), tipp, tipp,
                 (sx-sweep*span_*.6, sd*(wy+span_*.82)), (sx-.02*L, sd*(wy+span_*.45)), (sx+.01*L, sd*(wy+span_*.15))]
        sfin(m, L, o, plane='xy', side=-.28, up=zlow+.28*wy, bend=.15)
        # Pelvic fins under the belly, two thirds back.
        pv = S(.6)
        wv = float(curve(np.array([.6]), wid)[0])*BL*.5
        o = [(pv, sd*wv), (pv-.06*L, sd*wv), (pv-.085*L, sd*(wv+.045*L)), (pv-.03*L, sd*(wv+.04*L))]
        sfin(m, L, o, plane='xy', side=-.35, up=-H(.6)*.6+.35*wv)
    if sp.get('hammer'):
        # The cephalofoil: a flat blade across the head, its front edge nearly straight with a notch in the middle (the
        # great hammerhead's), its back edge sweeping into the head; an eye at each end.
        hw = .26*L/2*2
        front = L/2
        for sd in (-1, 1):
            o = [(front+.005*L, 0), (front-.07*L, 0), (front-.075*L, sd*.05*L), (front-.06*L, sd*hw*.7), (front-.05*L, sd*hw), (front-.025*L, sd*hw*1.0),
                 (front-.012*L, sd*hw*.8), (front-.004*L, sd*hw*.4), (front-.01*L, sd*.02*L)]
            sfin(m, L, o, plane='xy', up=.004*L, bend=0, root=(0, 1))
            # A small dark disc at each tip of the hammer: the eye (fins carry no drawn eye).
            th_ = np.linspace(0, np.pi*2, 10, endpoint=False)
            ex, ey = front-.035*L, sd*hw*.97
            q = np.stack([np.full(10, ex)+.008*np.cos(th_), np.full(10, ey)+sd*.004, .004*L+.008*np.sin(th_)], 1)
            q = np.vstack([q, [(ex, ey+sd*.006, .004*L)]])
            m.add(q, np.tile([.0, .2, 0, 1], (11, 1)), np.tile([.0, .2], (11, 1)), [(10, k, (k+1) % 10) for k in range(10)])
    return m


def hammerhead():
    return shark('hammer')


def nurse_shark():
    """Broad-headed, sluggish, two dorsals set far back and a long low tail: it rests on the sand under ledges by day."""
    m = Mesh()
    L = 2.4
    BL = L*.74
    h = [(0, .01), (.06, .04), (.2, .085), (.42, .09), (.7, .05), (1, .02)]
    w = [(0, .03), (.06, .06), (.2, .1), (.42, .095), (.7, .05), (1, .015)]
    k0 = len(m.p)
    body(m, BL, h, w, flat=.7, sides=16, rows=30)
    m.p[k0][:, 0] += (L-BL)/2
    m.axis = (BL, (L-BL)/2)
    rx = -L/2+L-BL
    S = lambda s: L/2-s*BL
    fin(m, L, [(rx, .02*L), (rx-.1*L, .06*L), (rx-.26*L, .07*L), (rx-.25*L, .02*L), (rx-.08*L, -.02*L), (rx, -.02*L)])
    for s0, s1, hh in ((.52, .62, .075), (.72, .8, .06)):
        z = float(curve(np.array([(s0+s1)/2]), h)[0])*BL
        fin(m, L, [(S(s0), z*.9), (S(s0+.05), z+hh*L), (S(s1), z+hh*L*.8), (S(s1), z*.9)])
    for sd in (-1, 1):
        x, y = S(.28), .09*L
        fin(m, L, [(x, sd*y), (x-.12*L, sd*y), (x-.13*L, sd*(y+.15*L)), (x-.04*L, sd*(y+.14*L))], plane='xy', side=-.12, up=-.04, bend=.1)
    return m


# Batoid planforms, from photographs seen from above: per share of the half span (0 the midline, 1 the wing tip), where the
# leading and the trailing edge lie, in disc lengths (nose +.5, back of the disc -.5). The tip is where they meet.
RAYS = dict(
    # Spotted eagle ray: a domed head standing out ahead of the wings like a duck's bill, wings swept back to sharp tips, a
    # concave trailing edge, a whip of a tail three disc lengths long.
    # 2026-11-11: broader wings (the chord half way out was .4 of the disc and the ray read as a gull), the leading edge
    # bowed forward, the tips still sharp.
    eagle=dict(le=[(0, .5), (.04, .49), (.075, .43), (.095, .31), (.13, .28), (.3, .2), (.55, .08), (.78, -.04), (.92, -.15), (1, -.26)],
               te=[(0, -.5), (.07, -.5), (.12, -.45), (.25, -.43), (.5, -.37), (.72, -.33), (.9, -.29), (1, -.26)],
               body=.13, body_w=.11, wing=.022),
    # Manta: a broad blunt head, the mouth across its front, cephalic fins either side; long sickle wings.
    manta=dict(le=[(0, .4), (.07, .4), (.1, .36), (.2, .27), (.45, .1), (.75, -.1), (1, -.34)],
               te=[(0, -.5), (.09, -.49), (.15, -.42), (.3, -.36), (.6, -.38), (.85, -.4), (1, -.34)],
               body=.11, body_w=.14, wing=.018),
    # Southern stingray: a rhomb with rounded corners and a short pointed snout, lying flat on the sand.
    sting=dict(le=[(0, .5), (.12, .44), (.4, .3), (.75, .12), (.92, .02), (1, -.06)],
               te=[(0, -.5), (.14, -.47), (.4, -.36), (.75, -.2), (.92, -.12), (1, -.06)],
               body=.1, body_w=.25, wing=.03),
)


def ray(span=2.2, length=None, kind='eagle', tail=2.6, tail_w=.022):
    """A batoid: a flat disc of wings, not a body with fins. R: share of the half span (the material flaps by it).
    tail: the whip's length in metres; tail_w its radius at the root."""
    m = Mesh()
    spec = RAYS[kind]
    L = length or span*.5
    half = span/2
    cols, rows = 33, 17
    V = np.linspace(-1, 1, cols)
    a = np.abs(V)
    le, te = curve(a, spec['le'])*L, curve(a, spec['te'])*L
    u = np.linspace(0, 1, rows)
    UU, VV = np.meshgrid(u, V, indexing='ij')
    A = np.abs(VV)
    x = le[None, :]+(te-le)[None, :]*UU
    y = VV*half
    chord = np.sin(np.pi*np.clip(UU, 0, 1))**.55
    # A domed body down the middle, thin wings that thin out further to the tip.
    dome = spec['body']*L*np.exp(-(A/spec['body_w'])**2)*np.sin(np.pi*np.clip((x/L+.5), 0, 1))**.7
    wing = spec['wing']*L*(1-A)**.8*chord
    z_top = dome+wing
    z_bot = -(dome*.42+wing*.6)
    # U for the pattern: along the body, 0 the nose; the same on top and below.
    U = np.clip(.5-x/L, 0, 1).reshape(-1)
    col = np.stack([A.reshape(-1)**1.15, .9+.1*(1-A.reshape(-1)), np.zeros(rows*cols), np.ones(rows*cols)], 1)
    for z, v in ((z_top, .9), (z_bot, -.9)):
        m.add(np.stack([x, y, z], -1).reshape(-1, 3), col, np.stack([U, np.full(rows*cols, v)], 1), grid(rows, cols, False))
    # Tail: a whip from the back of the disc, R grows along it.
    n, sides = 14, 5
    tt = np.linspace(0, 1, n)
    P = np.linspace(0, np.pi*2, sides, endpoint=False)
    TT, PP = np.meshgrid(tt, P, indexing='ij')
    rad = tail_w*(1-.88*TT**.6)
    q = np.stack([-L*.45-TT*tail, rad*np.cos(PP), rad*np.sin(PP)+spec['body']*L*.15], -1).reshape(-1, 3)
    c2 = np.stack([(TT**1.2).reshape(-1), np.ones(n*sides), np.ones(n*sides), np.zeros(n*sides)], 1)
    m.add(q, c2, np.stack([np.ones(n*sides), np.ones(n*sides)*.9], 1), grid(n, sides, True))
    if kind == 'manta':
        # Cephalic fins: rolled paddles from the head's corners, forward past the mouth.
        for sd in (-1, 1):
            y0, y1 = sd*.075*half, sd*.12*half
            o = [(.36*L, y0), (.62*L, y0*1.05), (.66*L, (y0+y1)/2), (.6*L, y1), (.33*L, y1)]
            fin(m, L, o, plane='xy', up=spec['body']*L*.25, bend=0)
    return m


def turtle(L=1.0, leather=False):
    """A green turtle, from photographs seen from above and the side: a low, wide teardrop of a carapace (widest a third of
    the way back, about .78 as wide as long, its top only a fifth of the length high), a thin overhanging rim, a flat
    plastron, a short blunt head with a beak on a neck that comes out from under the rim, long curved fore flippers that
    taper to a point and small rounded hind ones. R marks flippers, head and neck only; the shell stays rigid.
    U along the shell, V +1 on the carapace and -1 under it: the material draws the scutes from them.
    (The 2026-11 shell was an 18-row spindle drawn with bands: a striped melon.)"""
    m = Mesh()
    rows, cols = 30, 36
    s_ = np.linspace(0, 1, rows)
    th = np.linspace(0, np.pi*2, cols, endpoint=False)
    S, T = np.meshgrid(s_, th, indexing='ij')
    # Outline in plan: the half width along the length, nose (s 0) to tail (s 1).
    half = .39*L*np.interp(S, [0, .06, .2, .36, .6, .82, .95, 1], [.0, .55, .88, 1.0, .9, .6, .25, 0])**.9
    x = L*(.44-S*.9)
    cx, sx = np.cos(T), np.sin(T)
    # Carapace on top (sx>0), plastron flat below (sx<0); a rim a couple of cm thick where they meet.
    hump = .19*L*np.interp(S, [0, .08, .3, .55, .85, 1], [0, .55, 1, .92, .45, 0])
    top = hump*np.clip(sx, 0, 1)**.55*(1-.08*np.abs(cx)**4)
    under = -.07*L*np.interp(S, [0, .1, .4, .8, 1], [0, .7, 1, .6, 0])*np.clip(-sx, 0, 1)**.35
    rim = .012*L*np.clip(1-np.abs(sx)*4, 0, 1)
    z = np.where(sx >= 0, top, under)+rim*0
    y = half*cx*(1+.04*np.clip(sx, 0, 1))
    q = np.stack([x, y, z], -1).reshape(-1, 3)
    col = np.stack([0*S, .85+.15*np.clip(sx, 0, 1), 0*S, 1+0*S], -1).reshape(-1, 4)
    uv = np.stack([S, np.sign(sx)*np.abs(cx)**0+0*S], -1).reshape(-1, 2)
    uv[:, 1] = np.where(sx.reshape(-1) >= 0, 1.0-.6*np.abs(cx.reshape(-1)), -1.0)
    tri = grid(rows, cols, True)
    m.add(q, col, uv, tri)
    # Neck and head: out from under the front of the shell, the head a blunt wedge with a beak, held a little down.
    n, sides = 12, 12
    t = np.linspace(0, 1, n)
    P = np.linspace(0, np.pi*2, sides, endpoint=False)
    TT, PP = np.meshgrid(t, P, indexing='ij')
    cxh = L*(.34+.27*TT)
    rad = L*np.interp(TT, [0, .3, .45, .7, .9, 1], [.07, .055, .062, .066, .045, .012])
    zc = L*(.0-.03*TT)
    hd = np.stack([cxh, rad*np.cos(PP)*1.05, zc+rad*np.sin(PP)*.82], -1).reshape(-1, 3)
    rr = (np.clip((TT-.0)/1.0, 0, 1)*.25).reshape(-1)
    # U .05 at the neck to 0 at the beak, so that the material's eye (EyeU .03) sits on the head; B 0: skin, not fin.
    m.add(hd, np.stack([rr, np.full(n*sides, .9), np.zeros(n*sides), np.ones(n*sides)], 1),
          np.stack([(.05*(1-TT)).reshape(-1), np.sin(PP).reshape(-1)], 1), grid(n, sides, True))
    def flipper(sd, x0, y0, length, width, sweep, curve_, thick):
        # A flattened tube: root inside the shell, curving back, tapering to a point; R grows from the root.
        k, ring = 14, 8
        t = np.linspace(0, 1, k)
        a = np.linspace(0, np.pi*2, ring, endpoint=False)
        cxp = x0-sweep*length*t**1.2+curve_*length*np.sin(np.pi*t)*.35
        cyp = sd*(y0+length*t)
        cz = -.02*L-.04*L*t
        chord = width*np.interp(t, [0, .15, .45, .8, 1], [.55, 1, .9, .5, .05])
        th_ = thick*np.interp(t, [0, .2, 1], [1, .6, .15])
        TT, AA = np.meshgrid(np.arange(k), a, indexing='ij')
        pos = np.stack([cxp[TT]+chord[TT]*.5*np.cos(AA), cyp[TT]+0*AA, cz[TT]+th_[TT]*np.sin(AA)], -1).reshape(-1, 3)
        rr = np.repeat(np.clip(t-.08, 0, 1)**1.1, ring)
        colf = np.stack([rr, np.full(k*ring, .85), np.ones(k*ring), np.zeros(k*ring)], 1)
        m.add(pos, colf, np.stack([rr, np.sin(AA).reshape(-1)*.5], 1), grid(k, ring, True))
    for sd in (-1, 1):
        flipper(sd, .2*L, .24*L, .5*L, .15*L, .55, .5, .02*L)
        flipper(sd, -.3*L, .15*L, .13*L, .1*L, .25, .1, .012*L)
    return m


def jellyfish(R=.16, tentacles=14, long=.9, box=0.0, tall=.55, arms=0):
    """A moon jelly: a translucent bell, four horseshoe gonads and fine tentacles. R: 1 at the bell's rim; B the tentacles."""
    m = Mesh()
    rows, cols = 12, 28
    s, p = np.linspace(0, 1, rows), np.linspace(0, np.pi*2, cols, endpoint=False)
    S, P = np.meshgrid(s, p, indexing='ij')
    rad = R*np.sin(S*np.pi*.55)**.85*(1+.012*np.cos(P*16)*S)
    # A box jelly's bell is a rounded cube: four flat sides, a tentacle bunch at each corner.
    rad = rad*(1+box*(np.abs(np.cos(P*2))**.5-.6))
    z = R*tall*np.cos(S*np.pi*.5)
    q = np.stack([rad*np.cos(P), rad*np.sin(P), z], -1).reshape(-1, 3)
    uv = np.stack([S, np.cos(P*2)], -1).reshape(-1, 2)
    m.add(q, np.stack([S, .9+0*S, 0*S, 1+0*S], -1).reshape(-1, 4), uv, grid(rows, cols, True))
    rng = np.random.default_rng(int(R*1000)+tentacles)
    for i in range(tentacles):
        a = (np.round(i/tentacles*4-.5)+.5)*np.pi/2+rng.uniform(-.08, .08) if box else i/tentacles*np.pi*2+rng.uniform(-.1, .1)
        t = np.linspace(0, 1, 8)
        L = rng.uniform(.6, 1.0)*long
        r0 = R*.98
        pos = np.stack([(r0*(1-t*.3)+.015*np.sin(t*7+a))*np.cos(a), (r0*(1-t*.3)+.015*np.cos(t*7+a))*np.sin(a), -L*t], 1)
        w = .0022*(1.2-t)
        side = np.array((-np.sin(a), np.cos(a), 0))
        pts = np.stack([pos-side*w[:, None], pos+side*w[:, None]], 1).reshape(-1, 3)
        rr = np.repeat(t, 2)
        m.add(pts, np.stack([rr, np.ones(16), np.ones(16), np.zeros(16)], 1), np.stack([rr, np.zeros(16)], 1), grid(8, 2, False))
    for i in range(arms):
        a = i/max(arms, 1)*np.pi*2+.3
        t = np.linspace(0, 1, 10)
        L = long*rng.uniform(.45, .7)
        pos = np.stack([R*.18*np.cos(a)+.03*np.sin(t*9+a)*R*4, R*.18*np.sin(a)+.03*np.cos(t*8+a)*R*4, -L*t], 1)
        w = R*.16*(1-.6*t)
        side = np.array((-np.sin(a), np.cos(a), 0))
        pts = np.stack([pos-side*w[:, None], pos+side*w[:, None]], 1).reshape(-1, 3)
        rr = np.repeat(t, 2)
        m.add(pts, np.stack([rr, np.full(20, .8), np.ones(20), np.zeros(20)], 1), np.stack([rr, np.ones(20)*.5], 1), grid(10, 2, False))
    return m


def cetacean(L, depth, girth, a=.55, dorsal=.09, dorsal_s=.46, pect=.15, fluke=.3, knots=None, wknots=None, flipper='paddle'):
    """A whale or dolphin: a spindle narrowing to a deep, flat-sided tail stock that ends in horizontal flukes; the beat
    goes up and down (the material's mode 1). wknots: half widths, if the body is not round (the tail stock is not)."""
    m = Mesh()
    BL = L*.9
    if knots is None:
        knots = [(0, .012), (.03, depth*.28), (.12, depth*.42), (.34, depth*.5), (.65, depth*.3), (.88, depth*.1), (1, .012)]
    wid = wknots or [(s, h*girth/depth) for s, h in knots]
    k0 = len(m.p)
    body(m, BL, knots, wid, rows=34, sides=16)
    m.p[k0][:, 0] += (L-BL)/2
    m.axis = (BL, (L-BL)/2)
    S = lambda s: L/2-s*BL
    root = L/2-BL
    fh = fluke*L/2
    # Flukes: swept-back leading edges, a straight trailing edge with a notch in the middle, starting inside the tail stock
    # (they used to start at its point, and showed a gap).
    stock = float(curve(np.array([.97]), wid)[0])*BL
    for sd in (-1, 1):
        o = [(root+.045*L, 0), (root+.035*L, sd*stock*.9), (root+.005*L, sd*.05*L), (root-.03*L, sd*fh*.55), (root-.06*L, sd*fh*.92),
             (root-.075*L, sd*fh), (root-.07*L, sd*fh*.82), (root-.058*L, sd*fh*.45), (root-.06*L, sd*fh*.12), (root-.052*L, 0)]
        fin(m, L, o, plane='xy', bend=.2)
    s_p = .27 if flipper == 'humpback' else .25
    h_p = float(curve(np.array([s_p]), knots)[0])*BL
    w_p = float(curve(np.array([s_p]), wid)[0])*BL
    x = S(s_p)
    for sd in (-1, 1):
        if flipper == 'humpback':
            # A humpback's flipper: a third of the body long, white, its leading edge knobbed with about ten tubercles. Photos
            # (2026-11-11 review): narrow at the root, broadest a quarter of the way out, tapering to a point, gently curved
            # like a banana and swept well back along the belly. The old even chord read as a plank hanging down.
            n = 21
            t = np.linspace(0, 1, n)
            span_ = pect*L*.92
            sweep = 1.15*span_
            chord_ = L*np.interp(t, [0, .22, .55, .85, 1], [.05, .072, .058, .03, .008])
            bow = .028*L*np.sin(np.pi*t)
            knob = .007*L*(np.cos(t*np.pi*19)*.5+.5)*(t > .06)*(t < .92)
            out = [sd*(w_p*.85+span_*t[i]) for i in range(n)]
            lead = [(x+.01*L-sweep*t[i]+bow[i]+knob[i], out[i]) for i in range(n)]
            trail = [(x+.01*L-sweep*t[i]+bow[i]-chord_[i], out[i]) for i in range(n)][::-1]
            tip = [(x+.01*L-sweep*1.02+bow[-1]-chord_[-1]*.5, sd*(w_p*.85+span_*1.02))]
            o = lead+tip+trail
            side = -.24
            yr = w_p*.85
            fin(m, L, o, plane='xy', side=side, up=-h_p*.42-side*yr, bend=.15, row=False, root=(0, len(o)-1))
        elif flipper == 'orca':
            # An orca's pectorals are broad rounded paddles, a fifth of the body long, held out and down at about 35 degrees.
            y = w_p*.85
            span_ = pect*L
            o = [(x, sd*y), (x-.085*L, sd*y), (x-.11*L, sd*(y+span_*.35)), (x-.12*L, sd*(y+span_*.75)), (x-.095*L, sd*(y+span_*.98)),
                 (x-.06*L, sd*(y+span_*1.0)), (x-.03*L, sd*(y+span_*.8)), (x-.012*L, sd*(y+span_*.4))]
            sfin(m, L, o, plane='xy', side=-.7, up=-h_p*.4+.7*y, bend=.1)
        else:
            # A dolphin's: small, pointed, swept back, held out at about 30 degrees below level.
            y = w_p*.85
            o = [(x, sd*y), (x-.07*L, sd*y), (x-.14*L, sd*(y+pect*L*.85)), (x-.16*L, sd*(y+pect*L)), (x-.13*L, sd*(y+pect*L*.92)), (x-.03*L, sd*(y+pect*L*.35))]
            sfin(m, L, o, plane='xy', side=-.58, up=-h_p*.4+.58*y, bend=.1)
    if dorsal:
        top = float(curve(np.array([dorsal_s]), knots)[0])*BL
        fin(m, L, [(S(dorsal_s-.04), top*.92), (S(dorsal_s+.06), top+dorsal*L), (S(dorsal_s+.09), top+dorsal*L*.86), (S(dorsal_s+.1), top*.85)])
    return m


def moray():
    """A moray's front half, out of its hole, gaping: the rest is in the rock. It has no paired fins: a fold all along the back."""
    m = Mesh()
    L = 1.4
    # Deep, flattened from side to side, a blunt snout, the head swollen behind the jaw (the muscles that hold it gaping),
    # tapering to a point at the tail; the earlier tube had none of that and read as a stick on the sand.
    h = [(0, .008), (.025, .026), (.07, .04), (.13, .056), (.2, .05), (.45, .048), (.75, .036), (.92, .018), (1, .004)]
    w = [(0, .008), (.025, .02), (.07, .03), (.13, .036), (.2, .029), (.45, .026), (.75, .02), (.92, .01), (1, .003)]
    k0 = len(m.p)
    body(m, L, h, w, rows=34, sides=12)
    # Lying in a slow S, as a moray does on a ledge or half out of a hole; the material's soft-body motion moves it on.
    p = m.p[k0]
    s = np.clip(.5-p[:, 0]/L, 0, 1)
    p[:, 1] += .07*L*np.sin(s*np.pi*1.6)*np.clip(s*3, 0, 1)
    # The mouth: a dark gape line from the snout back to the eye, the lower jaw a little open.
    gape = (s < .07) & (p[:, 2] < 0)
    p[gape, 2] -= .012*L*(1-s[gape]/.07)
    # The fold along the back from behind the head to the tail, and under the tail half (the anal fin): one fin each,
    # following the S of the body.
    def fold(s0, s1, hgt, below):
        ss = np.linspace(s0, s1, 14)
        xs = L*(.5-ss)
        ys = .07*L*np.sin(ss*np.pi*1.6)*np.clip(ss*3, 0, 1)
        top = curve(ss, h)*L
        sign = -1 if below else 1
        base = np.stack([xs, ys, sign*top*.92], 1)
        tip = np.stack([xs, ys, sign*(top+hgt*L*np.sin(np.pi*np.clip((ss-s0)/(s1-s0)*1.1, 0, 1))**.5)], 1)
        pts = np.stack([base, tip], 1).reshape(-1, 3)
        r = np.repeat(np.clip(ss, 0, 1)**1.5, 2)
        col = np.stack([r, np.tile([.75, 1.0], 14), np.ones(28), np.zeros(28)], 1)
        m.add(pts, col, np.stack([np.repeat(ss, 2), np.tile([0, 1.0], 14)], 1), grid(14, 2, False))
    fold(.15, 1.0, .022, False)
    fold(.5, 1.0, .016, True)
    return m


def octopus():
    """A Caribbean reef octopus resting on the sand, as in photographs: the mantle a soft bag raised up and back behind the
    head, the head with an eye bulging on each side, eight arms thick at the root and joined there by a web, lying on the
    sand and curling at their tips. Arm span about a metre. R grows along each arm (the material's soft-body motion);
    the mantle has a little of it, for breathing. (It was a ball on eight spikes.)"""
    m = Mesh()
    # Head and mantle: one surface of revolution along an axis from the head (front, low) to the mantle's end (back, high).
    a0, a1 = np.array((.05, 0, .055)), np.array((-.22, 0, .2))
    ax = a1-a0
    Lx = np.linalg.norm(ax)
    ax /= Lx
    up = np.cross(np.cross(ax, (0, 0, 1)), ax)
    up /= np.linalg.norm(up)
    side = np.cross(ax, up)
    n, ring = 22, 16
    t = np.linspace(0, 1, n)
    rad = np.interp(t, [0, .06, .2, .3, .45, .7, .9, 1], [.0, .05, .062, .052, .072, .078, .05, .0])
    P = np.linspace(0, np.pi*2, ring, endpoint=False)
    TT, PP = np.meshgrid(np.arange(n), P, indexing='ij')
    centre = a0[None, None]+(t[TT]*Lx)[..., None]*ax[None, None]
    rr = rad[TT][..., None]
    # The body sags onto the arms underneath, and the eyes stand out of the head's sides.
    eye = np.exp(-((t[TT]-.17)/.06)**2)*np.exp(-((np.abs(np.sin(PP))-1.0)/.35)**2)*(np.cos(PP) > -.2)
    rr = rr*(1+.35*eye[..., None])
    pos = centre+rr*(np.cos(PP)[..., None]*up[None, None]+np.sin(PP)[..., None]*side[None, None])
    pos[..., 2] = np.maximum(pos[..., 2], .03)
    pos = pos.reshape(-1, 3)
    r_ = (.12*t[TT]).reshape(-1)
    # Eyes as skin, not fin; U .05..0 on the head so the material's eye (EyeU) lands on the bulge.
    U = (t[TT]*.5).reshape(-1)
    m.add(pos, np.stack([r_, np.full(len(pos), .9), np.zeros(len(pos)), np.ones(len(pos))], 1), np.stack([U, np.sin(PP).reshape(-1)], 1), grid(n, ring, True))
    rng = np.random.default_rng(5)
    arms = []
    for i in range(8):
        h = (i+.5)/8*np.pi*2+rng.normal(0, .12)
        k = 26
        t = np.linspace(0, 1, k)
        reach = rng.uniform(.42, .56)
        # Out along the sand, a slow bend, then a curl of one or two turns at the tip.
        curl_dir = 1 if rng.random() < .5 else -1
        ang = h+curl_dir*(.35*t+np.clip((t-.62)/.38, 0, 1)**1.6*rng.uniform(4.5, 7.5))
        stepl = np.full(k, reach/(k-1))*np.interp(t, [0, .6, 1], [1, 1, .55])
        x, y = [.02+.035*np.cos(h)], [.035*np.sin(h)]
        for j in range(1, k):
            x.append(x[-1]+stepl[j]*np.cos(ang[j]))
            y.append(y[-1]+stepl[j]*np.sin(ang[j]))
        x, y = np.array(x), np.array(y)
        r = np.interp(t, [0, .12, .5, 1], [.03, .022, .012, .0025])
        # Lying on the sand (the centre a radius up), rising into the body at the root; a tip lifted now and then.
        z = r*.9+np.interp(t, [0, .15, 1], [.035, 0, 0])+(.025*np.clip((t-.8)/.2, 0, 1) if rng.random() < .4 else 0)
        ring = 8
        P = np.linspace(0, np.pi*2, ring, endpoint=False)
        TT, PP = np.meshgrid(np.arange(k), P, indexing='ij')
        tx = np.gradient(x)
        ty = np.gradient(y)
        tl = np.hypot(tx, ty)+1e-9
        nx, ny = -ty/tl, tx/tl
        pos = np.stack([x[TT]+r[TT]*np.cos(PP)*nx[TT], y[TT]+r[TT]*np.cos(PP)*ny[TT], z[TT]+r[TT]*.8*np.sin(PP)], -1).reshape(-1, 3)
        rr = (t[TT]**1.2).reshape(-1)
        # V -1 underneath, where the suckers are (the pattern pales there).
        m.add(pos, np.stack([rr, np.full(k*ring, .85), np.zeros(k*ring), np.ones(k*ring)], 1), np.stack([(.3+.7*t[TT]).reshape(-1), np.sin(PP).reshape(-1)], 1),
              grid(k, ring, True))
        arms.append(np.stack([x, y, z+r*.5], 1))
    # The web between neighbouring arms, out to a fifth of their length, sagging a little between them.
    centre = np.array((.02, 0, .06))
    for i in range(8):
        A, B = arms[i], arms[(i+1) % 8]
        k = 7
        rows = []
        for j in range(k):
            f = j/(k-1)
            pa, pb = A[int(f*5)], B[int(f*5)]
            mid = (pa+pb)/2
            mid[2] -= .01*f
            mid = centre+(mid-centre)*(1-.25*f)
            rows += [pa, mid, pb]
        pts = np.array(rows)
        rr = np.repeat(np.linspace(0, .2, k), 3)
        m.add(pts, np.stack([rr, np.full(k*3, .7), np.zeros(k*3), np.ones(k*3)], 1), np.stack([np.full(k*3, .35), np.full(k*3, -.5)], 1), grid(k, 3, False))
    return m


def seal():
    """A harbour seal: a fat spindle with a small head, foreflippers and hind flippers held together like a tail."""
    m = Mesh()
    L = 1.6
    BL = L*.86
    h = [(0, .02), (.05, .07), (.12, .075), (.2, .08), (.45, .135), (.7, .1), (.92, .04), (1, .02)]
    k0 = len(m.p)
    body(m, BL, h, h, rows=28, sides=14)
    m.p[k0][:, 0] += (L-BL)/2
    m.axis = (BL, (L-BL)/2)
    root = -L/2+L-BL
    fin(m, L, [(root+.02, .012), (root-.14*L, .12), (root-.13*L, -.12), (root+.02, -.012)], plane='xy')
    for sd in (-1, 1):
        x, y = L/2-.28*BL, .12
        fin(m, L, [(x, sd*y), (x-.1, sd*y), (x-.2, sd*(y+.22)), (x-.1, sd*(y+.24))], plane='xy', side=-.6, up=-.07, bend=.25)
    return m


SPECIES = dict(
    Sardine=SARDINE, Herring=HERRING, Grunt=GRUNT, Snapper=SNAPPER, Tang=TANG, Angelfish=ANGEL, Butterflyfish=BUTTERFLY, Sergeant=SERGEANT,
    Pufferfish=PUFFER, Swordfish=SWORDFISH, BlueMarlin=MARLIN, MahiMahi=MAHI, Lionfish=LIONFISH, QueenTriggerfish=TRIGGER,
    YellowtailSnapper=YELLOWTAIL, Hogfish=HOGFISH, Squirrelfish=SQUIRREL, Spadefish=SPADEFISH, Porkfish=PORKFISH, HorseEyeJack=JACK,
    Goatfish=goatfish, Cowfish=cowfish, Flounder=flounder,
    Parrotfish=PARROT, Grouper=GROUPER, Cod=COD, Tuna=TUNA, Tarpon=TARPON, Barracuda=BARRACUDA, Trumpetfish=TRUMPET, Moray=moray,
    ReefShark=lambda: shark('reef'), BullShark=lambda: shark('bull'), Blacktip=lambda: shark('blacktip'),
    OceanicWhitetip=lambda: shark('whitetip'), GreatWhite=lambda: shark('white'),
    BoxJellyfish=lambda: jellyfish(.12, 16, 2.2, box=.35, tall=1.1), SeaNettle=lambda: jellyfish(.11, 24, 1.6, tall=.6, arms=4), LionsMane=lambda: jellyfish(.45, 70, 3.2, tall=.45, arms=8), TigerShark=lambda: shark('tiger'), Hammerhead=hammerhead, NurseShark=nurse_shark,
    EagleRay=lambda: ray(2.1, 1.05, 'eagle', tail=2.8, tail_w=.022), Manta=lambda: ray(5.0, 2.2, 'manta', tail=1.4, tail_w=.03),
    Stingray=lambda: ray(1.3, 1.25, 'sting', tail=1.6, tail_w=.035),
    GreenTurtle=lambda: turtle(1.05), Jellyfish=jellyfish, Octopus=octopus, Seal=seal,
    Dolphin=lambda: cetacean(2.5, .22, .21, dorsal=.11, dorsal_s=.42, pect=.15, fluke=.26,
                             knots=[(0, .007), (.05, .018), (.08, .055), (.16, .085), (.36, .11), (.66, .065), (.9, .017), (1, .006)]),
    # An adult male: dorsal fin up to 1.8 m (a quarter of the length), a blunt rounded head with no beak, a stout body.
    Orca=lambda: cetacean(7.0, .26, .24, dorsal=.24, dorsal_s=.4, pect=.19, fluke=.27, flipper='orca',
                          knots=[(0, .03), (.03, .07), (.1, .11), (.3, .13), (.5, .12), (.7, .075), (.88, .03), (1, .014)]),
    Humpback=lambda: cetacean(13.0, .22, .2, dorsal=.02, dorsal_s=.66, pect=.3, fluke=.32, flipper='humpback',
                              knots=[(0, .012), (.03, .04), (.1, .07), (.25, .105), (.45, .1), (.68, .066), (.85, .04), (.95, .026), (1, .018)],
                              # A flat, tapering head seen from above (the blunt end looked sawn off).
                              wknots=[(0, .012), (.03, .04), (.1, .07), (.3, .1), (.5, .085), (.7, .045), (.85, .018), (1, .009)]),
)


def write_glb(path, m):
    p, c, u, t = np.concatenate(m.p), np.concatenate(m.c), np.concatenate(m.u), np.concatenate(m.t)
    a, b, d = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
    fn = np.cross(b-a, d-a)
    n = np.zeros_like(p)
    for i in range(3):
        np.add.at(n, t[:, i], fn)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    gp = np.stack([p[:, 0], p[:, 2], p[:, 1]], 1).astype('f4')
    gn = np.stack([n[:, 0], n[:, 2], n[:, 1]], 1).astype('f4')
    a, b, d = gp[t[:, 0]], gp[t[:, 1]], gp[t[:, 2]]
    flip = (np.cross(b-a, d-a)*gn[t[:, 0]]).sum(1) < 0
    t = t.copy()
    t[flip] = t[flip][:, ::-1]
    c8 = np.clip(c*255, 0, 255).astype('u1')
    blobs = [gp.tobytes(), gn.tobytes(), c8.tobytes(), u.astype('f4').tobytes(), t.astype('u4').tobytes()]
    views, off = [], 0
    for b_ in blobs:
        views.append(dict(buffer=0, byteOffset=off, byteLength=len(b_)))
        off += (len(b_)+3) & ~3
    N = len(gp)
    doc = dict(asset=dict(version='2.0'), buffers=[dict(byteLength=off)], bufferViews=views,
               accessors=[dict(bufferView=0, componentType=5126, count=N, type='VEC3', min=gp.min(0).tolist(), max=gp.max(0).tolist()),
                          dict(bufferView=1, componentType=5126, count=N, type='VEC3'),
                          dict(bufferView=2, componentType=5121, normalized=True, count=N, type='VEC4'),
                          dict(bufferView=3, componentType=5126, count=N, type='VEC2'),
                          dict(bufferView=4, componentType=5125, count=len(t)*3, type='SCALAR')],
               materials=[dict(name='M_Sea', doubleSided=True)],
               meshes=[dict(name=path.stem, primitives=[dict(attributes=dict(POSITION=0, NORMAL=1, COLOR_0=2, TEXCOORD_0=3), indices=4, material=0)])],
               nodes=[dict(mesh=0, name=path.stem)], scenes=[dict(nodes=[0])], scene=0)
    js = json.dumps(doc, separators=(',', ':')).encode()
    js += b' '*(-len(js) % 4)
    body_ = b''.join(b_+b'\0'*(-len(b_) % 4) for b_ in blobs)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12+8+len(js)+8+len(body_)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)+js)
        f.write(struct.pack('<II', len(body_), 0x004E4942)+body_)
    return len(t), (p.max(0)-p.min(0)).round(2).tolist()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:]
    total, sizes = 0, {}
    for name, make in SPECIES.items():
        if only and name not in only:
            continue
        tris, size = write_glb(OUT/f'SM_Sea_{name}.glb', make())
        total += tris
        sizes[name] = dict(tris=tris, size=size)
        print(name, tris, size, flush=True)
    if not only:
        (OUT/'manifest_fauna.json').write_text(json.dumps(sizes, indent=1))
    print('MARINE FAUNA DONE', total, 'tris')


if __name__ == '__main__':
    main()
