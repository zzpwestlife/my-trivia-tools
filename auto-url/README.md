# AutoURL

macOS 平台自动化网址打开工具 - 按照预设的时间计划，自动打开用户指定的多个网址。

## 功能特性

- ✅ 网址管理 - 添加、编辑、删除网址，支持分组
- ✅ 定时计划 - 支持单次、每日、每周、自定义 Cron 表达式
- ✅ 自动打开 - 调用系统默认浏览器打开网址
- ✅ 守护进程 - 后台持续运行，定时执行任务
- ✅ macOS 通知 - 任务执行时发送系统通知
- ✅ 日志记录 - 完整的运行日志
- ✅ 配置文件 - 支持 JSON 配置文件管理

## 环境要求

- macOS 10.15+ (Catalina)
- Python 3.8+

## 安装

```bash
cd auto-url
```

## 快速开始

### 方式一：配置文件（推荐）

直接编辑 `config.json` 文件：

```json
{
  "urls": [
    {"name": "Google", "url": "https://www.google.com", "enabled": true},
    {"name": "GitHub", "url": "https://github.com", "enabled": true}
  ],
  "groups": [
    {"name": "work", "color": "#007AFF"}
  ],
  "schedules": [
    {
      "name": "Work Start",
      "url_names": ["Google", "GitHub"],
      "type": "custom",
      "cron": "55 8 * * 1-5",
      "enabled": true
    },
    {
      "name": "Weekly Review",
      "url_names": ["Google"],
      "type": "weekly",
      "time": "17:00",
      "days": "5",
      "enabled": true
    }
  ]
}
```

然后执行重载命令使配置生效：

```bash
make reload
```

### 方式二：命令行

```bash
# 添加网址
python3 autourl.py url add --name "Google" --url "https://google.com"

# 创建定时计划
python3 autourl.py schedule add --name "Morning" --urls "ID1,ID2" --type daily --time "09:00"

# 启动守护进程
python3 autourl.py start
```

## 开机自启与服务管理 (macOS 推荐)

本项目使用 `launchd` 进行后台守护和开机自启。`Makefile` 封装了常用的管理命令：

```bash
make install     # 首次安装并启动服务
make reload      # 修改配置后重载服务 (常用)
make status      # 查看服务运行状态
make logs        # 查看实时日志
make uninstall   # 卸载服务
```

### 手动管理 (如果不使用 Make)

1. **生成配置文件**
   项目根目录下已提供 `com.user.autourl.plist` 模板文件。

2. **安装服务**
   ```bash
   # 复制配置文件到用户 LaunchAgents 目录
   cp com.user.autourl.plist ~/Library/LaunchAgents/

   # 加载服务
   launchctl load ~/Library/LaunchAgents/com.user.autourl.plist
   ```

3. **管理服务**
   ```bash
   # 查看状态
   launchctl list | grep autourl

   # 停止服务
   launchctl unload ~/Library/LaunchAgents/com.user.autourl.plist

   # 查看日志
   tail -f logs/autourl.log
   tail -f logs/autourl.err
   ```

## Makefile 命令速查

```bash
make help        # 查看帮助
make install     # 安装服务
make reload      # 重载配置
make status      # 查看状态
make logs        # 查看日志
make import      # 从 config.json 导入配置
make urls        # 查看所有网址
make schedules   # 查看所有定时计划
make open        # 打开所有启用的网址
make clean       # 清理数据
```

## 配置文件详解

### 网址配置

```json
{
  "name": "显示名称",
  "url": "https://...",
  "enabled": true,
  "group": "分组名"
}
```

### 分组配置

```json
{
  "name": "分组名称",
  "color": "#007AFF"
}
```

### 定时计划配置

**示例 1：每周一到周五 08:55 (Cron 方式)**
```json
{
  "name": "Work Start",
  "url_names": ["Google", "GitHub"],
  "type": "custom",
  "cron": "55 8 * * 1-5",
  "enabled": true
}
```

**示例 2：每周五 17:00 (Weekly 方式)**
```json
{
  "name": "Weekly Review",
  "url_names": ["周报链接"],
  "type": "weekly",
  "time": "17:00",
  "days": "5",
  "enabled": true
}
```

**定时类型 (type):**
| 类型 | 字段 | 示例 |
|------|------|------|
| `once` | `date` | `"2024-01-15 14:00"` |
| `daily` | `time` | `"09:00"` |
| `weekly` | `time`, `days` | `"09:00"`, `"1,2,3,4,5"` |
| `custom` | `cron` | `"0 9 * * 1-5"` |

**Cron 表达式格式:** `分 时 日 月 周`
- `0 9 * * *` - 每天 9:00
- `55 8 * * 1-5` - 每周一到周五 08:55 (工作日)
- `0 18 * * 1,3,5` - 每周一、三、五下午 6:00
- `0 10 * * 6,0` - 每周末上午 10:00 (周六和周日)

## 数据存储

- 配置目录: `./data/`
- 日志目录: `./logs/`

## 许可证

MIT License
