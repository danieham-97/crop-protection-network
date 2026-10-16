import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SITES = {
    "Alfalfa (seed treatment)": "Alfalfa",
    "Barley (seed treatment)": "Barley",
    "Cereal crops (seed treatment)": "Cereal crops",
    "Corn (seed treatment)": "Corn",
    "Corn (field) (seed treatment)": "Corn",
    "Cotton (seed treatment)": "Cotton",
    "Cotton (acid delinted) (seed treatment)": "Cotton",
    "Cotton (machine delinted) (seed treatment)": "Cotton",
    "Cotton (reginned) (seed treatment)": "Cotton",
    "Cotton Seed (Fuzzy) (seed treatment)": "Cotton",
    "Small grains (seed treatment)": "Small grains",
    "Soybeans (seed treatment)": "Soybeans",
    "Soybeans, Edible (Seed and Pod Vegetable) (seed treatment)": "Soybeans",
    "Wheat (seed treatment)": "Wheat",
}
API_URL = "https://ordspub.epa.gov/ords/pesticides/apprilapi/"
LANDING_URL = "https://ordspub.epa.gov/ords/pesticides/f?p=APPRIL:1"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    timezone: str = field(default_factory=lambda: os.getenv("APP_TIMEZONE", "America/Chicago"))
    sync_seconds: int = field(default_factory=lambda: int(os.getenv("SYNC_INTERVAL_SECONDS", "21600")))
    dump_url: str = field(default_factory=lambda: os.getenv("EPA_DUMP_URL", ""))
    demo: bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "false").lower() == "true")

    def today(self):
        return datetime.now(ZoneInfo(self.timezone)).date()

    @property
    def db_path(self):
        return self.data_dir / ("demo.sqlite3" if self.demo else "catalog.sqlite3")
