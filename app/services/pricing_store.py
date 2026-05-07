from pathlib import Path
import json
from app.services.storage import get_writable_data_dir

DEFAULTS = {
    "trip": 175,
    "fuel": 20,
    "labor": 175,
    "crew_labor": 235,
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
        {"city": "No Sales Tax", "rate": 0},
        {"city": "Default / San Diego", "rate": 7.75},
        {"city": "San Diego", "rate": 7.75},
        {"city": "Escondido", "rate": 8.75}
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
        return data

    def save(self, data):
        current = self.load() if self.path.exists() else dict(DEFAULTS)
        if isinstance(data, dict):
            current.update(data)
        self.path.write_text(json.dumps(current, indent=2))
