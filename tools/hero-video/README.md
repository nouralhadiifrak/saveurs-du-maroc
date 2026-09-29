# Hero video generator

Builds `assets/video/hero-tajine-loop.mp4` from the four recipe photos in
`assets/img/recipes/`: the tajine from photo 1 turns slowly, the lid closes,
the next recipe is revealed, and after the 4th recipe the 1st comes back so the
video loops seamlessly (32 s, 1920x1080, 30 fps).

```bash
pip install opencv-python-headless numpy scipy imageio-ffmpeg
python3 prep.py                 # cut out the lid, clean the dish, build the food layers
python3 render.py ../../assets/video/hero-tajine-loop.mp4
python3 render.py preview.jpg 0 5.2 6.2   # optional: preview single frames (seconds)
```

Timing (`SEG`, `OMEGA`), recipe order (`ORDER`) and framing are constants at
the top of `render.py`.
