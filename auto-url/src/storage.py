import json
from pathlib import Path
from typing import Optional
from .models import URLItem, URLGroup, Schedule, AppSettings, Logger


class StorageService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = Logger("StorageService")

        base_dir = Path(__file__).parent.parent
        self.config_dir = base_dir / "data"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.urls_file = self.config_dir / "urls.json"
        self.groups_file = self.config_dir / "groups.json"
        self.schedules_file = self.config_dir / "schedules.json"
        self.settings_file = self.config_dir / "settings.json"

        self._urls: list = []
        self._groups: list = []
        self._schedules: list = []
        self._settings = AppSettings()

        self._load_all()
        self._initialized = True

    def _load_all(self):
        self._urls = self._load_json(self.urls_file, [])
        self._groups = self._load_json(self.groups_file, [])
        self._schedules = self._load_json(self.schedules_file, [])
        self._settings = AppSettings.from_dict(self._load_json(self.settings_file, None))
        self.logger.info(f"Loaded {len(self._urls)} URLs, {len(self._groups)} groups, {len(self._schedules)} schedules")

    def _load_json(self, file_path: Path, default):
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
        return default

    def _save_json(self, file_path: Path, data):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save {file_path}: {e}")

    @property
    def urls(self) -> list[URLItem]:
        return [URLItem.from_dict(d) for d in self._urls]

    @property
    def groups(self) -> list[URLGroup]:
        return [URLGroup.from_dict(d) for d in self._groups]

    @property
    def schedules(self) -> list[Schedule]:
        return [Schedule.from_dict(d) for d in self._schedules]

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def add_url(self, url: URLItem):
        self._urls.append(url.to_dict())
        self._save_json(self.urls_file, self._urls)
        self.logger.info(f"Added URL: {url.name}")

    def update_url(self, url: URLItem):
        for i, d in enumerate(self._urls):
            if d['id'] == url.id:
                self._urls[i] = url.to_dict()
                break
        self._save_json(self.urls_file, self._urls)
        self.logger.info(f"Updated URL: {url.name}")

    def delete_url(self, url_id: str):
        self._urls = [d for d in self._urls if d['id'] != url_id]
        self._save_json(self.urls_file, self._urls)

        for d in self._schedules:
            if url_id in d.get('url_ids', []):
                d['url_ids'].remove(url_id)
        self._save_json(self.schedules_file, self._schedules)

        self.logger.info(f"Deleted URL: {url_id}")

    def get_url_by_id(self, url_id: str) -> Optional[URLItem]:
        for d in self._urls:
            if d['id'] == url_id:
                return URLItem.from_dict(d)
        return None

    def add_group(self, group: URLGroup):
        self._groups.append(group.to_dict())
        self._save_json(self.groups_file, self._groups)
        self.logger.info(f"Added group: {group.name}")

    def update_group(self, group: URLGroup):
        for i, d in enumerate(self._groups):
            if d['id'] == group.id:
                self._groups[i] = group.to_dict()
                break
        self._save_json(self.groups_file, self._groups)
        self.logger.info(f"Updated group: {group.name}")

    def delete_group(self, group_id: str):
        self._groups = [d for d in self._groups if d['id'] != group_id]
        self._save_json(self.groups_file, self._groups)

        for d in self._urls:
            if d.get('group_id') == group_id:
                d['group_id'] = None

        self._save_json(self.urls_file, self._urls)
        self.logger.info(f"Deleted group: {group_id}")

    def add_schedule(self, schedule: Schedule):
        schedule.calculate_next_execution()
        self._schedules.append(schedule.to_dict())
        self._save_json(self.schedules_file, self._schedules)
        self.logger.info(f"Added schedule: {schedule.name}")

    def update_schedule(self, schedule: Schedule):
        schedule.calculate_next_execution()
        for i, d in enumerate(self._schedules):
            if d['id'] == schedule.id:
                self._schedules[i] = schedule.to_dict()
                break
        self._save_json(self.schedules_file, self._schedules)
        self.logger.info(f"Updated schedule: {schedule.name}")

    def delete_schedule(self, schedule_id: str):
        self._schedules = [d for d in self._schedules if d['id'] != schedule_id]
        self._save_json(self.schedules_file, self._schedules)
        self.logger.info(f"Deleted schedule: {schedule_id}")

    def get_schedule_by_id(self, schedule_id: str) -> Optional[Schedule]:
        for d in self._schedules:
            if d['id'] == schedule_id:
                return Schedule.from_dict(d)
        return None

    def update_settings(self, settings: AppSettings):
        self._settings = settings
        self._save_json(self.settings_file, settings.to_dict())
        self.logger.info("Updated settings")

    def get_urls_for_schedule(self, schedule: Schedule) -> list[URLItem]:
        result = []
        for d in self._urls:
            if d['id'] in schedule.url_ids and d.get('enabled', True):
                result.append(URLItem.from_dict(d))
        return result

    def export_data(self) -> dict:
        return {
            "urls": self._urls,
            "groups": self._groups,
            "schedules": self._schedules,
            "exported_at": datetime.now().isoformat()
        }

    def import_data(self, data: dict):
        self._urls = data.get("urls", [])
        self._groups = data.get("groups", [])
        self._schedules = data.get("schedules", [])

        self._save_json(self.urls_file, self._urls)
        self._save_json(self.groups_file, self._groups)
        self._save_json(self.schedules_file, self._schedules)

        self.logger.info("Imported data successfully")


from datetime import datetime
