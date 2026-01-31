#!/bin/bash
#
# TGF 安装脚本
# 适用于 Debian/Ubuntu/CentOS 等 Linux 系统
#
# 便携安装模式：程序和配置都在安装目录下
# 全局命令 tgf 通过符号链接实现
#
# 使用方法:
#   # 安装到 /opt/tgf（推荐）
#   mkdir -p /opt/tgf && cd /opt/tgf
#   wget -qO- https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | sudo bash -s install
#
#   # 或下载后运行
#   wget -O install.sh https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh
#   sudo bash install.sh install
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
GITHUB_REPO="lengmoX/tg-Telethon"
GLOBAL_BIN="/usr/local/bin/tgf"

# 安装目录 = 当前目录
INSTALL_DIR="$(pwd)"
TGF_BIN="$INSTALL_DIR/tgf"

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 sudo 或 root 用户运行此脚本"
        print_info "例如: sudo bash install.sh install"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    local missing=""
    
    if ! command -v curl &> /dev/null; then
        missing+=" curl"
    fi
    
    if [ -n "$missing" ]; then
        print_error "缺少依赖:$missing"
        print_info "请先安装: apt install$missing"
        exit 1
    fi
}

# 获取最新版本号
get_latest_version() {
    local version
    version=$(curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest" 2>/dev/null | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    echo "$version"
}

# 获取当前安装版本
get_current_version() {
    if [ -f "$TGF_BIN" ]; then
        $TGF_BIN --version 2>/dev/null | head -1 || echo "unknown"
    else
        echo "未安装"
    fi
}

# 下载并安装
install_tgf() {
    check_dependencies
    
    print_info "安装目录: $INSTALL_DIR"
    print_info "正在获取最新版本..."
    
    local version
    version=$(get_latest_version)
    
    if [ -z "$version" ]; then
        print_error "无法获取最新版本，请检查网络连接"
        exit 1
    fi
    
    print_info "最新版本: $version"
    
    # 下载 URL
    local download_url="https://github.com/$GITHUB_REPO/releases/download/$version/tgf-linux"
    
    print_info "正在下载..."
    
    # 下载到当前目录
    if ! curl -fsSL -o "$TGF_BIN" "$download_url" 2>/dev/null; then
        print_error "下载失败"
        echo ""
        print_info "手动下载地址: https://github.com/$GITHUB_REPO/releases"
        exit 1
    fi
    
    # 验证下载的文件
    if [ ! -s "$TGF_BIN" ]; then
        print_error "下载的文件为空"
        exit 1
    fi
    
    # 设置权限
    chmod +x "$TGF_BIN"
    
    # 创建全局符号链接
    if [ -L "$GLOBAL_BIN" ]; then
        rm -f "$GLOBAL_BIN"
    elif [ -f "$GLOBAL_BIN" ]; then
        print_warning "已存在全局 tgf 命令，将覆盖"
        rm -f "$GLOBAL_BIN"
    fi
    ln -s "$TGF_BIN" "$GLOBAL_BIN"
    
    # 创建子目录
    mkdir -p "$INSTALL_DIR/sessions"
    mkdir -p "$INSTALL_DIR/logs"
    
    # 如果 .env 不存在，创建模板
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        cat > "$INSTALL_DIR/.env" << 'EOF'
# TGF 配置文件
# 从 https://my.telegram.org 获取 API 凭证

TGF_API_ID=你的API_ID
TGF_API_HASH=你的API_HASH
EOF
        print_info "已创建配置模板: $INSTALL_DIR/.env"
    fi
    
    echo ""
    print_success "TGF 安装成功!"
    echo ""
    echo -e "  ${CYAN}安装目录${NC}: $INSTALL_DIR"
    echo -e "  ${CYAN}可执行文件${NC}: $TGF_BIN"
    echo -e "  ${CYAN}全局命令${NC}: $GLOBAL_BIN -> $TGF_BIN"
    echo ""
    echo -e "${YELLOW}下一步:${NC}"
    echo "  1. 编辑配置文件: nano $INSTALL_DIR/.env"
    echo "     填入你的 API_ID 和 API_HASH"
    echo ""
    echo "  2. 登录: tgf login"
    echo ""
    echo -e "${CYAN}获取 API 凭证:${NC} https://my.telegram.org"
}

# 更新
update_tgf() {
    if [ ! -f "$TGF_BIN" ]; then
        print_error "TGF 未安装在当前目录"
        print_info "请先 cd 到安装目录后再运行"
        exit 1
    fi
    
    check_dependencies
    
    local current latest
    current=$(get_current_version)
    latest=$(get_latest_version)
    
    print_info "当前版本: $current"
    print_info "最新版本: $latest"
    
    if [ -z "$latest" ]; then
        print_error "无法获取最新版本"
        exit 1
    fi
    
    if [ "$current" = "$latest" ]; then
        print_success "已是最新版本"
        return
    fi
    
    print_info "正在更新..."
    
    # 下载新版本
    local download_url="https://github.com/$GITHUB_REPO/releases/download/$latest/tgf-linux"
    if ! curl -fsSL -o "$TGF_BIN.new" "$download_url" 2>/dev/null; then
        print_error "下载失败"
        exit 1
    fi
    
    chmod +x "$TGF_BIN.new"
    mv "$TGF_BIN.new" "$TGF_BIN"
    
    print_success "更新完成!"
}

# 卸载
uninstall_tgf() {
    print_warning "即将卸载 TGF..."
    echo ""
    
    # 删除全局符号链接
    if [ -L "$GLOBAL_BIN" ]; then
        rm -f "$GLOBAL_BIN"
        print_success "已删除全局命令: $GLOBAL_BIN"
    fi
    
    # 删除可执行文件
    if [ -f "$TGF_BIN" ]; then
        rm -f "$TGF_BIN"
        print_success "已删除: $TGF_BIN"
    fi
    
    # 询问是否删除数据
    echo ""
    echo -n "是否删除所有数据 (sessions, logs, db)? [y/N] "
    read -r answer </dev/tty
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR/sessions"
        rm -rf "$INSTALL_DIR/logs"
        rm -f "$INSTALL_DIR/tgf.db"
        rm -f "$INSTALL_DIR/.env"
        print_success "已删除所有数据"
    else
        print_info "保留数据文件"
    fi
    
    echo ""
    print_success "TGF 已卸载"
}

# 显示菜单
show_menu() {
    clear
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}     ${BLUE}TGF - Telegram Forwarder 安装器${NC}        ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  安装目录: ${GREEN}$INSTALL_DIR${NC}"
    echo -e "  当前状态: ${GREEN}$(get_current_version)${NC}"
    echo ""
    echo "  1) 安装 TGF"
    echo "  2) 更新 TGF"
    echo "  3) 卸载 TGF"
    echo "  0) 退出"
    echo ""
}

