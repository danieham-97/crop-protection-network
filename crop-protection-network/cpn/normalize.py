import html
import re
from datetime import date, datetime
from urllib.parse import quote

from .classification import classify
from .config import SITES


class SourceError(ValueError):
    pass


def text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value)))).strip()


def key(value):
    return re.sub(r"[^a-z0-9]", "", text(value).casefold())


ALIASES = {
    "reg_num": ["reg_num", "registration number", "epa registration number", "EPA Product Registration Number"],
    "product_name": ["product_name", "product name"],
    "status_group": ["status_group", "status group"],
    "status_dt": ["status_dt", "status date"],
    "status_desc": ["status_desc", "status"],
    "reg_type": ["reg_type", "registration type"],
    "company_name": ["company_name", "company name"],
    "ais": ["ais", "active ingredients", "ingredients actives"],
    "sites": ["sites", "site", "site name"],
    "abns": ["abns", "alternate brand names", "alternatebrandnames"],
    "pests": ["pests", "pest"],
    "rup_flag": ["rup_flag", "restricted use flag"],
    "signal_word": ["signal_word", "signal word"],
    "pesticide_category": ["pesticide_category", "pesticide category", "pest_cat"],
}
ALIAS_INDEX = {key(alias): field for field, aliases in ALIASES.items() for alias in aliases}


def canonical(row):
    return {ALIAS_INDEX.get(key(k), key(k)): v for k, v in row.items() if k is not None}


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = text(value)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value, fmt).date()
        except ValueError:
            pass
    raise SourceError(f"Unrecognized status date: {value!r}")


def matching_sites(value):
    # Anchored full labels: never split the comma inside 'Soybeans, Edible ...'.
    raw = text(value)
    found = []
    for site in SITES:
        pattern = r"(?:^|[,;|\n])\s*" + re.escape(site).replace(r"\ ", r"\s+") + r"\s*(?=$|[,;|\n])"
        if re.search(pattern, raw, re.I):
            found.append(site)
    return found


AI_PATTERN = re.compile(r"\s*(?P<name>.*?)\s*\((?P<pc>\d{1,6})/(?P<cas>[^)]*)\)\s*-\s*\(\s*(?P<pct>[\d.]+)\s*%\s*\)\s*(?:[,;]|$)")


def ingredients(value):
    raw = text(value)
    if not raw:
        return [], []
    result, warnings = [], []
    pos = 0
    # APPRIL structured terminators preserve chemical names containing commas.
    for match in AI_PATTERN.finditer(raw):
        if raw[pos:match.start()].strip(" ,;"):
            raise SourceError("Unexpected ingredient text between structured entries")
        name = match["name"].strip(" ,;")
        percent = float(match["pct"])
        if not name or not 0 <= percent <= 100:
            raise SourceError("Invalid active ingredient name or percentage")
        result.append({"name": name, "pc_code": match["pc"].zfill(6), "cas": match["cas"].strip(),
                       "percent": percent, **classify(name)})
        pos = match.end()
    remainder = raw[pos:].strip(" ,;")
    if remainder:
        # Retain every unparsed character. Do not fabricate a comma-split chemical.
        result.append({"name": remainder, "pc_code": None, "cas": None, "percent": None,
                       "purposes": ["Unclassified"], "family": "Unparsed EPA ingredient text",
                       "group": None, "source": None, "reviewed": None})
        warnings.append("Some ingredient text needs review; original EPA text is retained.")
    return result, warnings


def validate_schema(row):
    required = {"reg_num", "product_name", "status_group", "status_dt", "sites", "ais"}
    missing = required - set(canonical(row))
    if missing:
        raise SourceError("EPA schema is missing required columns: " + ", ".join(sorted(missing)))


def normalize(row, today):
    r = canonical(row)
    if text(r.get("status_group")).casefold() not in {"active", "active products"}:
        return None
    # End is an inclusive range bound, not a requirement that the action happened today.
    status_date = as_date(r.get("status_dt"))
    if status_date > today:
        return None
    sites = matching_sites(r.get("sites"))
    if not sites:
        return None
    reg = text(r.get("reg_num"))
    if not re.fullmatch(r"\d+-\d+(?:-\d+)?", reg):
        raise SourceError(f"Invalid registration number: {reg!r}")
    name = text(r.get("product_name"))
    if not name:
        raise SourceError(f"Missing product name for {reg}")
    ai, warnings = ingredients(r.get("ais"))
    if not ai:
        warnings.append("Active ingredients not supplied in this source record.")
    base_reg = "-".join(reg.split("-")[:2])
    return {
        "reg_num": reg, "name": name, "company": text(r.get("company_name")),
        "registration_type": text(r.get("reg_type")), "status": text(r.get("status_desc")),
        "status_date": status_date.isoformat(), "sites": sites,
        "crops": sorted({SITES[s] for s in sites}), "ingredients": ai,
        "purposes": sorted({p for item in ai for p in item["purposes"]}),
        "all_sites": text(r.get("sites")), "raw_ingredients": text(r.get("ais")),
        "alternate_names": text(r.get("abns")), "pests": text(r.get("pests")),
        "restricted_use": text(r.get("rup_flag")), "signal_word": text(r.get("signal_word")),
        "label_url": "https://ordspub.epa.gov/ords/pesticides/f?p=PPLS:102:::NO::P102_REG_NUM:" + quote(base_reg),
        "label_registration": base_reg, "warnings": warnings,
    }
