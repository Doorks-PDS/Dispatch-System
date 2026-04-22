from pathlib import Path
import json
from uuid import uuid4
from app.services.storage import get_writable_data_dir

class DoorLogsStore:
    def __init__(self, project_root):
        self.path = get_writable_data_dir(project_root) / "door_logs.json"
        if not self.path.exists():
            self.save([])

    def load(self):
        return json.loads(self.path.read_text())

    def save(self, data):
        self.path.write_text(json.dumps(data, indent=2))

    def create(self, log):
        data = self.load()
        log["id"] = uuid4().hex
        data.append(log)
        self.save(data)
        return log

    def update(self, log_id, updates):
        data = self.load()
        for d in data:
            if d["id"] == log_id:
                d.update(updates)
        self.save(data)

    def delete(self, log_id):
        data = self.load()
        data = [d for d in data if d["id"] != log_id]
        self.save(data)
