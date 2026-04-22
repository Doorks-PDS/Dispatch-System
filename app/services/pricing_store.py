from pathlib import Path
import json
from app.services.storage import get_writable_data_dir

DEFAULTS = {
    "trip": 175,
    "fuel": 20,
    "labor": 175,
    "crew_labor": 235,
    "tax": 7.75
}

class PricingStore:
    def __init__(self, project_root):
        self.path = get_writable_data_dir(project_root) / "pricing.json"
        self._ensure()

    def _ensure(self):
        if not self.path.exists():
            self.save(DEFAULTS)

    def load(self):
        return json.loads(self.path.read_text())

    def save(self, data):
        self.path.write_text(json.dumps(data, indent=2))
