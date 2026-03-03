import subprocess
import threading
import time
from datetime import datetime
from typing import Optional
from .models import Schedule, Logger
from .storage import StorageService
from .launcher import URLLauncherService


class SchedulerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.storage = StorageService()
        self.launcher = URLLauncherService()
        self.logger = Logger("SchedulerService")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._initialized = True

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Scheduler started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.logger.info("Scheduler stopped")

    def _run_loop(self):
        while self._running:
            try:
                self._check_schedules()
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
            time.sleep(60)

    def _check_schedules(self):
        now = datetime.now()
        schedules = self.storage.schedules

        for schedule_dict in schedules:
            if not schedule_dict.enabled:
                continue

            schedule = Schedule.from_dict(schedule_dict) if isinstance(schedule_dict, dict) else schedule_dict
            if not schedule.next_execution:
                schedule.calculate_next_execution()
                self.storage.update_schedule(schedule)

            if not schedule.next_execution:
                continue

            try:
                next_exec = datetime.fromisoformat(schedule.next_execution)
                if next_exec <= now:
                    self._execute_schedule(schedule)

                    schedule.last_executed = now.isoformat()
                    schedule.calculate_next_execution()
                    self.storage.update_schedule(schedule)
            except Exception as e:
                self.logger.error(f"Error checking schedule {schedule.name}: {e}")

    def _execute_schedule(self, schedule: Schedule):
        self.logger.info(f"Executing schedule: {schedule.name}")

        urls = self.storage.get_urls_for_schedule(schedule)
        browser_id = self.storage.settings.selected_browser_bundle_id

        self.launcher.open_urls(urls, browser_id, new_window=True)
        self._send_notification(
            title="已打开网址",
            body=f"{schedule.name} - 已打开 {len(urls)} 个网址"
        )

    def execute_now(self, schedule: Schedule):
        self.logger.info(f"Manually executing schedule: {schedule.name}")

        urls = self.storage.get_urls_for_schedule(schedule)
        browser_id = self.storage.settings.selected_browser_bundle_id

        self.launcher.open_urls(urls, browser_id, new_window=True)
        self._send_notification(
            title="已手动执行",
            body=f"{schedule.name} - 已打开 {len(urls)} 个网址"
        )

    def _send_notification(self, title: str, body: str):
        if not self.storage.settings.enable_notifications:
            return
        try:
            sound = "-sound default" if self.storage.settings.sound_enabled else ""
            subprocess.run([
                'osascript', '-e',
                f'display notification "{body}" with title "{title}" {sound}'
            ], check=True)
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def refresh_schedules(self):
        for schedule_dict in self.storage.schedules:
            schedule = Schedule.from_dict(schedule_dict) if isinstance(schedule_dict, dict) else schedule_dict
            schedule.calculate_next_execution()
            self.storage.update_schedule(schedule)
        self.logger.info("Refreshed all schedules")

import subprocess
