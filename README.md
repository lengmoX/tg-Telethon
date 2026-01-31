# TGF - Telegram 消息转发 CLI 工具

[![Build](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml/badge.svg)](https://github.com/lengmoX/tg-Telethon/actions/workflows/build.yml)

基于 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## ✨ 功能特性

- **QR 码登录** - 扫码即可登录，支持两步验证
- **多账号支持** - 通过 `-n/--namespace` 管理多个账号
- **消息过滤** - 关键词、正则表达式过滤
- **定时监听** - 自动转发新消息
- **完整备份** - 一键导出/恢复所有数据

---

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
# Linux 安装
chmod +x tgf-linux
sudo mv tgf-linux /usr/local/bin/tgf

# Windows: 将 tgf-windows.exe 重命名为 tgf.exe，放入 PATH 目录
```

### 从源码安装

```bash
git clone https://github.com/lengmoX/tg-Telethon.git
cd tg-Telethon
pip install -e .
```

---

## ⚙️ 配置（重要！）

### 1. 获取 API 凭证

访问 https://my.telegram.org：
1. 登录你的 Telegram 账号
2. 点击 "API development tools"
3. 创建应用，获取 `api_id` 和 `api_hash`

### 2. 创建配置文件

**Linux:**
```bash
mkdir -p ~/.tgf
cat > ~/.tgf/.env << 'EOF'
TGF_API_ID=12345678
TGF_API_HASH=abcdef1234567890abcdef1234567890
EOF
```

**Windows (PowerShell):**
```powershell
# 创建目录
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.tgf"

# 创建配置文件
@"
TGF_API_ID=12345678
TGF_API_HASH=abcdef1234567890abcdef1234567890
"@ | Out-File -FilePath "$env:USERPROFILE\.tgf\.env" -Encoding UTF8
```

**或在项目目录创建 `.env` 文件（开发模式）**

### 3. 验证配置

```bash
tgf info
```

输出示例：
```
═══ TGF 状态 ═══

配置信息
  命名空间: default
  数据目录: ~/.tgf
  
API 凭证
  API ID:   已配置 (12345678)
  API Hash: 已配置

登录状态
  会话文件: 不存在
  使用 'tgf login' 登录
```

---

## 🚀 快速开始

### 登录

```bash
# 扫码登录
tgf login

# 多账号登录
tgf -n work login
```

### 检查状态

```bash
# 查看配置和登录状态
tgf info

# 查看同步状态
tgf status
```

### 转发消息

```bash
# 转发到 "已保存的消息"
tgf forward --from https://t.me/channel/123

# 转发到指定频道
tgf forward --from https://t.me/channel/123 --to @mychannel

# 转发多条
tgf forward --from https://t.me/ch/1 --from https://t.me/ch/2
```

### 规则管理

```bash
# 添加规则（每30分钟同步）
tgf rule add --name news -s @telegram -t me --interval 30

# 添加带过滤的规则
tgf rule add --name clean -s @source -t @target --filter "广告;推广"

# 查看规则
tgf rule list
tgf rule show news

# 编辑/删除
tgf rule edit news --interval 60
tgf rule remove news
```

### 消息过滤

```bash
# 添加全局过滤器（排除包含"广告"的消息）
tgf filter add "广告" --action exclude

# 添加包含过滤器（只转发包含"重要"的消息）
tgf filter add "重要" --action include

# 测试过滤效果
tgf filter test "这是一条包含广告的消息"
```

### 监听模式

```bash
# 监听所有规则
tgf watch

# 监听指定规则
tgf watch news

# 同步一次后退出
tgf watch --once
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

---

## 📋 命令参考

| 命令 | 说明 |
|------|------|
| `tgf info` | **查看配置和登录状态** |
| `tgf login` | 扫码登录 |
| `tgf logout` | 登出 |
| `tgf forward` | 转发消息 |
| `tgf rule add/list/edit/remove` | 规则管理 |
| `tgf filter add/list/remove/test` | 过滤器管理 |
| `tgf backup export/import` | 备份恢复 |
| `tgf watch` | 监听模式 |
| `tgf status` | 同步状态 |
| `tgf chat ls` | 列出对话 |

### 全局选项

| 选项 | 说明 |
|------|------|
| `-n, --namespace NAME` | 账号命名空间（默认: default） |
| `-v, --verbose` | 详细输出 |
| `--debug` | 调试模式 |

---

## 📁 数据存储

| 文件/目录 | 说明 |
|-----------|------|
| `.env` | API 凭证配置 |
| `sessions/` | 登录会话文件 |
| `tgf.db` | 规则/过滤器数据库 |
| `logs/` | 日志文件 |

**存储位置：**
- 开发模式：`~/.tgf/`
- 便携模式（打包后）：可执行文件同目录的 `tgf_data/`

---

## ❓ 常见问题

### "API credentials not configured" 错误

配置文件未找到或格式错误。运行 `tgf info` 查看当前状态，按提示创建 `.env` 文件。

### 如何检查登录状态？

```bash
tgf info
```

### 如何多账号使用？

```bash
tgf -n account1 login
tgf -n account2 login
tgf -n account1 chat ls
```

---

## 📄 许可证

MIT License
