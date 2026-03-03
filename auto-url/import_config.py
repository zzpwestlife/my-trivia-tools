import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import URLItem, URLGroup, Schedule, TriggerType
from src.storage import StorageService
from src.cli import CLI


def load_config(config_path: str = "config.json", force_reload: bool = False):
    storage = StorageService()
    cli = CLI()

    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    name_to_url_id = {}
    alias_map = {}
    updated_count = 0
    added_count = 0

    groups = config.get('groups', [])
    for g in groups:
        group = URLGroup.create(name=g['name'], color_hex=g.get('color', '#007AFF'))
        existing = [gr for gr in storage.groups if gr.name == group.name]
        if existing:
            existing[0].color_hex = group.color_hex
            print(f"更新分组: {group.name}")
            updated_count += 1
        else:
            storage.add_group(group)
            print(f"添加分组: {group.name}")
            added_count += 1

    urls = config.get('urls', [])
    for u in urls:
        url = URLItem.create(name=u['name'], url=u['url'])
        url.enabled = u.get('enabled', True)

        group_name = u.get('group')
        if group_name:
            for grp in storage.groups:
                if grp.name == group_name:
                    url.group_id = grp.id
                    break

        existing = [ur for ur in storage.urls if ur.name == url.name]
        if existing:
            existing[0].url = url.url
            existing[0].enabled = url.enabled
            existing[0].group_id = url.group_id
            print(f"更新网址: {url.name}")
            updated_count += 1
            url = existing[0]
        else:
            storage.add_url(url)
            print(f"添加网址: {url.name}")
            added_count += 1

        name_to_url_id[url.name] = url.id
        if 'alias' in u:
            alias_map[u['alias']] = url.id
        else:
            alias_map[url.name] = url.id

    schedules = config.get('schedules', [])
    for s in schedules:
        # Support both 'alias' (preferred) and 'url_names' (legacy)
        target_names = s.get('alias') or s.get('url_names', [])
        
        url_ids = []
        for name in target_names:
            if name in alias_map:
                url_ids.append(alias_map[name])
            elif name in name_to_url_id:
                url_ids.append(name_to_url_id[name])
            else:
                print(f"警告: 计划 '{s['name']}' 中的网址(或别名) '{name}' 未找到定义")

        if not url_ids:
            print(f"警告: 计划 '{s['name']}' 没有有效的网址，跳过")
            continue

        trigger_value = s.get('time') or s.get('cron') or s.get('date', '09:00')
        week_days_str = s.get('days', '1,2,3,4,5')
        
        week_days = [1,2,3,4,5] # Default
        if week_days_str:
             if isinstance(week_days_str, str):
                 week_days = week_days_str.split(',')
             elif isinstance(week_days_str, list):
                 week_days = week_days_str
             else:
                 week_days = str(week_days_str).split(',')

        schedule = Schedule.create(
            name=s['name'],
            url_ids=url_ids,
            trigger_type=s.get('type', 'daily'),
            trigger_value=trigger_value,
            week_days=week_days
        )
        schedule.enabled = s.get('enabled', True)

        existing = [sc for sc in storage.schedules if sc.name == schedule.name]
        if existing:
            # Only update fields that are explicitly set or calculated
            existing[0].url_ids = schedule.url_ids
            existing[0].trigger_type = schedule.trigger_type
            existing[0].trigger_value = schedule.trigger_value
            existing[0].week_days = schedule.week_days
            existing[0].enabled = schedule.enabled
            
            # Re-calculate next execution because time/type might have changed
            existing[0].calculate_next_execution()
            storage.update_schedule(existing[0])
            
            print(f"更新计划: {schedule.name} (下次执行: {existing[0].next_execution})")
            updated_count += 1
        else:
            schedule.calculate_next_execution()
            storage.add_schedule(schedule)
            print(f"添加计划: {schedule.name} (下次执行: {schedule.next_execution})")
            added_count += 1

    print(f"\n配置导入完成! 新增: {added_count}, 更新: {updated_count}")
    return True


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    force = "--force" in sys.argv or "-f" in sys.argv
    load_config(config_file, force)
