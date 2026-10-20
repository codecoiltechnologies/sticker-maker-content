# Licences and attribution

Every published item carries a `credit` in its manifest entry, and the app shows it on the viewer and in **Settings → Content library → Credits**. This file explains the sources.

## Allowed licences

Only these licences are accepted. `tools/validate.py` rejects anything else:

| Licence | Typical source |
|---|---|
| MIT | Microsoft Fluent Emoji |
| CC BY 4.0 | Google Noto Animated Emoji; original CodeCoil captions and lettering |
| CC0 / Public domain | Wikimedia Commons photos |
| CC BY 2.0 / 2.5 / 3.0 / 4.0 | Wikimedia Commons photos (author credited) |
| CC BY-SA 2.0 / 2.5 / 3.0 / 4.0 | Wikimedia Commons photos (author credited; the modified meme image is shared under the same licence) |
| All rights reserved (CodeCoil) | Sticker Maker's own character artwork |

NonCommercial (NC) and NoDerivatives (ND) licences are never used. Memes are modified works (cropped, captioned) and the app may be monetised.

## Sources

- **Fluent Emoji 3D**: © Microsoft Corporation, MIT licence. https://github.com/microsoft/fluentui-emoji. The static emoji stickers and the emoji in text stickers and text-post memes are rendered from these images.
- **Noto Animated Emoji**: © Google, CC BY 4.0. https://googlefonts.github.io/noto-emoji-animation/. Animated stickers are re-encoded to 512x512 animated WebP (frame rate reduced to meet WhatsApp's 500 KB limit).
- **Wikimedia Commons photos**: taken from the "Quality images" categories, one file at a time, with the licence read from each file page. Each meme records the author, licence, licence URL and the Commons page in `credit`. Photos were cropped, resized and captioned.
- **Fonts** (used to draw lettering; not redistributed as font files): Lilita One, Fredoka, Pacifico, Anton, Bangers, Baloo Bhaijaan 2, Lobster, Permanent Marker, Poppins, Oswald, Inter, Lalezar (SIL Open Font License 1.1); Gulzar, Noto Nastaliq Urdu, Noto Naskh Arabic, Amiri (SIL OFL 1.1).
- **Sticker Maker artwork**: the chibi characters (Cute Boy, Chibi Friends) and the "Sticker Maker Originals" pack come from the app's own design files. © CodeCoil Technologies, all rights reserved; they are only licensed for use inside the Sticker Maker app.
- **Captions and lettering**: written for this project by CodeCoil, released under CC BY 4.0.

## Not used

- Images scraped from meme sites, social networks or search engines.
- Film or TV stills, photos of celebrities or private people, copyrighted characters, brand logos.
- Well-known meme templates whose original photo is not under an open licence.

## Takedown

If you believe something here infringes your rights, open an issue in this repository or email the address on the app's Play Store page. Include the file path and we will remove it promptly.
