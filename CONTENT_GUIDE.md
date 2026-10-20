# Content guide

How to add, change or remove stickers and memes in this repository, and how those changes reach the Sticker Maker app.

## How the app reads this repo

1. On start-up and on pull-to-refresh the app downloads `v1/index.json`, from `raw.githubusercontent.com`, with `github.com/<repo>/raw/main/` as a fallback host.
2. The index lists every manifest with a SHA-256 prefix. The app downloads only the manifests whose hash changed, validates them, and only then switches to the new library. If anything is invalid, it keeps its last good copy.
3. Images are loaded lazily: list screens use the small files in `media/thumbs/` and `media/meme-thumbs/`, and full-size files are fetched only when a sticker or meme is opened, shared, saved or added to WhatsApp. Media comes from the same two GitHub hosts (the list is `mediaBaseUrls` in the index, so a CDN can be added later without an app update).
4. The APK ships a small starter snapshot (manifests plus a few packs) so the app works offline on first launch.

Nothing is pushed to phones. A change becomes visible the next time the app checks the index:
- GitHub raw caches files for about 5 minutes, so a new commit is usually visible within 5–10 minutes.
- jsDelivr is **not** used: it refuses GitHub repositories larger than 50 MB, and this one is bigger.

## Layout

```
v1/                      generated manifests (never edit by hand)
  index.json             entry point: version, mirrors, manifest list with sha + size, counts, credits
  categories.json        sticker and meme categories (only non-empty ones are published)
  packs.json             pack summaries (tray, cover, 4 preview thumbs, count, sha of the pack manifest)
  packs/<id>.json        one pack: every sticker with file, thumb, emojis, tags, credit
  memes/index.json       meme feeds: per category and "all", 24 memes per page
  memes/<feed>/<n>.json  one page of memes
  trending.json          curated sections + "recently added" sections
  search.json            search index (categories, packs, stickers, memes)
  credits.json           libraries and every photo author/licence
media/
  stickers/<pack>/NN.webp    512x512 WebP (static <= 100 KB, animated <= 500 KB, <= 10 s)
  thumbs/<pack>/NN.webp      160 px thumbnails for grids
  gifs/<pack>/NN.gif         240 px GIF copies of animated stickers, for sharing to apps without WebP animation
  trays/<pack>.png           96x96 PNG tray icon (<= 50 KB)
  covers/<pack>.webp         720x400 pack cover collage
  memes/<category>/<id>.webp     full meme (max 1080 px wide, <= 300 KB)
  meme-thumbs/<category>/<id>.webp   360 px thumbnail
build/                   per-pack and per-meme metadata written by the build tools (input to make_manifests.py)
curation/                editorial files: trending.json, premium.json, added.json (first-published dates)
tools/                   build, manifest and validation scripts
```

## Adding a sticker pack

1. Add a spec line to `tools/spec_stickers.py`:
   - `EMOJI_PACKS`: emoji-based packs;
   - `TEXT_PACKS`: lettering;
   - `ANIMATED_PACKS`: Noto animated emoji;
   - `LEGACY_PACKS`: your own artwork, with files in the work folder.

   Every pack needs a category id that exists in `CATEGORIES`.
2. Render it with `python tools/build_stickers.py <work-dir> <pack-id>`. The work dir holds the source art and fonts, which are not stored in this repo: Fluent Emoji PNGs, Noto animated WebP cache and OFL fonts. The build script prints where it expects them.
3. Look at the result: `media/covers/<pack-id>.webp` is a collage of the whole pack.
4. Run `python tools/make_manifests.py` and then `python tools/validate.py`.
5. Commit `build/`, `media/`, `v1/` and `curation/added.json` together and open a pull request. CI runs the same validation.

To add your **own artwork** instead, drop 512x512 PNG/WebP files into the work folder and add an entry to `build_legacy()`. Use credit key `own`.

## Adding memes

1. Find a photo with a licence on the allow-list (see [LICENSES.md](LICENSES.md)), or use emoji art. Record it in the photo sources file with title, page URL, author, licence and licence URL. `scripts/commons_html.py` does this for Wikimedia Commons "Quality images" categories.
2. Add an item to `tools/spec_memes.py`:
   - `cap(...)`: caption above the photo;
   - `classic(...)`: top/bottom text;
   - `cmp(...)`: two photos side by side;
   - `post(...)`: text card with an emoji reaction;
   - `ecmp(...)`: two emoji panels.

   Use `lang="en"`, `"ur-Latn"` (Roman Urdu) or `"ur"` (Urdu script).
3. Run `python tools/build_memes.py`, look at the images in `media/memes/`, then run `make_manifests.py` and `validate.py`.

Caption rules:
- Write original captions.
- No real people's photos or names.
- No film or TV stills.
- No copyrighted characters or logos.
- Nothing hateful, sexual or targeting a group.
- Jokes about everyday life (family, school, office, food, weather, cricket) are the house style.

## Editing Trending

`curation/trending.json` is edited by hand. Each section has an `id`, a `title`, a `subtitle`, a `basis` and `items`:
- `basis` says honestly why these items are here, for example "Seasonal pick for Diwali (8 Nov)".
- `items` are references like `"pack:good-morning"` or `"meme:cats-1a2b3c4d"`.

Unknown references stop the manifest build. Update `updatedAt` when you change it.

Trending is **curated**, not measured. The app does not collect usage statistics, so no section may claim popularity, download counts or ratings. The app labels the section "Curated by Sticker Maker editors" and shows the date.

## Removing content

Delete the spec line, delete the files under `media/` and the JSON under `build/`, then re-run `make_manifests.py`. Validation warns about orphan media files. Users who already added a pack to WhatsApp keep their copy.

## Versioning

- `contentVersion` (e.g. `2026.10.20-1`) changes on every manifest build. The app drops cached meme pages and the search index when it changes.
- `schema` is the manifest format version. A breaking format change must go to `v2/` with `schema: 2`, so older apps keep reading `v1/`.
- `minAppVersionCode` makes older apps show an "update the app" banner when new content needs a newer app.

## Size limits

- No single file over 20 MB; validation enforces this.
- Keep each push under about 500 MB so GitHub accepts it. Large imports should be split over several commits.
- GitHub raw is fine for this app's traffic. For much larger audiences, enable GitHub Pages (Settings → Pages → main / root) and add `https://codecoiltechnologies.github.io/sticker-maker-content/` as the first entry of `mediaBaseUrls` in `tools/make_manifests.py`.
