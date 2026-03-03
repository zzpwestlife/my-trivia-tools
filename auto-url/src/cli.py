import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import URLItem, URLGroup, Schedule, TriggerType, AppSettings
from src.storage import StorageService
from src.launcher import URLLauncherService
from src.scheduler import SchedulerService


def sync_config_if_needed():
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        return
    
    storage = StorageService()
    config_mtime = config_path.stat().st_mtime
    storage_mtime = getattr(storage, '_config_mtime', 0)
    
    if config_mtime > storage_mtime:
        import importlib
        import import_config
        importlib.reload(import_config)
        import_config.load_config(str(config_path))
        storage._config_mtime = config_mtime


class CLI:
    def __init__(self):
        self.storage = StorageService()
        self.launcher = URLLauncherService()
        self.scheduler = SchedulerService()

    def run(self, args):
        if args.command == 'url':
            self.handle_url(args)
        elif args.command == 'schedule':
            self.handle_schedule(args)
        elif args.command == 'group':
            self.handle_group(args)
        elif args.command == 'start':
            self.start_daemon()
        elif args.command == 'open':
            self.open_all()
        else:
            print("Unknown command. Use --help for usage information.")

    def handle_url(self, args):
        if args.subcommand == 'list':
            self.list_urls()
        elif args.subcommand == 'add':
            self.add_url(args)
        elif args.subcommand == 'edit':
            self.edit_url(args)
        elif args.subcommand == 'delete':
            self.delete_url(args)
        elif args.subcommand == 'open':
            self.open_url(args)

    def list_urls(self):
        urls = self.storage.urls
        if not urls:
            print("No URLs found.")
            return

        print(f"\n{'ID':<8} {'Name':<20} {'URL':<40} {'Enabled':<10}")
        print("-" * 80)
        for url in urls:
            status = "✓" if url.enabled else "✗"
            print(f"{url.id[:8]:<8} {url.name:<20} {url.url:<40} {status:<10}")

    def add_url(self, args):
        if not args.name or not args.url:
            print("Error: --name and --url are required")
            return

        is_valid, error = self.launcher.validate_url(args.url)
        if not is_valid:
            print(f"Error: {error}")
            return

        url = URLItem.create(name=args.name, url=args.url, group_id=args.group)
        self.storage.add_url(url)
        print(f"Added URL: {url.name} ({url.id[:8]})")

    def edit_url(self, args):
        if not args.id:
            print("Error: --id is required")
            return

        url = self.storage.get_url_by_id(args.id)
        if not url:
            print(f"URL not found: {args.id}")
            return

        if args.name:
            url.name = args.name
        if args.url:
            url.url = args.url
        if args.group is not None:
            url.group_id = args.group
        if args.enable is not None:
            url.enabled = args.enable

        url.updated_at = datetime.now().isoformat()
        self.storage.update_url(url)
        print(f"Updated URL: {url.name}")

    def delete_url(self, args):
        if not args.id:
            print("Error: --id is required")
            return
        self.storage.delete_url(args.id)
        print(f"Deleted URL: {args.id}")

    def open_url(self, args):
        if args.id:
            url = self.storage.get_url_by_id(args.id)
            if url:
                self.launcher.open_url(url.url)
                print(f"Opened: {url.name}")
            else:
                print(f"URL not found: {args.id}")
        else:
            self.open_all()

    def handle_schedule(self, args):
        if args.subcommand == 'list':
            self.list_schedules()
        elif args.subcommand == 'add':
            self.add_schedule(args)
        elif args.subcommand == 'edit':
            self.edit_schedule(args)
        elif args.subcommand == 'delete':
            self.delete_schedule(args)
        elif args.subcommand == 'run':
            self.run_schedule(args)
        elif args.subcommand == 'enable':
            self.toggle_schedule(args, True)
        elif args.subcommand == 'disable':
            self.toggle_schedule(args, False)

    def list_schedules(self):
        schedules = self.storage.schedules
        if not schedules:
            print("No schedules found.")
            return

        print(f"\n{'ID':<8} {'Name':<20} {'Trigger':<15} {'Next Execution':<20} {'Enabled':<10}")
        print("-" * 85)
        for s in schedules:
            status = "✓" if s.enabled else "✗"
            next_exec = s.next_execution[:16] if s.next_execution else "N/A"
            print(f"{s.id[:8]:<8} {s.name:<20} {s.trigger_type:<15} {next_exec:<20} {status:<10}")

    def add_schedule(self, args):
        if not args.name or not args.urls:
            print("Error: --name and --urls are required")
            return

        url_ids = args.urls.split(',')
        schedule = Schedule.create(
            name=args.name,
            url_ids=url_ids,
            trigger_type=args.type or TriggerType.DAILY.value,
            trigger_value=args.time or "09:00",
            week_days=args.days.split(',') if args.days else [1, 2, 3, 4, 5]
        )
        self.storage.add_schedule(schedule)
        print(f"Added schedule: {schedule.name} ({schedule.id[:8]})")

    def edit_schedule(self, args):
        if not args.id:
            print("Error: --id is required")
            return

        schedule = self.storage.get_schedule_by_id(args.id)
        if not schedule:
            print(f"Schedule not found: {args.id}")
            return

        if args.name:
            schedule.name = args.name
        if args.urls:
            schedule.url_ids = args.urls.split(',')
        if args.time:
            schedule.trigger_value = args.time
        if args.type:
            schedule.trigger_type = args.type

        schedule.updated_at = datetime.now().isoformat()
        self.storage.update_schedule(schedule)
        print(f"Updated schedule: {schedule.name}")

    def delete_schedule(self, args):
        if not args.id:
            print("Error: --id is required")
            return
        self.storage.delete_schedule(args.id)
        print(f"Deleted schedule: {args.id}")

    def run_schedule(self, args):
        if not args.id:
            print("Error: --id is required")
            return

        schedule = self.storage.get_schedule_by_id(args.id)
        if not schedule:
            print(f"Schedule not found: {args.id}")
            return

        self.scheduler.execute_now(schedule)
        print(f"Executed schedule: {schedule.name}")

    def toggle_schedule(self, args, enabled: bool):
        if not args.id:
            print("Error: --id is required")
            return

        schedule = self.storage.get_schedule_by_id(args.id)
        if not schedule:
            print(f"Schedule not found: {args.id}")
            return

        schedule.enabled = enabled
        schedule.updated_at = datetime.now().isoformat()
        self.storage.update_schedule(schedule)
        status = "enabled" if enabled else "disabled"
        print(f"Schedule {status}: {schedule.name}")

    def handle_group(self, args):
        if args.subcommand == 'list':
            self.list_groups()
        elif args.subcommand == 'add':
            self.add_group(args)
        elif args.subcommand == 'delete':
            self.delete_group(args)

    def list_groups(self):
        groups = self.storage.groups
        if not groups:
            print("No groups found.")
            return

        print(f"\n{'ID':<8} {'Name':<20} {'Color':<10}")
        print("-" * 40)
        for g in groups:
            print(f"{g.id[:8]:<8} {g.name:<20} {g.color_hex:<10}")

    def add_group(self, args):
        if not args.name:
            print("Error: --name is required")
            return

        group = URLGroup.create(name=args.name, color_hex=args.color or "#007AFF")
        self.storage.add_group(group)
        print(f"Added group: {group.name} ({group.id[:8]})")

    def delete_group(self, args):
        if not args.id:
            print("Error: --id is required")
            return
        self.storage.delete_group(args.id)
        print(f"Deleted group: {args.id}")

    def start_daemon(self):
        print("Starting AutoURL daemon...")
        self.scheduler.start()
        print("Daemon started. Press Ctrl+C to stop.")

        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping daemon...")
            self.scheduler.stop()
            print("Daemon stopped.")

    def open_all(self):
        urls = [u for u in self.storage.urls if u.enabled]
        if urls:
            self.launcher.open_urls(urls, new_window=True)
            print(f"Opened {len(urls)} URLs")
        else:
            print("No enabled URLs.")


