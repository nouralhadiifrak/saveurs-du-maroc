# saveurs-du-maroc

## Hero video

`assets/video/hero-tajine-loop.{webm,mp4}` is a seamless 32 s loop (1920x1080,
black background) of the tajine turning, closing and reopening on each of the
four recipes. Use it as a muted, autoplaying background:

```html
<section class="hero">
  <video class="hero__video" autoplay muted loop playsinline
         poster="assets/video/hero-tajine-poster.jpg">
    <source src="assets/video/hero-tajine-loop.webm" type="video/webm">
    <source src="assets/video/hero-tajine-loop.mp4" type="video/mp4">
  </video>
</section>
```

```css
.hero { position: relative; height: 100vh; background: #000; overflow: hidden; }
.hero__video { width: 100%; height: 100%; object-fit: cover; }
```

To regenerate it, see `tools/hero-video/README.md`.
