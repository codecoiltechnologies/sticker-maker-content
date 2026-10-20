# Curating content with an AI assistant

The library was built with help from an AI assistant (Claude). This file describes the process so a person — or another assistant session — can repeat it safely. **Nothing here runs automatically.** Each update is a deliberate run of the tools followed by a reviewed pull request.

## Ground rules for any assistant session

1. **Licences first.**
   - Only use sources on the allow-list in [LICENSES.md](LICENSES.md), and read the licence from the file's own page rather than from a search result.
   - Record author, licence, licence URL and source page for every photo.
   - If the licence is unclear, skip the file.
2. **No scraping of meme sites, social media or image search.** No celebrities, private people, film stills, logos or copyrighted characters.
3. **Original captions only.**
   - Keep them light, inclusive and family-friendly.
   - No hate, no sexual content.
   - No jokes that target religion, ethnicity, gender or a nationality.
   - Religious greetings (Islamic, Eid, Diwali, Christmas) must be respectful and spelled correctly.
4. **Honest labels.**
   - Trending is curated.
   - Never invent download counts, ratings, "most popular" claims or usage statistics.
   - Seasonal sections state their reason in `basis`.
5. **Look at the output.** Open the pack cover collages (`media/covers/`) and a contact sheet of new memes before publishing, and check Urdu text renders right-to-left with joined letters.
6. **Validate and review.**
   - `python tools/make_manifests.py && python tools/validate.py` must pass.
   - Open a pull request; a person merges it.
7. **No secrets.** This repository is public. Never commit keystores, tokens, `.env` files or API keys; validation fails if it sees them.

## Suggested update routine (monthly, or before a festival)

1. Pick themes: upcoming festivals (Ramadan, Eid, Independence Day 14 Aug, Diwali, Christmas, New Year), the cricket calendar, the season.
2. Text packs: add lines to `TEXT_PACKS` in `tools/spec_stickers.py`, then render with `build_stickers.py <work> <pack-id>`.
3. Memes:
   - collect new openly licensed photos with `scripts/commons_html.py` (2.5 s between requests, descriptive User-Agent);
   - write 20–50 captions in `tools/spec_memes.py`;
   - build with `build_memes.py`.
4. Update `curation/trending.json`: replace the seasonal section and set `updatedAt`.
5. Build manifests, validate, review contact sheets, open a pull request.
6. After merge, check the **Validate content** workflow run, then confirm `v1/index.json` shows the new `contentVersion` on both mirrors:
   - https://raw.githubusercontent.com/codecoiltechnologies/sticker-maker-content/main/v1/index.json
   - https://cdn.jsdelivr.net/gh/codecoiltechnologies/sticker-maker-content@main/v1/index.json

## Prompt template

> You are curating content for the public repo codecoiltechnologies/sticker-maker-content. Read CONTENT_GUIDE.md, LICENSES.md and AI_CURATION.md first and follow them exactly. Task: add a seasonal section and about 30 new memes for <festival/theme>. Use only allow-listed licences, record every credit, write original captions in English and Roman Urdu, render, run make_manifests.py and validate.py, show me a contact sheet, and open a pull request. Do not merge, and do not claim anything is trending by popularity.