# 等待按键
wait_key() {
    echo ""
    echo -n "按回车键继续..."
    read -r </dev/tty
}

# 交互式菜单
interactive_menu() {
    check_root
    
    while true; do
        show_menu
        echo -n "请选择 [0-3]: "
        read -r choice </dev/tty
        
        case "$choice" in
            1)
                install_tgf
                wait_key
                ;;
            2)
                update_tgf
                wait_key
                ;;
            3)
                uninstall_tgf
                wait_key
                ;;
            0|q|Q)
                echo ""
                echo "再见!"
                exit 0
                ;;
            *)
                print_error "无效选择"
                sleep 1
                ;;
        esac
    done
}

# 显示帮助
show_help() {
    echo "TGF 安装脚本 - 便携安装模式"
    echo ""
    echo "用法: sudo bash $0 [command]"
    echo ""
    echo "命令:"
    echo "  install    安装到当前目录"
    echo "  update     更新当前目录的 TGF"
    echo "  uninstall  卸载"
    echo "  menu       显示交互式菜单"
    echo ""
    echo "示例:"
    echo "  # 安装到 /opt/tgf"
    echo "  mkdir -p /opt/tgf && cd /opt/tgf"
    echo "  sudo bash install.sh install"
    echo ""
    echo "  # 一键安装"
    echo "  mkdir -p /opt/tgf && cd /opt/tgf && wget -qO- https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | sudo bash -s install"
}

# 主函数
main() {
    case "${1:-}" in
        install)
            check_root
            install_tgf
            ;;
        update)
            check_root
            update_tgf
            ;;
        uninstall)
            check_root
            uninstall_tgf
            ;;
        menu)
            interactive_menu
            ;;
        --help|-h|help)
            show_help
            ;;
        "")
            interactive_menu
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