def create_parser():
    parser = argparse.ArgumentParser(prog='autourl', description='AutoURL - 定时打开网址工具')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    url_parser = subparsers.add_parser('url', help='Manage URLs')
    url_subparsers = url_parser.add_subparsers(dest='subcommand', help='URL commands')

    list_url = url_subparsers.add_parser('list', help='List all URLs')
    add_url = url_subparsers.add_parser('add', help='Add a URL')
    add_url.add_argument('--name', required=True, help='URL name')
    add_url.add_argument('--url', required=True, help='URL address')
    add_url.add_argument('--group', help='Group ID')

    edit_url = url_subparsers.add_parser('edit', help='Edit a URL')
    edit_url.add_argument('--id', required=True, help='URL ID')
    edit_url.add_argument('--name', help='URL name')
    edit_url.add_argument('--url', help='URL address')
    edit_url.add_argument('--group', help='Group ID')
    edit_url.add_argument('--enable', type=bool, help='Enable/disable')

    delete_url = url_subparsers.add_parser('delete', help='Delete a URL')
    delete_url.add_argument('--id', required=True, help='URL ID')

    open_url = url_subparsers.add_parser('open', help='Open URL(s)')
    open_url.add_argument('--id', help='URL ID (optional, opens all if not specified)')

    schedule_parser = subparsers.add_parser('schedule', help='Manage schedules')
    schedule_subparsers = schedule_parser.add_subparsers(dest='subcommand', help='Schedule commands')

    list_schedule = schedule_subparsers.add_parser('list', help='List all schedules')

    add_schedule = schedule_subparsers.add_parser('add', help='Add a schedule')
    add_schedule.add_argument('--name', required=True, help='Schedule name')
    add_schedule.add_argument('--urls', required=True, help='Comma-separated URL IDs')
    add_schedule.add_argument('--type', choices=['once', 'daily', 'weekly', 'custom'], help='Trigger type')
    add_schedule.add_argument('--time', help='Time (HH:MM for daily/weekly, Y-m-d H:M for once)')
    add_schedule.add_argument('--days', help='Comma-separated weekdays (1-7)')

    edit_schedule = schedule_subparsers.add_parser('edit', help='Edit a schedule')
    edit_schedule.add_argument('--id', required=True, help='Schedule ID')
    edit_schedule.add_argument('--name', help='Schedule name')
    edit_schedule.add_argument('--urls', help='Comma-separated URL IDs')
    edit_schedule.add_argument('--time', help='Time')
    edit_schedule.add_argument('--type', help='Trigger type')

    delete_schedule = schedule_subparsers.add_parser('delete', help='Delete a schedule')
    delete_schedule.add_argument('--id', required=True, help='Schedule ID')

    run_schedule = schedule_subparsers.add_parser('run', help='Run a schedule now')
    run_schedule.add_argument('--id', required=True, help='Schedule ID')

    enable_schedule = schedule_subparsers.add_parser('enable', help='Enable a schedule')
    enable_schedule.add_argument('--id', required=True, help='Schedule ID')

    disable_schedule = schedule_subparsers.add_parser('disable', help='Disable a schedule')
    disable_schedule.add_argument('--id', required=True, help='Schedule ID')

    group_parser = subparsers.add_parser('group', help='Manage groups')
    group_subparsers = group_parser.add_subparsers(dest='subcommand', help='Group commands')

    list_group = group_subparsers.add_parser('list', help='List all groups')

    add_group = group_subparsers.add_parser('add', help='Add a group')
    add_group.add_argument('--name', required=True, help='Group name')
    add_group.add_argument('--color', help='Color hex code')

    delete_group = group_subparsers.add_parser('delete', help='Delete a group')
    delete_group.add_argument('--id', required=True, help='Group ID')

    subparsers.add_parser('start', help='Start the daemon')
    subparsers.add_parser('open', help='Open all enabled URLs')

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    sync_config_if_needed()

    cli = CLI()
    cli.run(args)


if __name__ == '__main__':
    main()
