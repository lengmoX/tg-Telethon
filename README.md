# TGF - Telegram 消息转发 CLI 工具

[![Build](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml/badge.svg)](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## ✨ 功能特性

- **QR 码登录** - 无需输入手机号，支持两步验证
- **多账号支持** - 通过 `-n/--namespace` 管理多个账号
- **消息过滤** - 关键词、正则表达式过滤
- **定时监听** - 自动转发新消息
- **完整备份** - 一键导出/恢复所有数据

## 📦 安装

### Linux 一键安装

```bash
wget -qO- https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | sudo bash -s install
```

### 手动下载

从 [Releases](https://github.com/lengmoX/tg-Telethon/releases) 下载：

| 平台 | 文件 |
|------|------|
| Linux | `tgf-linux` |
| Windows | `tgf-windows.exe` |

```bash
# Linux
chmod +x tgf-linux
sudo mv tgf-linux /usr/local/bin/tgf
```

### 从源码安装

```bash
git clone https://github.com/lengmoX/tg-Telethon.git
cd tg-Telethon
pip install -e .
```

## ⚙️ 配置

1. 获取 API 凭证：https://my.telegram.org

2. 创建配置文件 `~/.tgf/.env`：

```bash
mkdir -p ~/.tgf
cat > ~/.tgf/.env << EOF
TGF_API_ID=你的API_ID
TGF_API_HASH=你的API_HASH
EOF
```

## 🚀 快速开始

```bash
# 登录
tgf login

# 转发消息
tgf forward --from https://t.me/channel/123 --to me

# 添加规则
tgf rule add --name news -s @telegram -t me

# 监听模式
tgf watch
```

## 📋 命令一览

| 命令 | 说明 |
|------|------|
| `tgf login` | 登录 |
| `tgf forward --from URL --to CHAT` | 转发消息 |
| `tgf rule add/list/edit/remove` | 规则管理 |
| `tgf filter add/list/remove` | 过滤器 |
| `tgf backup export/import` | 备份恢复 |
| `tgf watch` | 监听模式 |
| `tgf chat ls` | 列出对话 |

## 📄 许可证

MIT License
