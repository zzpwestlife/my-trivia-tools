.PHONY: help start stop restart urls add schedules add-schedule open logs clean test import install uninstall status

PYTHON := python3
APP := autourl.py
PLIST := com.user.autourl.plist
PLIST_DEST := $(HOME)/Library/LaunchAgents/$(PLIST)

help:
	@echo "AutoURL - 定时打开网址工具"
	@echo ""
	@echo "常用命令:"
	@echo "  make install        安装并启动服务 (首次使用)"
	@echo "  make reload         修改配置后重载服务 (常用)"
	@echo "  make status         查看服务运行状态"
	@echo "  make logs           查看实时日志"
	@echo ""
	@echo "配置管理:"
	@echo "  make import         从 config.json 导入配置到数据库"
	@echo "  make urls           查看已配置的网址"
	@echo "  make schedules      查看已配置的计划"
	@echo ""
	@echo "其他命令:"
	@echo "  make start          手动启动守护进程 (调试用)"
	@echo "  make open           立即打开所有启用的网址"
	@echo "  make uninstall      卸载服务"
	@echo "  make clean          清理所有数据"

install:
	@echo "安装服务..."
	@cp $(PLIST) $(PLIST_DEST)
	@launchctl load $(PLIST_DEST)
	@echo "服务已启动，使用 'make status' 查看状态"

uninstall:
	@echo "卸载服务..."
	@launchctl unload $(PLIST_DEST) || true
	@rm -f $(PLIST_DEST)
	@echo "服务已卸载"

reload: import
	@echo "重载服务配置..."
	@launchctl unload $(PLIST_DEST)
	@launchctl load $(PLIST_DEST)
	@echo "服务已重启，配置已生效"

status:
	@launchctl list | grep autourl || echo "服务未运行"

start:
	@echo "启动 AutoURL 守护进程..."
	$(PYTHON) $(APP) start

urls:
	$(PYTHON) $(APP) url list

schedules:
	$(PYTHON) $(APP) schedule list

open:
	$(PYTHON) $(APP) open

logs:
	@if [ -d logs ]; then tail -f logs/autourl.log; else echo "暂无日志"; fi

import:
	@echo "从 config.json 导入配置..."
	$(PYTHON) import_config.py

clean:
	@echo "清理数据..."
	@rm -rf data/*.json
	@echo "数据已清理"

test:
	$(PYTHON) -c "from src.models import URLItem, Schedule; print('模块导入成功')"
