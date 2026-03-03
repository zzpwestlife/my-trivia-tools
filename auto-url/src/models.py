import json
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class TriggerType(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class URLItem:
    id: str
    name: str
    url: str
    group_id: Optional[str] = None
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, name: str, url: str, group_id: Optional[str] = None):
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            url=url,
            group_id=group_id,
            enabled=True,
            created_at=now,
            updated_at=now
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class URLGroup:
    id: str
    name: str
    color_hex: str = "#007AFF"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, name: str, color_hex: str = "#007AFF"):
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            color_hex=color_hex,
            created_at=datetime.now().isoformat()
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Schedule:
    id: str
    name: str
    url_ids: list
    trigger_type: str = TriggerType.DAILY.value
    trigger_value: str = "09:00"
    week_days: list = field(default_factory=lambda: [1, 2, 3, 4, 5])
    enabled: bool = True
    last_executed: Optional[str] = None
    next_execution: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, name: str, url_ids: list, trigger_type: str = TriggerType.DAILY.value,
               trigger_value: str = "09:00", week_days: Optional[list] = None):
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            url_ids=url_ids,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            week_days=week_days or [1, 2, 3, 4, 5],
            enabled=True,
            created_at=now,
            updated_at=now
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def calculate_next_execution(self):
        from datetime import timedelta
        now = datetime.now()

        if self.trigger_type == TriggerType.ONCE.value:
            try:
                dt = datetime.strptime(self.trigger_value, "%Y-%m-%d %H:%M")
                if dt > now:
                    self.next_execution = dt.isoformat()
                else:
                    self.next_execution = None
            except ValueError:
                self.next_execution = None

        elif self.trigger_type == TriggerType.DAILY.value:
            self.next_execution = self._calculate_daily_next(now)

        elif self.trigger_type == TriggerType.WEEKLY.value:
            self.next_execution = self._calculate_weekly_next(now)

        elif self.trigger_type == TriggerType.CUSTOM.value:
            self.next_execution = self._calculate_cron_next(now)

        self.updated_at = datetime.now().isoformat()

    def _calculate_daily_next(self, now):
        try:
            hour, minute = map(int, self.trigger_value.split(":"))
            today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if today > now:
                return today.isoformat()
            else:
                from datetime import timedelta
                return (today + timedelta(days=1)).isoformat()
        except:
            return None

    def _calculate_weekly_next(self, now):
        try:
            hour, minute = map(int, self.trigger_value.split(":"))
            valid_days = set(int(d) for d in self.week_days)

            for day_offset in range(8):
                check_date = now + timedelta(days=day_offset)
                check_weekday = check_date.weekday() + 1

                if check_weekday in valid_days:
                    scheduled = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if scheduled > now:
                        return scheduled.isoformat()

            return None
        except:
            return None

    def _calculate_cron_next(self, now):
        parts = self.trigger_value.split()
        if len(parts) < 5:
            return None

        minute_part, hour_part, day_part, month_part, weekday_part = parts[:5]
        from datetime import timedelta

        def parse_cron_field(value, min_val, max_val):
            if value == '*':
                return set(range(min_val, max_val + 1))
            values = set()
            for part in value.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    values.update(range(start, end + 1))
                else:
                    values.add(int(part))
            return values

        # Parse fields
        allowed_minutes = parse_cron_field(minute_part, 0, 59)
        allowed_hours = parse_cron_field(hour_part, 0, 23)
        # allowed_days = parse_cron_field(day_part, 1, 31) # Simplified, day logic is tricky with month length
        # allowed_months = parse_cron_field(month_part, 1, 12)
        allowed_weekdays = parse_cron_field(weekday_part, 0, 7) # 0=Sun, 1=Mon... 7=Sun

        # Check next 365 days
        for day_offset in range(365):
            check_date = now + timedelta(days=day_offset)
            
            # Weekday check: python weekday() is 0=Mon, 6=Sun.
            # Crontab: 0=Sun, 1=Mon, ..., 6=Sat, 7=Sun.
            # Convert python weekday to crontab weekday (0-6, where 0 is Sun)
            # Python: Mon=0, Tue=1, ... Sun=6
            # Crontab (Linux): Sun=0, Mon=1, ... Sat=6
            
            # Let's align with standard crontab: 1=Mon, 5=Fri
            py_weekday = check_date.weekday() # 0=Mon
            cron_weekday = py_weekday + 1 # 1=Mon, 7=Sun
            if cron_weekday == 7: cron_weekday = 0 # 0=Sun

            # Special handling for 7=Sun in input
            if 7 in allowed_weekdays:
                allowed_weekdays.add(0)

            if weekday_part != '*' and cron_weekday not in allowed_weekdays:
                continue

            check_day = check_date.day
            check_month = check_date.month

            if day_part != "*" and check_day not in parse_cron_field(day_part, 1, 31):
                continue
            if month_part != "*" and check_month not in parse_cron_field(month_part, 1, 12):
                continue

            # Iterate hours and minutes
            for h in sorted(list(allowed_hours)):
                for m in sorted(list(allowed_minutes)):
                    scheduled = check_date.replace(hour=h, minute=m, second=0, microsecond=0)
                    if scheduled > now:
                        return scheduled.isoformat()
        
        return None


@dataclass
class AppSettings:
    launch_at_login: bool = False
    show_in_menu_bar: bool = True
    default_browser: Optional[str] = None
    enable_notifications: bool = True
    sound_enabled: bool = False
    selected_browser_bundle_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data) if data else cls()


class Logger:
    def __init__(self, name: str = "AutoURL"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            base_dir = Path(__file__).parent.parent
            log_dir = base_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_dir / "autourl.log")
            file_handler.setLevel(logging.DEBUG)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)
