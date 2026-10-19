# CPN appearance

The header uses the supplied **Crop Protection Network Logo 2022.png** without cropping, recoloring or changing its proportions. The hosted copy is `static/assets/cpn-logo-2022.png`; the standalone build embeds the exact same image. Its SHA-256 is `31d483c6cbe5e9126b3ee7e03739206684735de1b0c999079fdfa2746b3d265f`.

## Colors and layout

These three colors were sampled from solid areas in the supplied logo. They are not a separately verified brand-manual specification.

| Color | Hex | Use |
| --- | --- | --- |
| Dark green | `#0B6623` | Title background, section headings, links and primary buttons |
| Lime | `#A7C339` | Title divider and comparison controls |
| Yellow | `#FEDA2F` | Small title label |
| Light neutral | `#F7F8F4` | Page background, selected for this interface |
| White | `#FFFFFF` | Logo header, product cards and information panels |

The page uses a full-width green title area, white logo header, lighter content background, consistent sans-serif headings, and responsive spacing. The original logo's transparency and dimensions are preserved. At narrow phone widths the logo and database label stack vertically.

## Typography

**Roboto Condensed** is bundled for headings, with Arial for body text. This is a visual approximation of the supplied logo's condensed lettering. CPN's exact website font could not be verified through the accessible public pages, and no brand font specification was supplied.

The heading and body stacks are controlled by `--font-heading` and `--font-body` at the top of `static/index.html`. A CPN developer can replace these with approved typefaces and update the `@font-face` declaration and standalone asset list in `build_preview.py` as needed.

The original variable font is from [Google Fonts' Roboto Condensed directory](https://github.com/google/fonts/tree/main/ofl/robotocondensed), source blob `221055572bc92e324d26337dee7b43b435e39fc8`. It is distributed under the SIL Open Font License in `static/assets/RobotoCondensed-OFL.txt`. No remote font request is needed. The standalone HTML embeds the logo, font and license along with the EPA catalog.

CPN reference pages reviewed: [What's on Your Seed?](https://cropprotectionnetwork.org/whats-on-your-seed-tool), [Media Kit](https://cropprotectionnetwork.org/media-kit), and [Visuals](https://cropprotectionnetwork.org/visuals). Their accessible text did not expose a definitive font specification.
