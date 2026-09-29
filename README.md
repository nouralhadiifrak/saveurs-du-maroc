# Saveurs du Maroc

Website of **Saveurs du Maroc**, a traditional Moroccan restaurant at
13 rue de la République, 30900 Nîmes. It's open every day from 07:00 to 00:00.

It's a static site, a single `index.html` with no build step. Open it in a
browser, or put the folder on any static host (GitHub Pages, Netlify, OVH…).

## Features

- Hero with the looping tajine video (`assets/video/`), blended into an animated red/green background.
- Signature dishes, then the full menu with category filters, prices, and the Kids and Student set menus.
- Reservation form that opens WhatsApp (+33 7 54 09 65 67) with a pre-filled message (name, date, time, guests, note).
- Floating WhatsApp button.
- Customer reviews section with Google reviews and Instagram buttons.
- Live "open / closed" badge in Paris time. Opening hours, address and a Google Map.
- French / English switch and light / dark mode. Both choices are remembered in the browser.
- Scroll animations. They are turned off automatically when the visitor asks the system for reduced motion.
- Self-hosted fonts in `assets/fonts/`: Cinzel, Great Vibes, Amiri, Aref Ruqaa and Reem Kufi. No Google Fonts request is made.

## Editing

- **Menu and prices**: the `MENU`, `DISHES` and `FORMULAS` arrays in the `<script>` at the bottom of `index.html`.
- **Texts (FR/EN)**: the `T` object in the same script.
- **WhatsApp number**: `var WA = '33754096567'`, plus the displayed number in the HTML.
- **Instagram, Google rating and reviews**: `INSTAGRAM`, `RATING` and `REVIEWS` at the top of the same script.
- **Colors**: the CSS variables at the top of the `<style>` block (`--red`, `--green`, `--gold`…).

## Assets

- `assets/img/logo.webp` / `logo-full.png`: the logo without the dishes and without "Restauration rapide". Made with `tools/logo-cleanup.py`.
- `assets/video/hero-tajine-loop.{webm,mp4}`: the hero loop. See `tools/hero-video/README.md` to regenerate it.
- `assets/img/recipes/`: the dish photos.
