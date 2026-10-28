from pathlib import Path
import json
from app.services.storage import get_writable_data_dir

DEFAULTS = {
    "trip": 190,
    "fuel": 20,
    "labor": 190,
    "crew_labor": 250,
    "tax": 7.75,
    "default_terms": "Due on Receipt",
    "billing_terms": [
        "Due on Receipt",
        "100% Materials Deposit/Remainder Upon Complete",
        "Net 5",
        "Net 10",
        "Net 15",
        "Net 30",
        "Net 60",
        "Net 90"
    ],
    "tax_cities": [
        {
                "city": "No Sales Tax",
                "rate": 0.0
        },
        {
                "city": "Default / San Diego",
                "rate": 7.75
        },
        {
                "city": "San Diego",
                "rate": 7.75
        },
        {
                "city": "Escondido",
                "rate": 8.75
        },
        {
                "city": "Carlsbad",
                "rate": 7.75
        },
        {
                "city": "Oceanside",
                "rate": 8.25
        },
        {
                "city": "Vista",
                "rate": 8.25
        },
        {
                "city": "San Marcos",
                "rate": 7.75
        },
        {
                "city": "Encinitas",
                "rate": 7.75
        },
        {
                "city": "Poway",
                "rate": 7.75
        },
        {
                "city": "El Cajon",
                "rate": 8.25
        },
        {
                "city": "La Mesa",
                "rate": 8.5
        },
        {
                "city": "Chula Vista",
                "rate": 8.75
        },
        {
                "city": "National City",
                "rate": 8.75
        },
        {
                "city": "Imperial Beach",
                "rate": 8.75
        },
        {
                "city": "Temecula",
                "rate": 8.75
        },
        {
                "city": "Murrieta",
                "rate": 8.75
        },
        {
                "city": "Riverside",
                "rate": 8.75
        },
        {
                "city": "Irvine",
                "rate": 7.75
        },
        {
                "city": "Los Angeles",
                "rate": 9.5
        }
]
}

class PricingStore:
    def __init__(self, project_root):
        self.path = get_writable_data_dir(project_root) / "pricing.json"
        self._ensure()

    def _ensure(self):
        if not self.path.exists():
            self.save(DEFAULTS)

    def load(self):
        data = json.loads(self.path.read_text())
        if not isinstance(data, dict):
            data = {}
        for key, value in DEFAULTS.items():
            data.setdefault(key, value)
        old_cities = ["No Sales Tax", "Default / San Diego", "San Diego", "Escondido"]
        saved_cities = data.get("tax_cities")
        if (isinstance(saved_cities, list) and len(saved_cities) == 4
                and [x.get("city") for x in saved_cities if isinstance(x, dict)] == old_cities):
            # Legacy seeded defaults, not a full city list. Read-only fallback;
            # don't rewrite or destroy the persisted pricing file.
            data["tax_cities"] = [dict(x) for x in DEFAULTS["tax_cities"]]
        return data

    def save(self, data):
        current = self.load() if self.path.exists() else dict(DEFAULTS)
        if isinstance(data, dict):
            current.update(data)
        self.path.write_text(json.dumps(current, indent=2))
