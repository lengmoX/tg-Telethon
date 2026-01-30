# TGF - Telegram 消息转发 CLI 工具

基于 Python 和 Telethon 的 Telegram 频道/群组消息转发命令行工具。

## 功能特性

- **QR 码登录**：无需输入手机号，使用 Telegram App 扫码即可登录
- **多账号支持**：通过 `-n/--namespace` 管理多个账号
- **两种转发模式**：
  - `clone`：复制消息内容，无"转发自"标签（默认）
  - `direct`：原生转发，带"转发自"标签
- **定时监听**：监控频道并自动转发新消息
- **增量同步**：基于消息 ID 锚点，避免重复转发
- **智能降级**：受限频道自动下载后重新上传

## 安装

```bash
# 进入项目目录
cd d:\develop\PythonProject\tg-Telethon

# 开发模式安装
pip install -e .

# 或仅安装依赖
pip install -r requirements.txt
```

## 配置

1. 从 https://my.telegram.org 获取 API 凭证

2. 复制配置模板并填写：

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API 凭证
```

`.env` 文件内容示例：
```ini
TGF_API_ID=12345678
TGF_API_HASH=abcdef1234567890abcdef1234567890
```

可选配置项：
- `TGF_DATA_DIR`：自定义数据目录（默认：`~/.tgf`）
- `TGF_NAMESPACE`：默认命名空间（默认：`default`）
- `TGF_LOG_LEVEL`：日志级别（默认：`INFO`）

## 快速开始

### 登录

```bash
# QR 码登录
tgf login

# 使用其他账号登录
tgf -n work login
```

### 手动转发

```bash
# 转发到"已保存的消息"
tgf forward -s @channel -t me --limit 10

# 使用原生转发模式
tgf forward -s @source -t @target --mode direct

# 预览模式（不实际转发）
tgf forward -s @channel -t me --dry-run
```

### 规则管理

```bash
# 添加规则
tgf rule add --name news -s @telegram -t me --interval 30

# 列出所有规则
tgf rule list

# 查看规则详情
tgf rule show news

# 编辑规则
tgf rule edit news --interval 60

# 禁用/启用规则
tgf rule edit news --disable
tgf rule edit news --enable

# 删除规则
tgf rule remove news
```

### 监听模式

```bash
# 监听所有启用的规则
tgf watch

# 监听特定规则
tgf watch news

# 同步一次后退出
tgf watch --once

# 查看状态
tgf status
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `tgf login` | QR 码登录 |
| `tgf logout` | 登出并删除会话 |
| `tgf chat ls` | 列出所有对话 |
| `tgf chat export` | 导出消息到 JSON |
| `tgf forward` | 手动转发消息 |
| `tgf rule add` | 添加转发规则 |
| `tgf rule list` | 列出所有规则 |
| `tgf rule show` | 查看规则详情 |
| `tgf rule edit` | 编辑规则 |
| `tgf rule remove` | 删除规则 |
| `tgf watch` | 启动监听模式 |
| `tgf status` | 查看同步状态 |
| `tgf info` | 显示配置信息 |

### 全局选项

| 选项 | 说明 |
|------|------|
| `-n, --namespace NAME` | 账号命名空间（默认：default） |
| `-v, --verbose` | 详细输出模式 |
| `--debug` | 调试模式 |

## 架构

```
tgf/
├── cli/         # CLI 命令层 (Click)
├── service/     # 业务逻辑层
├── core/        # Telegram API 封装层
├── data/        # 数据库和配置层
└── utils/       # 工具函数
```

## 数据存储

所有数据存储在 `~/.tgf/` 目录：
- `sessions/` - Telethon 会话文件
- `logs/` - 日志文件
- `tgf.db` - SQLite 数据库（规则和状态）

## 许可证

MIT
