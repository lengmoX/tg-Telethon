# TGF - Telegram 消息转发 CLI 工具

[![Build](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml/badge.svg)](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 Python 和 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## ✨ 功能特性

- **QR 码登录**：无需输入手机号，支持两步验证
- **多账号支持**：通过 `-n/--namespace` 管理多个账号
- **两种转发模式**：
  - `clone`：复制消息内容，无"转发自"标签（默认）
  - `direct`：原生转发，带"转发自"标签
- **消息过滤**：支持关键词、正则表达式过滤
- **定时监听**：监控频道并自动转发新消息
- **完整备份**：导出/恢复所有数据，支持跨设备迁移

## 📦 安装

### Linux 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | sudo bash
```

### 手动下载

从 [Releases](https://github.com/lengmoX/tg-Telethon/releases) 下载对应平台的可执行文件：

- **Linux**: `tgf-linux`
- **Windows**: `tgf-windows.exe`

### 从源码安装

```bash
git clone https://github.com/lengmoX/tg-Telethon.git
cd tg-Telethon
pip install -e .
```

## ⚙️ 配置

1. 从 https://my.telegram.org 获取 API 凭证

2. 创建 `.env` 文件（与程序同目录）：

```env
TGF_API_ID=12345678
TGF_API_HASH=abcdef1234567890abcdef1234567890
```

可选配置：
| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TGF_DATA_DIR` | 数据目录 | `~/.tgf` 或 `./tgf_data` |
| `TGF_NAMESPACE` | 默认命名空间 | `default` |
| `TGF_LOG_LEVEL` | 日志级别 | `INFO` |

## 🚀 快速开始

### 登录

```bash
tgf login            # QR 码登录
tgf -n work login    # 多账号登录
```

### 转发消息

```bash
# 转发到 "已保存的消息"
tgf forward --from https://t.me/durov/1

# 转发到指定频道
tgf forward --from https://t.me/channel/123 --to @mychannel

# 转发多条消息
tgf forward --from https://t.me/ch/1 --from https://t.me/ch/2

# 原生转发模式
tgf forward --from https://t.me/channel/123 --mode direct
```

### 规则管理

```bash
# 添加规则
tgf rule add --name news -s @telegram -t me --interval 30

# 添加带过滤器的规则
tgf rule add --name clean -s @source -t @target --filter "广告;推广;!重要"

# 列出/编辑/删除规则
tgf rule list
tgf rule edit news --interval 60
tgf rule remove news
```

### 消息过滤

```bash
# 添加全局过滤器
tgf filter add "广告" --action exclude
tgf filter add "重要" --action include

# 测试过滤效果
tgf filter test "这是一条包含广告的消息"
```

### 监听模式

```bash
tgf watch           # 监听所有规则
tgf watch news      # 监听指定规则
tgf watch --once    # 同步一次后退出
```

### 备份与恢复

```bash
# 完整备份（包含会话、数据库、配置）
tgf backup export

# 恢复备份
tgf backup import backup.zip

# 查看备份内容
tgf backup list backup.zip
```

## 📋 命令参考

| 命令 | 说明 |
|------|------|
| `tgf login` | QR 码登录 |
| `tgf logout` | 登出并删除会话 |
| `tgf chat ls` | 列出所有对话 |
| `tgf chat export` | 导出消息到 JSON |
| `tgf forward` | 手动转发消息 |
| `tgf rule add/list/edit/remove` | 规则管理 |
| `tgf filter add/list/remove/test` | 过滤器管理 |
| `tgf backup export/import/list` | 备份与恢复 |
| `tgf watch` | 启动监听模式 |
| `tgf status` | 查看同步状态 |
| `tgf info` | 显示配置信息 |

### 全局选项

| 选项 | 说明 |
|------|------|
| `-n, --namespace NAME` | 账号命名空间 |
| `-v, --verbose` | 详细输出 |
| `--debug` | 调试模式 |

## 📁 数据存储

| 文件/目录 | 说明 |
|-----------|------|
| `sessions/` | Telethon 会话文件 |
| `logs/` | 日志文件 |
| `tgf.db` | SQLite 数据库 |
| `.env` | 配置文件 |

**便携模式**：打包后的可执行文件会在同目录创建 `tgf_data/` 存储所有数据。

## 🏗️ 架构

```
tgf/
├── cli/         # CLI 命令层 (Click)
├── service/     # 业务逻辑层
├── core/        # Telegram API 封装层
├── data/        # 数据库和配置层
└── utils/       # 工具函数
```

## 📄 许可证

MIT License
