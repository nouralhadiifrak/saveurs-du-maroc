"""Build static layers (clean dish, lid cutout, food layers) in image-1 coordinates."""
import cv2, numpy as np, os
D = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(D, '..', '..', 'assets', 'img', 'recipes')
OUT = os.path.join(D, 'layers'); os.makedirs(OUT, exist_ok=True)
NAMES = {1: '1-tajine-viande-pruneaux', 2: '2-tajine-poulet-olives', 3: '3-couscous-legumes', 4: '4-tajine-kefta'}

def load(i): return cv2.imread(f'{IMG}/{NAMES[i]}.jpg').astype(np.float32) / 255.

# ---- canonical geometry (image 1 pixel coords) ----
OUTER = (670, 689, 515, 356)   # dish outer ellipse
LEDGE = (670, 662, 435, 252)   # ring where the lid sits
FLOOR = (670, 695, 355, 205)   # food floor
# floor ellipse of each source photo
SRC_FLOOR = {1: FLOOR, 2: (575, 830, 385, 275), 3: (555, 725, 415, 330), 4: (648, 480, 278, 210)}
# lid bottom edge polylines (everything above = lid)
LID_POLY = {
    1: [(740, 0), (745, 372), (800, 431), (900, 517), (1000, 564), (1100, 597), (1200, 624), (1300, 644), (1400, 644), (1430, 600), (1448, 560), (1448, 0)],
    2: [(610, 0), (612, 390), (640, 425), (700, 478), (800, 542), (900, 592), (1000, 628), (1100, 662), (1200, 690), (1254, 700), (1254, 0)],
    3: [(695, 0), (698, 340), (720, 388), (800, 455), (900, 525), (1000, 585), (1100, 612), (1254, 622), (1254, 0)],
    4: [(705, 0), (708, 225), (730, 265), (800, 315), (900, 355), (1000, 383), (1100, 398), (1160, 380), (1160, 0)],
}

def ell_r(shape, e):
    h, w = shape[:2]; cx, cy, a, b = e
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return np.sqrt(((x - cx) / a) ** 2 + ((y - cy) / b) ** 2)

