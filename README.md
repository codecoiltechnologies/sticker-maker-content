# Sticker Maker content

Public content library for the **Sticker Maker – Create. Explore. Share** Android app by CodeCoil Technologies: WhatsApp sticker packs, animated stickers and memes, with manifests the app reads at runtime.

| | |
|---|---|
| Sticker packs | 65 (10 animated) |
| Stickers | 1593 (287 animated) |
| Memes | 333 in 18 categories (English, Roman Urdu, Urdu) |
| Categories | 41 |
| Content version | `2026.10.20-2` |

Entry point for the app: [`v1/index.json`](v1/index.json)
- GitHub raw: https://raw.githubusercontent.com/codecoiltechnologies/sticker-maker-content/main/v1/index.json
- Fallback host: https://github.com/codecoiltechnologies/sticker-maker-content/raw/main/v1/index.json

## What's inside

**Sticker categories:**
Emoji Faces (2), Animated & GIFs (10), Love & Romance (3), Friends & BFF (1), Sad & Heartbreak (2), Funny (3), Reactions (4), Cute Animals (5), Cartoon & Chibi (4), Gaming (2), Birthday & Party (3), Good Morning & Night (2), Islamic Greetings (3), Urdu & Roman Urdu (2), Desi Vibes (1), Savage & Attitude (1), Festivals & Seasons (2), Text Stickers (1), Food & Chai (4), Sports & Cricket (2), Office & Study (4), Filmy Dialogues (1), Nature & Travel (3)

**Meme categories:**
Funny Memes (15), Desi Memes (16), Urdu Memes (15), Cat Memes (30), Dog Memes (25), Animal Memes (28), Relatable & Mood (28), Students & Exams (21), Work & Office (19), Gaming Memes (15), Food & Chai Memes (20), Family Memes (15), Cricket Memes (13), Love & Single Life (14), Savage & Sarcastic (12), Filmy Memes (11), Wholesome & Motivational (17), Seasonal Memes (19)

Every sticker is a 512×512 WebP that passes WhatsApp's limits:
- static stickers 100 KB or less; animated stickers 500 KB or less and 10 s or shorter;
- 96×96 tray icons;
- 3–30 stickers per pack.

Every item has an id, title, category, tags, language, file type, thumbnail, file path and credit. URLs are `mediaBaseUrls[i] + path`.

**Trending** (`v1/trending.json`) is curated by hand. Its sections say why they were picked (for example seasonal festivals) and when. There are also "recently added" sections sorted by publish date. No popularity or usage numbers are claimed, because none are collected.

## Repository layout

See [CONTENT_GUIDE.md](CONTENT_GUIDE.md) for the full layout, how to add packs and memes, and how updates reach the app.

```
v1/          generated manifests (index, categories, packs, memes pages, trending, search, credits)
media/       stickers, thumbs, GIFs, trays, covers, memes, meme thumbs
build/       per-item metadata produced by the build scripts
curation/    trending.json (editorial), premium.json, added.json (first-published dates)
tools/       build_stickers.py, build_memes.py, make_manifests.py, validate.py, bundle_starter.py
```

## Publishing an update

```bash
python tools/build_stickers.py <work-dir> <pack-id>   # or build_memes.py
python tools/make_manifests.py --version 2026.10.20-2
python tools/validate.py
git add -A && git commit -m "Add …" && git push      # via pull request
```

The **Validate content** GitHub Actions workflow re-checks every push and pull request:
- the manifests are fresh;
- every referenced file exists and is safe;
- WhatsApp limits are met;
- only allowed licences are used;
- there are no duplicates or secrets.

After a push to `main` it confirms that both GitHub hosts the app uses serve the new index.

Publishing itself is a manual step: someone runs the tools and merges the pull request. No scheduled job adds content by itself. [AI_CURATION.md](AI_CURATION.md) describes how to use an AI assistant for curation runs.

## Licences

See [LICENSES.md](LICENSES.md). In short:
- Fluent Emoji is MIT (Microsoft).
- Noto Animated Emoji is CC BY 4.0 (Google).
- Photos come from Wikimedia Commons under CC0 / CC BY / CC BY-SA, each credited in its meme's metadata and in `v1/credits.json`.
- Captions and lettering are original (CC BY 4.0, CodeCoil).
- The Sticker Maker character art is © CodeCoil.

This repository contains no credentials, signing keys or tokens.
