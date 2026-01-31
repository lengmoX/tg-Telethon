# TGF - Telegram 消息转发 CLI 工具

[![Build](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml/badge.svg)](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml)

基于 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## ✨ 功能特性

- **QR 码登录** - 扫码即可登录，支持两步验证
- **多账号支持** - 通过 `-n/--namespace` 管理多个账号
- **消息过滤** - 关键词、正则表达式过滤
- **定时监听** - 自动转发新消息
- **媒体组转发** - 自动检测并转发整个相册/媒体组
- **完整备份** - 一键导出/恢复所有数据
- **便携模式** - 所有配置和数据存储在安装目录

---

## 📦 安装

### Linux 一键安装（推荐）

```bash
# 创建安装目录并安装（所有配置都在 /opt/tgf 下）
mkdir -p /opt/tgf && cd /opt/tgf
wget -qO- https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | sudo bash -s install
```

安装后目录结构：
```
/opt/tgf/
├── tgf              # 可执行文件
├── .env             # 配置文件（自动创建模板）
├── tgf.db           # 规则数据库
├── sessions/        # 登录会话
└── logs/            # 日志
```

### Windows

1. 从 [Releases](https://github.com/lengmoX/tg-Telethon/releases) 下载 `tgf-windows.exe`
2. 重命名为 `tgf.exe`
3. 放入任意目录，如 `D:\tgf\`
4. 在该目录创建 `.env` 配置文件
5. 运行时，所有数据自动保存在 `tgf.exe` 同目录

### 从源码安装（开发模式）

```bash
git clone https://github.com/lengmoX/tg-Telethon.git
cd tg-Telethon
pip install -e .
```

---

## ⚙️ 配置

### 1. 获取 API 凭证

访问 https://my.telegram.org → API development tools → 创建应用

### 2. 编辑配置文件

**Linux（安装后自动创建模板）：**
```bash
nano /opt/tgf/.env
```

**Windows：** 在 `tgf.exe` 同目录创建 `.env` 文件

**配置内容：**
```ini
TGF_API_ID=12345678
TGF_API_HASH=abcdef1234567890abcdef1234567890
```

### 3. 验证配置

```bash
tgf info
```

---

## 🚀 快速开始

```bash
# 1. 检查配置和登录状态
tgf info

# 2. 登录（扫码）
tgf login

# 3. 转发消息
tgf forward --from https://t.me/channel/123 --to me
```

---

## 📋 命令详解

### `tgf forward` - 一次性转发

转发指定的消息（支持媒体组自动检测）：

```bash
# 转发到 Saved Messages（默认）
tgf forward --from https://t.me/channel/123

# 转发到其他频道
tgf forward --from https://t.me/channel/123 --to @mychannel

# 转发多条消息
tgf forward --from https://t.me/ch/1 --from https://t.me/ch/2

# 从 JSON 文件转发
tgf forward --from export.json --to me

# 禁用媒体组检测（只转发单条消息）
tgf forward --from https://t.me/channel/123 --no-group
```

---

### `tgf rule` - 规则管理

规则用于定义自动转发任务。

```bash
# 添加规则（从 @telegram 转发到 Saved Messages，每 30 秒检查一次）
tgf rule add --name news -s @telegram -t me --interval 30

# 添加带过滤器的规则（排除包含 "广告" 或 "推广" 的消息）
tgf rule add --name filtered -s @channel -t me --filter "广告;推广"

# 列出所有规则
tgf rule list

# 查看规则详情
tgf rule show myname

# 禁用规则
tgf rule edit myname --disable

# 启用规则
tgf rule edit myname --enable

# 修改检查间隔
tgf rule edit myname --interval 60

# 删除规则
tgf rule remove myname
```

---

### `tgf watch` - 监听模式 ⭐

**这是主要的自动转发功能**。`watch` 命令会持续运行，按照规则定义的间隔检查新消息并自动转发。

#### 基本用法

```bash
# 前台运行（按 Ctrl+C 停止）
tgf watch

# 后台运行（推荐）
tgf watch -d

# 查看监听状态
tgf status

# 停止后台监听
tgf stop

# 只监听指定规则
tgf watch myname

# 运行一次同步然后退出
tgf watch --once
```

#### 完整工作流程示例

```bash
# 1. 登录
tgf login

# 2. 创建规则：从 @telegram 转发到 Saved Messages，每 60 秒检查一次
tgf rule add --name telegram_news -s @telegram -t me --interval 60

# 3. 查看规则状态
tgf status

# 4. 启动监听（会持续运行）
tgf watch

# 输出示例：
# ✓ Watching all enabled rules
# ✓ Press Ctrl+C to stop
#
# --- Sync cycle complete ---
#   [telegram_news] 3 found, 3 forwarded
#
# --- Sync cycle complete ---
#   [telegram_news] No new messages
```

#### 查看规则状态

```bash
tgf status           # 查看所有规则状态
tgf status myname    # 查看指定规则状态

# 输出包括：
# - 规则名称
# - 来源 → 目标
# - 启用状态
# - 最后消息 ID
# - 已转发数量
# - 最后同步时间
```

#### 后台运行（Linux）

```bash
# 使用 nohup 后台运行
nohup tgf watch > /dev/null 2>&1 &

# 使用 screen
screen -S tgf
tgf watch
# 按 Ctrl+A+D 脱离

# 使用 systemd（推荐）
# 参见下方 systemd 配置
```

---

### 其他命令

| 命令 | 说明 |
|------|------|
| `tgf info` | 查看配置和登录状态 |
| `tgf login` | 扫码登录 |
| `tgf chat ls` | 列出对话 |
| `tgf chat export CHAT_ID` | 导出消息到 JSON |
| `tgf filter add/list/remove` | 全局过滤器管理 |
| `tgf backup export` | 导出所有数据 |
| `tgf backup import FILE` | 恢复数据 |

---

## 📁 数据存储

### 便携模式（默认）

| 平台 | 数据位置 |
|------|----------|
| Linux | 安装目录（如 `/opt/tgf/`） |
| Windows | `tgf.exe` 同目录 |

### 环境变量覆盖

```bash
export TGF_DATA_DIR=/custom/path
tgf info
```

---

## 🔧 Systemd 服务配置（Linux）

创建服务文件 `/etc/systemd/system/tgf.service`：

```ini
[Unit]
Description=TGF Telegram Forwarder
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tgf
ExecStart=/opt/tgf/tgf watch
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgf
sudo systemctl start tgf
sudo systemctl status tgf
```

---

## ❓ 常见问题

### "API credentials not configured" 错误

运行 `tgf info` 查看当前配置状态，确保 `.env` 文件在正确位置。

### Linux 如何更新？

```bash
cd /opt/tgf
sudo bash install.sh update
```

### 多账号使用

```bash
tgf -n account1 login
tgf -n account2 login
tgf -n account1 watch
```

### 转发限制频道的内容

程序会自动检测受限频道，下载后重新上传。视频、图片等媒体会保留原始格式和属性。

### 媒体组（相册）如何转发？

程序默认自动检测媒体组并整体转发。如需禁用，使用 `--no-group`：

```bash
tgf forward --from https://t.me/channel/123 --no-group
```

---

## 📄 许可证

MIT License
