# Side-by-side comparison matrix

Open **Comparison matrix**. Search by product name, alternate name, ingredient or full EPA registration; choose a match and press **Add to matrix**. The Compare checkboxes in Explore products use the same selection. Up to four formulations are retained in selection order and saved in the browser. Remove a column to replace it, or clear the selection. Product filters do not erase selections.

The matrix includes registration dates, ingredient percentages, FRAC/IRAC codes and classification references, target pests, label specifications, EPA signal words, restricted-use flags, state evidence and source links. Efficacy ratings and rankings are excluded.

**Export matrix CSV** downloads only the selected formulations as columns, including source URLs and the complete EPA pest index. **Print / Save PDF** prints the matrix in landscape; the print button expands the pest lists. On smaller screens, scroll inside the matrix to see additional columns. The first column and header remain visible while scrolling.

## Evidence and missing data

- `FIRST_REG_DT`, `STATUS_DT` and `MAX_LABEL_DT` are separate dates from the exact EPA product row. A missing first-registration date is never replaced by a status date or inherited from a base product.
- `PESTS` is retained verbatim as a product-wide index. It is not a crop-specific use authorization. The source can include uses outside seed treatment. Expand the index to view it.
- Crop-specific targets and selected specifications use separately reviewed label extracts. Initial coverage is **two exact registrations**: Saltro 100-1648 (soybeans; July 24, 2025 label) and LumiTreo 352-937 (soybeans; February 18, 2022 label). Other formulations show **No reviewed label extract loaded** and retain source label links where available. These extracts do not supply complete use directions.
- Label source links, PDF pages, source dates, review dates and crop scope accompany the extracts. Compare rate units carefully; weight conversions use the stated seed count assumptions.
- FRAC/IRAC classification coverage and missing assignments remain explicit. EPA ingredient percentages are not application rates.
- Official state reports and provider availability remain separate. No state approval is inferred from a federal registration or from a provider report.

## Updates and editorial review

The normal EPA workbook import now refreshes first-registration dates, product-wide pests and physical form along with existing source facts. The included September 21, 2026 workbook has first-registration dates for all 880 records and pest indexes for 879. This field expansion did not change the registration census or establish latest EPA website parity.

`data/label-specs.json` is an editorial reference, validated by `comparison_evidence.py` and included by every catalog publication. Match on the full EPA number and the ingredient PC-code/percentage fingerprint. A different/newer label reference, a changed composition, or an elapsed review deadline suppresses the extract and requests review. Distributor registrations never inherit extracts. A review deadline is an editorial freshness check, not an approval expiration date.

To extend coverage, review the exact product label, add its scoped fields and source pages, and run `python test_project.py --require-node`. Never derive rates, PPE or targets from a similarly named product. EPA imports do not automatically rewrite label summaries.

The host schedule remains subject to the existing hosting setup. Local HTML and GitHub tests do not activate source updates.
