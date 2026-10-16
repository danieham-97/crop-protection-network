"""Fictional fixtures, never loaded into the production database."""
from .config import SITES
from .normalize import normalize


def seed_demo(store, today):
    fixtures = [
        ("PrairieStart Complete", ["Corn", "Soybeans"], "Thiamethoxam (060109/153719-23-4) - (20%), Fludioxonil (071503/131341-86-1) - (2%), Mefenoxam (113502/70630-17-0) - (1%)"),
        ("Rootline Shield", ["Soybeans", "Cotton"], "Fluopyram (080302/658066-35-4) - (40%)"),
        ("Fieldwise Foundation", ["Wheat", "Barley"], "Sedaxane (129223/874967-67-6) - (5%), Difenoconazole (128847/119446-68-3) - (3%), Mefenoxam (113502/70630-17-0) - (1%)"),
        ("Emergence Plus", ["Corn", "Cotton"], "Clothianidin (044309/210880-92-5) - (25%), Ipconazole (125618/125225-28-7) - (1%)"),
        ("Seedward Select", ["Alfalfa", "Small grains"], "Metalaxyl (113501/57837-19-1) - (30%)"),
        ("StandGuard Trio", ["Soybeans", "Wheat"], "Pyraclostrobin (099100/175013-18-0) - (5%), Fluxapyroxad (138009/907204-31-3) - (5%), Metalaxyl (113501/57837-19-1) - (5%)"),
        ("CottonStart Duo", ["Cotton"], "Imidacloprid (129099/138261-41-3) - (30%), Thiram (079801/137-26-8) - (10%)"),
        ("Rootwise Reserve", ["Corn", "Cereal crops"], "Azoxystrobin (128810/131860-33-8) - (10%), Fludioxonil (071503/131341-86-1) - (3%)"),
        ("Greenfield Advance", ["Soybeans"], "Unreviewed microbial strain (000000/) - (1%)"),
    ]
    products = []
    for index, (name, crops, ais) in enumerate(fixtures, 1):
        p = normalize({"reg_num": f"999999-{index}", "product_name": name,
                       "status_group": "Active", "status_dt": "2025-01-01", "ais": ais,
                       "sites": ", ".join(s for s, crop in SITES.items() if crop in crops),
                       "company_name": "Example Agronomy Co. · Fictional", "reg_type": "Sec3",
                       "status_desc": "Illustrative only", "signal_word": "Not applicable"}, today)
        p.update(reg_num=f"DEMO-{index:03}", label_url=None, label_registration=None)
        products.append(p)
    store.publish(products, source="Fictional demonstration data", demo=True, as_of_date=today.isoformat(),
                  last_success=None, source_rows_scanned=len(products))
