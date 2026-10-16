"""Curated educational mapping. Unknowns stay unknown; no substring guesses.

Groups describe ingredients, not a product's approved uses or efficacy.
Review mappings against the cited authorities when adding or updating entries.
"""
import re

FRAC = "https://www.frac.info/fungicide-resistance-management/by-fungicide-common-name/"
IRAC = "https://irac-online.org/mode-of-action/"
MAP = {}


def add(names, purposes, family, group, source):
    for name in names.split("|"):
        MAP[name.casefold()] = {"purposes": purposes, "family": family,
                              "group": group, "source": source, "reviewed": "2026-10-15"}


add("thiamethoxam|clothianidin|imidacloprid|acetamiprid", ["Insecticide"], "Neonicotinoid", "IRAC 4A", IRAC)
add("cyantraniliprole|chlorantraniliprole", ["Insecticide"], "Diamide", "IRAC 28", IRAC)
add("bifenthrin|tefluthrin|permethrin", ["Insecticide"], "Pyrethroid", "IRAC 3A", IRAC)
add("spinosad", ["Insecticide"], "Spinosyn", "IRAC 5", IRAC)
add("abamectin|avermectin b1", ["Insecticide", "Nematicide"], "Avermectin", "IRAC 6", IRAC)
add("fludioxonil", ["Fungicide"], "Phenylpyrrole", "FRAC 12", FRAC)
add("metalaxyl|mefenoxam|metalaxyl-m", ["Fungicide"], "Phenylamide", "FRAC 4", FRAC)
add("azoxystrobin|pyraclostrobin|trifloxystrobin|fluoxastrobin", ["Fungicide"], "QoI", "FRAC 11", FRAC)
add("sedaxane|fluxapyroxad|penflufen|carboxin|boscalid|inpyrfluxam", ["Fungicide"], "SDHI", "FRAC 7", FRAC)
add("fluopyram|cyclobutrifluram", ["Fungicide", "Nematicide"], "SDHI", "FRAC 7", FRAC)
add("difenoconazole|tebuconazole|ipconazole|triticonazole|prothioconazole|myclobutanil", ["Fungicide"], "DMI / triazole", "FRAC 3", FRAC)
add("thiabendazole|thiophanate-methyl", ["Fungicide"], "MBC", "FRAC 1", FRAC)
add("ethaboxam", ["Fungicide"], "Ethylamino-thiazole-carboxamide", "FRAC 22", FRAC)
add("oxathiapiprolin", ["Fungicide"], "OSBPI", "FRAC 49", FRAC)
add("captan", ["Fungicide"], "Multi-site / phthalimide", "FRAC M04", FRAC)
add("thiram", ["Fungicide"], "Multi-site / dithiocarbamate", "FRAC M03", FRAC)
add("pydiflumetofen", ["Fungicide"], "SDHI", "FRAC 7", FRAC)

# Additional EPA evidence for ingredients with more than one functional use.
MAP["fluopyram"]["purpose_source"] = "https://www.epa.gov/sites/default/files/2019-09/documents/fluopyram-extension-of-exclusive-use.pdf"
MAP["cyclobutrifluram"]["purpose_source"] = "https://www.epa.gov/pesticides/epa-registers-new-pesticide-active-ingredient-cyclobutrifluram"
for alias in ("abamectin", "avermectin b1"):
    MAP[alias]["purpose_source"] = "https://ordspub.epa.gov/ords/pesticides/f?p=PPLS:102:::NO::P102_REG_NUM:100-1321"

CATEGORIES = {
    "Fungicide": "Used against fungal or oomycete diseases; the organisms controlled depend on the label.",
    "Insecticide": "Used against insect pests. Chemical families and modes of action help explain how ingredients differ.",
    "Nematicide": "Used against plant-parasitic nematodes. Activity is specific to the ingredient, crop, and labeled use.",
    "Biostimulant": "A plant growth or nutrient-use category, not automatically an EPA pesticide classification. Biological ingredients are not assumed to be biostimulants.",
}


def classify(name):
    key = re.sub(r"\s+", " ", name).strip().casefold()
    return dict(MAP.get(key, {"purposes": ["Unclassified"], "family": "Needs review",
                              "group": None, "source": None, "reviewed": None}))
