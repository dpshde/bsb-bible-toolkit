# FF Milo Serif (licensed desktop fonts)

This directory is the workstation drop for **FF Milo Serif** desktop OTFs.

Do **not** download, scrape, convert, or subset an unlicensed copy into this
tree. The travel print target will not fetch fonts and will not fall back to
Source Serif, Lexend, or any other substitute.

## License

- Foundry: FontFont (Monotype)
- Designer: Mike Abbink
- Site: <https://mikeabbink.com/typefaces/milo-serif/>
- Buy: FontFont / MyFonts desktop license
- This workstation: **desktop license, 1 workstation**
- Do not commit the font files

## Place these files here

Minimum (print target will not run without both):

- FF Milo Serif **Text**
- FF Milo Serif **Text Italic**

For heads and the chapter numeral:

- FF Milo Serif Regular
- FF Milo Serif Bold

Accepted filenames (any of these, `.otf` or `.ttf`):

- `MiloSerif-Text.otf`
- `MiloSerif-TextItalic.otf`
- `MiloSerifText-Regular.otf`
- `MiloSerifText-Italic.otf`
- `FFMiloSerif-Text.otf`
- `MiloSerif-Regular.otf`
- `MiloSerif-Bold.otf`

The Typst composer asks for family names `"FF Milo Serif Text"` /
`MiloSerif-Text` and `"FF Milo Serif"` for heads. Compile uses
`--font-path fonts/milo --ignore-system-fonts`.

Until Text + Text Italic are present, `make travel-john` fails with:

> Place licensed desktop OTFs from FontFont/MyFonts here (Text + Text Italic
> minimum; Regular/Bold for heads). Desktop license, 1 workstation.

A separate watermarked metrics compile (`make travel-john-grid-proof`) may
use the OFL stand-in in `fonts/grid-proof/`. That PDF is labeled
`GRID PROOF — NOT FINAL FACE` and is never the loved face.
