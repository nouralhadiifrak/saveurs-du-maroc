import cv2, numpy as np
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
im = cv2.imread('logo-original.jpg').astype(np.float32)
H, W = im.shape[:2]
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
OC, OR = (623.5, 557.5), 494.0      # outer ring (centre, radius of the stroke centre)
IC, IR = (622.0, 554.0), 371.0      # inner ring
ro = np.hypot(x - OC[0], y - OC[1]); ri = np.hypot(x - IC[0], y - IC[1])
hsv = cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_BGR2HSV)
ring = (np.abs(ro - OR) < 3) & (y > 400) & (y < 700) & (hsv[..., 2] > 110)
GOLD = im[ring].mean(0); print('gold', GOLD)
BG = np.array([11, 11, 11], np.float32)
out = im.copy()
# fade the green lattice panels out towards the bottom
band = (ri > IR + 3) & (ro < OR - 5)
f = np.clip((y - 640) / 120, 0, 1)[..., None] * band[..., None]
out = out * (1 - f) + BG * f
# erase food, the tajine lid, steam and the "RESTAURATION RAPIDE" line
kill = np.zeros((H, W), bool)
kill |= y >= 768
kill |= (x > 420) & (x < 866) & (y > 674) & (y < 726)   # tagline
kill |= (x > 318) & (x < 472) & (y > 672)               # tajine lid knob
kill |= (x < 300) & (y > 725) | (x > 960) & (y > 725)   # steam / food edges near the ring
km = cv2.GaussianBlur(kill.astype(np.float32), (0, 0), 2)[..., None]
out = out * (1 - km) + BG * km
# redraw the lower halves of both rings (4x supersampled for smooth edges)
SS = 4
lay = np.zeros((H * SS, W * SS), np.uint8)
cv2.circle(lay, (int(OC[0] * SS), int(OC[1] * SS)), int(OR * SS), 255, 8 * SS, cv2.LINE_AA)
cv2.circle(lay, (int(IC[0] * SS), int(IC[1] * SS)), int(IR * SS), 255, 4 * SS, cv2.LINE_AA)
lay = cv2.resize(lay, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
lay *= np.clip((y - 690) / 40, 0, 1)            # only where the original ring was hidden
shade = 0.85 + 0.25 * np.clip((x - 300) / 700, 0, 1)
col = GOLD[None, None, :] * shade[..., None]
out = out * (1 - lay[..., None]) + col * lay[..., None]
# transparent outside the emblem, then crop
alpha = np.clip((OR + 6 - ro) / 1.5, 0, 1)
rgba = np.dstack([np.clip(out, 0, 255), alpha * 255]).astype(np.uint8)
x0, y0 = int(OC[0] - OR - 8), int(OC[1] - OR - 8); s = int(2 * OR + 16)
rgba = rgba[y0:y0 + s, x0:x0 + s]
cv2.imwrite('../assets/img/logo-full.png', rgba)

