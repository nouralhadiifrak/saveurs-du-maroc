"""Render the seamless tajine hero loop. Scene is authored in photo-1 pixel coordinates."""
import cv2, numpy as np, os, sys, subprocess, imageio_ffmpeg
D = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(D, 'layers')

W, H = int(os.environ.get('W', 1920)), int(os.environ.get('H', 1080))
FPS = 30
SEG = 8.0                       # seconds per recipe
ORDER = [1, 2, 3, 4]
TOTAL = SEG * len(ORDER)
OMEGA = np.deg2rad(7.0)         # turntable speed (rad/s)
# scene -> output: X = (x - x0) * S
CX_SCENE, CY_SCENE, SPAN_Y = 670.0, 454.0, 1440.0
S = H / SPAN_Y
x0 = CX_SCENE - (W / S) / 2; y0 = CY_SCENE - (H / S) / 2

FLOOR = (670, 695, 355, 205)
LID_A0 = np.array([1086.0, 493.0]); LID_TAU = np.deg2rad(19.0)
LID_WH, LID_H = 357.0, 511.0
LID_C = np.array([670.0, 668.0]); LID_SC = 1.28; LID_B = 262.0
LIFT = 150.0
FLANGE = (0.05, 0.29, 0.70)  # BGR of the glazed clay

f16 = lambda n: np.load(f'{L}/{n}.npy').astype(np.float32)
base, lid, front = f16('base'), f16('lid'), f16('front')
foods = {i: f16(f'food{i}') for i in ORDER}

Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
SX = X / S + x0; SY = Y / S + y0             # scene coords of every output pixel
remap = lambda img, mx, my: cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
base_o = remap(base, SX, SY)
front_o = remap(front, SX, SY)
foods_o = {i: remap(f, SX, SY) for i, f in foods.items()}
# floor ellipse in output coords (food turntable)
fcx, fcy = (FLOOR[0] - x0) * S, (FLOOR[1] - y0) * S
fa, fb = FLOOR[2] * S, FLOOR[3] * S
U = (X - fcx) / fa; V = (Y - fcy) / fb
LEDGE = (670, 662, 470, 275)
LEDGE_IN = np.clip((1 - np.sqrt(((SX - LEDGE[0]) / LEDGE[2]) ** 2 + ((SY - LEDGE[1]) / LEDGE[3]) ** 2)) / 0.03, 0, 1)[..., None]

def ease(p): p = np.clip(p, 0, 1); return p * p * (3 - 2 * p) if p < 1 else 1.0
def ease2(p): p = np.clip(p, 0, 1); return 0.5 - 0.5 * np.cos(np.pi * p)

def state(t):
    k = int(t // SEG) % len(ORDER); tl = t - (t // SEG) * SEG
    if tl < 4.4: p = 0.0
    elif tl < 6.0: p = ease2((tl - 4.4) / 1.6)
    elif tl < 6.4: p = 1.0
    else: p = ease2(1 - (tl - 6.4) / 1.6)
    j = k if tl < 6.2 else (k + 1) % len(ORDER)
    center = SEG * j + 2.2
    dt = ((t - center + TOTAL / 2) % TOTAL) - TOTAL / 2
    return ORDER[j], p, OMEGA * dt

def lid_layer(p):
    e = p
    anchor = LID_A0 * (1 - e) + LID_C * e + np.array([0, -LIFT * np.sin(np.pi * e) ** 1.2])
    tau = LID_TAU * (1 - e)
    s = 1 + (LID_SC - 1) * e
    w = e ** 1.6
    bw = w * LID_B / LID_SC
    ct, st = np.cos(tau), np.sin(tau)
    dx, dy = (SX - anchor[0]) / s, (SY - anchor[1]) / s
    lx = dx * ct + dy * st; lyd = -dx * st + dy * ct
    c = bw * np.sqrt(np.clip(1 - (lx / (LID_WH * 1.02)) ** 2, 0, 1))
    ly = (lyd - c) / (1 + c / LID_H)
    ct0, st0 = np.cos(LID_TAU), np.sin(LID_TAU)
    px = LID_A0[0] + lx * ct0 - ly * st0; py = LID_A0[1] + lx * st0 + ly * ct0
    cone = remap(lid, px.astype(np.float32), py.astype(np.float32))
    if bw < 1: return cone
    # flat flange of the lid base (visible behind the cone once the lid is seen from above)
    rr = np.sqrt((lx / (LID_WH * 1.0)) ** 2 + (lyd / bw) ** 2)
    fa_ = np.clip((1 - rr) * bw * s * S / 1.2, 0, 1) * np.clip((e - 0.6) / 0.3, 0, 1)
    shade = 0.62 + 0.45 * np.clip(rr, 0, 1) ** 4 + 0.18 * np.clip((rr - 0.93) / 0.05, 0, 1) * np.clip((1.0 - rr) / 0.02, 0, 1)
    fl = np.dstack([FLANGE[0] * shade, FLANGE[1] * shade, FLANGE[2] * shade, fa_]).astype(np.float32)
    return _merge(cone, fl)

def _merge(top, bot):
    ta, ba = top[..., 3:4], bot[..., 3:4]
    oa = ta + ba * (1 - ta)
    oc = (top[..., :3] * ta + bot[..., :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.concatenate([oc, oa], 2)

def over(dst, src):
    a = src[..., 3:4]; return dst * (1 - a) + src[..., :3] * a

def frame(t):
    rec, p, ang = state(t)
    ca, sa = np.cos(-ang), np.sin(-ang)
    mx = (fcx + (U * ca - V * sa) * fa).astype(np.float32)
    my = (fcy + (U * sa + V * ca) * fb).astype(np.float32)
    fl = remap(foods_o[rec], mx, my)
    if p > 0.9:  # fully seated lid: nothing of the food can show at the sides
        fl[..., 3:4] *= 1 - LEDGE_IN * min(1.0, (p - 0.9) / 0.08)
    img = over(base_o, fl)
    img = over(img, lid_layer(p))
    img = over(img, front_o)
    return img

if __name__ == '__main__':
    out = sys.argv[1]
    if out.endswith('.jpg'):
        for tt in sys.argv[2:]:
            cv2.imwrite(out.replace('.jpg', f'_{tt}.jpg'), (np.clip(frame(float(tt)), 0, 1) * 255).astype(np.uint8))
        sys.exit()
    n = int(round(TOTAL * FPS))
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for fi in range(n):
        pr.stdin.write((np.clip(frame(fi / FPS), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if fi % 60 == 0: print(fi, n, flush=True)
    pr.stdin.close(); pr.wait()