def poly_mask(shape, pts):
    m = np.zeros(shape[:2], np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    return m

def foodness(img):
    hsv = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    notclay = np.clip((H - 15) / 3, 0, 1)                    # yellow/green food
    notclay = np.maximum(notclay, np.clip((205 - S) / 20, 0, 1))  # low-sat meat, prunes, couscous
    notclay = np.maximum(notclay, (H > 120).astype(np.float32))    # purple prunes
    bright = np.clip((V - 35) / 25, 0, 1)
    f = notclay * bright
    return cv2.GaussianBlur(f, (0, 0), 2)

base_src = load(1)
Hc, Wc = base_src.shape[:2]

# ---- lid cutout from photo 1 ----
lidm = poly_mask(base_src.shape, LID_POLY[1]).astype(np.float32) / 255.
lidm = cv2.GaussianBlur(lidm, (0, 0), 1.2)
V = base_src.max(2)
lid_a = lidm * np.clip((V - 0.07) / 0.1, 0, 1)
lid = np.dstack([base_src, lid_a])
np.save(f'{OUT}/lid.npy', lid.astype(np.float16))

# ---- clean dish: remove lid (mirror symmetric dish), remove food on the walls (inpaint) ----
base = base_src.copy()
# the dish is slightly tilted: reflect across its measured symmetry axis
ax, ay, psi = 669.0, 690.0, np.arctan(15 / 350)
dx, dy = np.sin(psi), np.cos(psi)
R = np.array([[2 * dx * dx - 1, 2 * dx * dy], [2 * dx * dy, 2 * dy * dy - 1]], np.float32)
t = np.array([ax, ay], np.float32) - R @ np.array([ax, ay], np.float32)
M = np.hstack([R, t[:, None]]).astype(np.float32)
mir = cv2.warpAffine(base_src, M, (Wc, Hc), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
hole = cv2.dilate((lidm > 0.01).astype(np.uint8), np.ones((41, 21), np.uint8)).astype(np.float32)
hole = cv2.GaussianBlur(hole, (0, 0), 6)[..., None]
base = base * (1 - hole) + mir * hole
r_out = ell_r(base.shape, OUTER)
r_led = ell_r(base.shape, LEDGE)
r_fl = ell_r(base.shape, FLOOR)
yy = np.mgrid[0:Hc, 0:Wc][0].astype(np.float32)
# remove image-1 food from the walls / back rim.
# Work in ring coordinates (angle x radius between floor, ledge and outer ellipses) and
# fill non-clay pixels along the angle axis, which keeps the radial shading bands of the clay.
from scipy.interpolate import griddata
NPHI, NRHO = 1440, 360
phi = np.linspace(0, 2 * np.pi, NPHI, endpoint=False).astype(np.float32)
rho = np.linspace(0, 2.0, NRHO).astype(np.float32)
def E(e, ph): return e[0] + e[2] * np.cos(ph), e[1] + e[3] * np.sin(ph)
fx, fy = E(FLOOR, phi); lx, ly = E(LEDGE, phi); ox, oy = E(OUTER, phi)
R_ = rho[:, None]
t1 = np.clip(R_, 0, 1); t2 = np.clip(R_ - 1, 0, 1)
px = np.where(R_ <= 1, fx + (lx - fx) * t1, lx + (ox - lx) * t2).astype(np.float32)
py = np.where(R_ <= 1, fy + (ly - fy) * t1, ly + (oy - ly) * t2).astype(np.float32)
P = cv2.remap(base, px, py, cv2.INTER_LINEAR)
hsv = cv2.cvtColor((np.clip(P, 0, 1) * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
Hh, Ss, Vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
clay = ((Hh >= 4) & (Hh <= 14) & (Ss > 200) & (Vv > 110)) | ((Vv > 225) & (Hh <= 16) & (Ss < 205))
clay = cv2.erode(clay.astype(np.uint8), np.ones((3, 9), np.uint8)).astype(np.float32)
Pf = np.zeros_like(P); got = np.zeros(clay.shape, bool)
for sig in (6, 15, 40, 100, 250):
    k = int(sig * 3) * 2 + 1
    pad = k // 2 + 1
    Pw = np.concatenate([P * clay[..., None]] * 3, 1); Cw = np.concatenate([clay] * 3, 1)
    num = cv2.GaussianBlur(Pw, (k, 1), sig, sigmaY=0.01)[:, NPHI:2 * NPHI]
    den = cv2.GaussianBlur(Cw, (k, 1), sig, sigmaY=0.01)[:, NPHI:2 * NPHI]
    ok = (den > 0.2) & ~got
    Pf[ok] = num[ok] / den[ok][:, None]; got |= ok
Pf = cv2.GaussianBlur(Pf, (0, 0), 1.0)
Pout = P * clay[..., None] + Pf * (1 - clay[..., None])
# inverse map: pixel -> (rho, phi) via scattered interpolation
sel = (slice(None, None, 2), slice(None, None, 2))
pts = np.stack([px[sel].ravel(), py[sel].ravel()], 1)
RR, PP = np.meshgrid(rho, phi, indexing='ij')
reg = (r_out < 1.01) & ((r_fl > 0.9) | (yy < 560))
ys_, xs_ = np.nonzero(reg)
ri = griddata(pts, RR[sel].ravel(), (xs_, ys_), method='linear')
cphi = np.stack([np.cos(PP[sel]).ravel(), np.sin(PP[sel]).ravel()], 1)
ci = griddata(pts, cphi, (xs_, ys_), method='linear')
okp = ~np.isnan(ri) & ~np.isnan(ci[:, 0])
mapx = np.full((Hc, Wc), -1, np.float32); mapy = np.full((Hc, Wc), -1, np.float32)
ph_i = (np.arctan2(ci[okp, 1], ci[okp, 0]) % (2 * np.pi)) / (2 * np.pi) * NPHI
mapx[ys_[okp], xs_[okp]] = ph_i; mapy[ys_[okp], xs_[okp]] = ri[okp] / 2.0 * (NRHO - 1)
Pwrap = np.concatenate([Pout, Pout[:, :2]], 1)
Cwrap = np.concatenate([clay, clay[:, :2]], 1)
clean = cv2.remap(Pwrap, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
cl_img = cv2.remap(Cwrap, mapx, mapy, cv2.INTER_LINEAR, borderValue=1)
valid = np.zeros((Hc, Wc), np.float32); valid[ys_[okp], xs_[okp]] = 1
km = (1 - cl_img) * valid
km = cv2.GaussianBlur(np.clip(km * 1.5, 0, 1), (0, 0), 1.5)[..., None]
base = base * (1 - km) + clean * km
base[r_out > 1.03] = 0
b8 = (np.clip(base, 0, 1) * 255).astype(np.uint8)
np.save(f'{OUT}/base.npy', base.astype(np.float16))
cv2.imwrite(f'{OUT}/base.jpg', b8)

# front rim overlay: dish in front of the ledge (hides the bottom of a closed lid and food spill)
front = np.clip((r_led - 1.0) / 0.015, 0, 1) * np.clip((1.03 - r_out) / 0.02, 0, 1) * np.clip((yy - LEDGE[1]) / 6, 0, 1)
np.save(f'{OUT}/front.npy', np.dstack([base_src, front]).astype(np.float16))

# ---- food layers, mapped floor-ellipse -> canonical floor ellipse ----
y, x = np.mgrid[0:Hc, 0:Wc].astype(np.float32)
u = (x - FLOOR[0]) / FLOOR[2]; v = (y - FLOOR[1]) / FLOOR[3]
r = np.sqrt(u * u + v * v)
for i in range(1, 5):
    src = load(i)
    scx, scy, sa, sb = SRC_FLOOR[i]
    mx = (scx + u * sa).astype(np.float32); my = (scy + v * sb).astype(np.float32)
    col = cv2.remap(src, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    occ = cv2.remap(poly_mask(src.shape, LID_POLY[i]), mx, my, cv2.INTER_LINEAR, borderValue=0)
    occ = cv2.dilate(occ, np.ones((7, 7), np.uint8)).astype(np.float32) / 255.
    fd = foodness(col)
    inner = np.clip((1.0 - r) / 0.08, 0, 1)
    # food piled above the floor (mound): keep only food-coloured pixels, never below the floor front
    up = fd * (v < 0.4) * np.clip((1.75 - r) / 0.2, 0, 1)
    a = np.maximum(inner, up) * (1 - occ)
    # fill occluded floor from rotated copies (the dish is round, food is roughly radial)
    need = (inner > 0) & (occ > 0.02)
    for ang in (100, -100, 150, -150):
        if not need.any(): break
        t = np.deg2rad(ang)
        ru = u * np.cos(t) - v * np.sin(t); rv = u * np.sin(t) + v * np.cos(t)
        rx = (FLOOR[0] + ru * FLOOR[2]).astype(np.float32); ry = (FLOOR[1] + rv * FLOOR[3]).astype(np.float32)
        c2 = cv2.remap(col, rx, ry, cv2.INTER_LINEAR); o2 = cv2.remap(occ, rx, ry, cv2.INTER_LINEAR, borderValue=1)
        ok = need & (o2 < 0.02)
        col[ok] = c2[ok]; need &= ~ok
    # soft-blend filled seams
    fill = np.clip(occ * (inner > 0), 0, 1)
    blur = cv2.GaussianBlur(col, (0, 0), 1.5)
    col = col * (1 - 0.5 * fill[..., None]) + blur * 0.5 * fill[..., None]
    a = np.maximum(a, inner * occ)
    layer = np.dstack([col, a])
    np.save(f'{OUT}/food{i}.npy', layer.astype(np.float16))
    prev = (np.clip(col * a[..., None] + base * (1 - a[..., None]), 0, 1) * 255).astype(np.uint8)
    cv2.imwrite(f'{OUT}/food{i}_prev.jpg', prev)
print('ok')
