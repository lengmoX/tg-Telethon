# TGF CLI 可执行程序打包指南

## 方法一：PyInstaller（推荐）

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 快速打包

```bash
# 进入项目目录
cd d:\develop\PythonProject\tg-Telethon

# 使用打包脚本（目录模式，启动更快）
python build.py

# 单文件模式（便于分发，但启动较慢）
python build.py --onefile
```

### 手动打包命令

```bash
# Windows 单文件
pyinstaller --onefile --console --name tgf tgf/cli/main.py

# 目录模式（推荐，启动更快）
pyinstaller --onedir --console --name tgf tgf/cli/main.py
```

### 输出位置

- 单文件模式：`dist/tgf.exe` (Windows) 或 `dist/tgf` (Linux)
- 目录模式：`dist/tgf/tgf.exe` 或 `dist/tgf/tgf`

---

## 方法二：使用 Nuitka（更好的性能）

Nuitka 将 Python 编译为 C，性能更好：

```bash
# 安装
pip install nuitka

# 打包
nuitka --standalone --onefile --output-filename=tgf tgf/cli/main.py
```

---

## 跨平台打包注意事项

⚠️ **重要**：PyInstaller 和 Nuitka 只能在当前平台打包该平台的可执行程序。

| 打包平台 | 生成的可执行文件 |
|----------|------------------|
| Windows  | `.exe` 文件      |
| Linux    | Linux 可执行文件 |
| macOS    | macOS 可执行文件 |

### 跨平台打包方案

1. **GitHub Actions**：在不同平台的 CI 环境中分别打包
2. **虚拟机/容器**：使用 WSL (Linux on Windows) 或 Docker
3. **远程服务器**：在目标平台的服务器上打包

---

## GitHub Actions 自动打包

创建 `.github/workflows/build.yml`:

```yaml
name: Build Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pyinstaller
      
      - name: Build
        run: python build.py --onefile
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: tgf-${{ matrix.os }}
          path: dist/tgf*
```

---

## 使用可执行程序

打包后，可执行程序是独立的，不需要安装 Python：

```bash
# Windows
.\tgf.exe login
.\tgf.exe forward --from https://t.me/xxx/1

# Linux
chmod +x ./tgf
./tgf login
./tgf forward --from https://t.me/xxx/1
```

### 添加到 PATH

**Windows (PowerShell)**:
```powershell
# 复制到用户目录
Copy-Item .\dist\tgf.exe $env:USERPROFILE\.local\bin\

# 添加到 PATH（需管理员权限或编辑环境变量）
$env:PATH += ";$env:USERPROFILE\.local\bin"
```

**Linux/macOS**:
```bash
# 复制到 /usr/local/bin
sudo cp ./dist/tgf /usr/local/bin/
sudo chmod +x /usr/local/bin/tgf

# 或复制到用户目录
mkdir -p ~/.local/bin
cp ./dist/tgf ~/.local/bin/
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

---

## 常见问题

### 打包后文件太大？

使用 UPX 压缩：
```bash
pip install pyinstaller-upx
pyinstaller --onefile --upx-dir=/path/to/upx tgf/cli/main.py
```

### 缺少模块？

添加隐藏导入：
```bash
pyinstaller --hidden-import=module_name tgf/cli/main.py
```

### 杀毒软件误报？

这是 PyInstaller 的常见问题，可以：
1. 将程序添加到杀毒软件白名单
2. 对可执行文件进行代码签名
