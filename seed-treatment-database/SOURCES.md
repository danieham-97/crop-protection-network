# Sources and provenance

The uploaded EPA APPRIL workbook is the authority for this imported registration inventory. Greenbook/CDMS links add supporting product and label references; they do not overwrite EPA status or formulation.

## EPA workbook

- Supplied file: apprildatadump_public(2).xlsx
- Official source: https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx
- Search interface: https://ordspub.epa.gov/ords/pesticides/f?p=APPRIL_PUBLIC:2
- Worksheet: ACTIVE_REGISTRATIONS5_PUBLIC_V
- Creation metadata: 2026-09-21T11:58:19Z
- Imported and cutoff: 2026-10-16; start date blank.
- SHA-256: c8ae0c3f1d683914689d3b4e08904b4c617735b19120dc819412a70b652258bb

366,837 rows were scanned. 886 active registrations matched the 14 sites, six deltamethrin records were removed, and 880 remain. The audit retains per-site counts, source rows, exclusions, and quality gaps. Creation metadata is not proof of a current-through date or of the latest release. The supplied original file was not altered.

## Distributor relationships and ingredient synonym

- EPA supplemental-distribution requirements and numbering: https://www.epa.gov/pesticide-registration/pesticide-registration-manual-chapter-9-supplemental-distribution-registered
- EPA Form 8570-5: https://www.epa.gov/sites/default/files/2020-01/documents/8570-5.pdf
- EPA chemical-name index: https://www.epa.gov/system/files/documents/2022-10/DSLChem.pdf — PC 113502 lists both Metalaxyl-M and mefenoxam. The EPA name remains displayed and the reviewed synonym is searchable.

185 distributor formulations are explicitly linked to related base registrations. Two missing formulations remain unresolved and visibly flagged; one concentration is missing. Distributor site claims are not inferred from base sites.

## Saved Greenbook and CDMS references

These links were reviewed in the earlier October 16 work. The source-reference JSON retains the original observation/revision information. Five Greenbook and three CDMS entries match this EPA inventory by full registration number. Unmatched references do not add products to the inventory. No live provider feed is connected.

- 71532-22-7969 · Greenbook: https://www.greenbook.net/products/46194/acquire-fungicide-seed-treatment
- 100-1508 · Greenbook: https://www.greenbook.net/products/57033/cruisermaxx-vibrance
- 100-1508 · Cdms: https://www.cdms.net/ldat/ldBSC000.pdf
  - specimen_label: https://www.cdms.net/ldat/ldBSC000.pdf
- 7969-441 · Greenbook: https://www.greenbook.net/products/66496/ilevo-seed-treatment
- 352-937 · Greenbook: https://www.greenbook.net/products/65891/lumitreo-fungicide-seed-treatment
- 352-937 · Cdms: https://www.cdms.net/ldat/ldJ2L000.pdf
  - specimen_label: https://www.cdms.net/ldat/ldJ2L000.pdf
- 100-1648 · Greenbook: https://www.greenbook.net/products/64344/saltro
- 55146-159 · Greenbook: https://www.greenbook.net/products/47369/salient-tmi-seed-treatment
- 55146-159 · Cdms: https://www.cdms.net/labelsSDS/home/prodidx?key=16105
- 7969-418 · Greenbook: https://www.greenbook.net/products/64948/teraxxa-seed-treatment
- 7969-418 · Cdms: https://www.cdms.net/labelsSDS/home/prodidx?key=19404

## Other integration references

- CDMS label/SDS search: https://www.cdms.net/LabelsSDS/home
- TELUS supported agriculture API information: https://www.telus.com/agcg/en/agriculture/agriculture-api
- EPA PPLS API documentation: https://www.epa.gov/pesticide-labels/pesticide-product-label-system-ppls-application-program-interface-api
- EPA PPIS bulk information: https://www.epa.gov/ingredients-used-pesticide-products/ppis-download-product-information-data
- Existing CPN tool: https://cropprotectionnetwork.org/whats-on-your-seed-tool

The official workbook URL is implemented in the updater, but live retrieval and the CPN host schedule were not activated here. PPIS remains optional staging code; it is not substituted for the APPRIL workbook. Ingredient classification references are stored individually in data/ingredients.json.
