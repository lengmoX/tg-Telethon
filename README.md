# TGF - Telegram 消息转发 CLI 工具

[![Build](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml/badge.svg)](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml)

基于 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## ✨ 功能特性

- **QR 码登录** - 扫码即可登录，支持两步验证
- **多账号支持** - 通过 `-n/--namespace` 管理多个账号
- **消息过滤** - 关键词、正则表达式过滤
- **定时监听** - 自动转发新消息
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
# 检查配置和登录状态
tgf info

# 登录（扫码）
tgf login

# 转发消息
tgf forward --from https://t.me/channel/123 --to me

# 添加规则
tgf rule add --name news -s @telegram -t me --interval 30

# 监听模式
tgf watch

# 备份
tgf backup export
```

---

## 📋 命令参考

| 命令 | 说明 |
|------|------|
| `tgf info` | 查看配置和登录状态 |
| `tgf login` | 扫码登录 |
| `tgf forward --from URL` | 转发消息 |
| `tgf rule add/list/edit/remove` | 规则管理 |
| `tgf filter add/list/remove` | 过滤器管理 |
| `tgf backup export/import` | 备份恢复 |
| `tgf watch` | 监听模式 |
| `tgf chat ls` | 列出对话 |

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

---

## 📄 许可证

MIT License
