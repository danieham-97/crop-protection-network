# Treatment guide, resistance groups and EPA hazard fields

The **Treatment guide** tab and the three-page PDF compare fungicides, insecticides, nematicides, biological biopesticides and inoculants. Biological origin overlaps with functional treatment types. PIPs and fumigants can occur in the EPA site census but are not presented as conventional seed coatings.

The interface adds separate FRAC and IRAC filters, EPA signal-word and restricted-use filters, product hazard panels, comparison rows and CSV fields. The printable reference is `static/assets/CPN_Seed_Treatment_Comparison.pdf`; the standalone HTML embeds it for offline download.

## Evidence and limits

- **70 reviewed ingredient-name entries**, including synonyms and illustrative reference ingredients, cover **68 of the 187 distinct EPA ingredient codes** in this snapshot. Sources are the **FRAC Code List 2026** and **IRAC MoA v11.5 (February 2026)**, reviewed October 19, 2026. Names are matched exactly after case/whitespace normalization. No group is inferred from a product category, genus or brand name. Unmapped biological strains, PIPs and other ingredients remain unclassified.
- Codes describe resistance-management groups, not efficacy, safety, crop authorization or the number of effective components against a pest. FRAC and IRAC are different systems. A reference ingredient's presence does not establish its registered use in every crop.
- **Signal words** come exclusively from each registration's `SIGNAL_WORD` field. The supplied workbook reports 594 CAUTION, 41 WARNING, 33 DANGER and 25 explicit `None` values. The 187 blank distributor fields remain missing. No signal word is copied from the base registration, ingredient data, SDS or a similarly named product.
- **Restricted-use flags** preserve `RUP_FLAG` and `RUP_REASON`: 19 Yes and 861 No in this workbook. A No flag does not override label restrictions or establish safety. Unknown future values are retained as unknown.
- **628 label-file links** use only exact-registration filenames found in `LABEL_NAMES`, with valid dates at or before the import cutoff. No distributor links or inferred base labels are substituted. They are the latest matching files listed in the supplied workbook, not independently reviewed current labels.
- Product-specific PPE, first aid, environmental hazards and all use restrictions have **not** been extracted or verified across the 880 labels. The interface gives general warnings and BMPs, source provenance and available label links. It directs users to the current label/seed tag for those requirements. No POISON or skull-and-crossbones status is inferred from DANGER.

The EPA source workbook was created September 21, 2026 and imported October 19. Its metadata is not proof of current EPA website parity. The 2026 classification references have their own review date.

## Updating

`refresh_epa.py` imports signal words, restricted-use flags/reasons and label filenames during each successful full-workbook refresh. The GitHub source workflow runs weekly; the alternative host schedule must still be installed on CPN hosting. It preserves the previous catalog after a failed source check. Optional older exports without hazard columns show missing fields rather than inferred values.

Classification assignments, guide text and BMPs are curated separately in `data/ingredients.json` and `data/education.json`. They do not change automatically when the EPA workbook updates. Review the latest FRAC/IRAC lists before changing group assignments, including biological strain identity, then update the reference version and review date.

To regenerate the fact sheet after an editorial update:

```sh
python3 -m pip install -r requirements-docs.txt
python3 build_fact_sheet.py
python3 refresh_epa.py --workbook /path/to/apprildatadump_public.xlsx
python3 build_preview.py
python3 test_project.py --require-node
```

The PDF build is an optional documentation dependency. Opening the app, importing EPA data and running the standard tests do not require ReportLab. Review rendered PDF pages before publishing an editorial revision.

Sources are linked in the guide and PDF. General pollinator BMPs draw on EPA resources and the Health Canada resource linked by EPA. Canadian legal requirements, including lubricant rules, are not presented as U.S. requirements. This is an educational draft prepared for CPN review; it has not been approved or endorsed by CPN.
