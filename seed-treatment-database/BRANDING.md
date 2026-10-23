# CPN appearance

The approved October 21, 2026 layout uses a compact Crop Protection Network header, a white background, green headings and links, and thin neutral dividers. The supplied logo is preserved without cropping, recoloring, or changing its proportions.

## Page structure

The introduction explains the tool's purpose and audience. Catalog dates come from the loaded data. An expandable About section contains the workflow, scope, update explanation, and suggested citation; its dates update with the catalog. Final CPN authorship and any publication identifier still require editorial confirmation.

Three primary views organize the application: Products, Compare, and Guides & sources. The latter includes the abbreviation guide, ingredient search, treatment/resistance guidance, EPA signal words and treatment warnings, handling practices, references, and the full source/coverage information.

Search, crop selection, and treatment purpose are visible first. More filters retains every advanced control, including technology. Download & print groups the full exports. Product rows use plain text for facts and underlined controls for ingredient details, full product details, and label access. Selection uses a checkbox; neither category color nor order indicates safety or efficacy.

The complete comparison matrix, reviewed label extracts, evidence distinctions, full-registration label guards, source updates, and CSV fields are unchanged. Native disclosures, keyboard tab navigation, focus restoration, 320px reflow, reduced motion, and forced-colors styles are retained.

## Seed photograph

`static/assets/adam-sisson-treated-corn.jpg` is a web-sized copy of the user-supplied treated-corn photograph. Its visible credit is **Photo: Adam Sisson, Iowa State University.** The descriptive alternative text identifies red and purple coatings on treated corn kernels. The photograph is not used as evidence for any individual product.

The JPEG is 900 × 600 pixels, resized and compressed from the supplied image without generating or replacing its content. The original supplied photograph was not modified. `build_preview.py` embeds the JPEG in the standalone file along with the CPN logo and fact-sheet PDF.

The earlier botanical illustration is no longer displayed. It remains in the repository as a historical asset. The interface uses no emoji or decorative icon controls.

## Typography and colors

The interface uses Arial/Helvetica/system sans-serif, without a downloadable font. Green `#155C32` identifies links and headings; `#104526` supplies darker interactive states. Text uses `#24332A`, secondary text `#58615A`, and dividers `#D9DFDA`. These are implementation choices consistent with the approved mockup, not a separately verified CPN brand manual.

The unused Roboto Condensed file and its license remain available for historical compatibility. They are no longer loaded or embedded. The logo remains `static/assets/cpn-logo-2022.png` with SHA-256 `31d483c6cbe5e9126b3ee7e03739206684735de1b0c999079fdfa2746b3d265f`.

CPN references informing the streamlined presentation: [ROI calculators](https://cropprotectionnetwork.org/roi-calculators), [Fungicide Efficacy Tool](https://cropprotectionnetwork.org/fungicide-efficacy-tool), and [Yield Loss Calculator](https://cropprotectionnetwork.org/yield-loss-calculator).

## Reverting the presentation

The checkpoint branch `checkpoint/seed-tool-before-streamlining-2026-10-21` preserves the preceding version at `a17ee78aa732e733c121ac529b86c1521e3ba824`. Revert the presentation commit while retaining newer catalog commits. Rebuild both standalone previews against the current catalog after a revert; do not reset the whole branch to the checkpoint and discard subsequent source updates. CPN deployment, if configured separately, must publish the reverted files too.
