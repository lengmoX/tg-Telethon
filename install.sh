#!/bin/bash
#
# TGF 安装脚本
# 适用于 Debian/Ubuntu/CentOS 等 Linux 系统
#
# 使用方法:
#   wget -qO install.sh https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh && bash install.sh
#   或直接下载后运行:
#   bash install.sh
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
INSTALL_DIR="/usr/local/bin"
TGF_BIN="$INSTALL_DIR/tgf"

# 获取实际用户（即使用 sudo 运行）
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
TGF_DATA_DIR="$REAL_HOME/.tgf"

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
        print_info "例如: sudo bash install.sh"
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
        print_info "请先安装: apt install$missing 或 yum install$missing"
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
    
    # 创建临时目录
    local tmp_dir
    tmp_dir=$(mktemp -d)
    local tmp_file="$tmp_dir/tgf"
    
    # 下载
    if ! curl -fsSL -o "$tmp_file" "$download_url" 2>/dev/null; then
        print_error "下载失败"
        echo ""
        print_info "可能的原因:"
        print_info "  1. 版本 $version 尚未发布可执行文件"
        print_info "  2. 网络连接问题"
        echo ""
        print_info "手动下载地址: https://github.com/$GITHUB_REPO/releases"
        print_info "手动安装命令: cp tgf-linux /usr/local/bin/tgf && chmod +x /usr/local/bin/tgf"
        rm -rf "$tmp_dir"
        exit 1
    fi
    
    # 验证下载的文件
    if [ ! -s "$tmp_file" ]; then
        print_error "下载的文件为空"
        rm -rf "$tmp_dir"
        exit 1
    fi
    
    # 安装
    chmod +x "$tmp_file"
    mv "$tmp_file" "$TGF_BIN"
    
    # 清理
    rm -rf "$tmp_dir"
    
    # 创建数据目录（使用实际用户权限）
    if [ -n "$SUDO_USER" ]; then
        sudo -u "$SUDO_USER" mkdir -p "$TGF_DATA_DIR"
    else
        mkdir -p "$TGF_DATA_DIR"
    fi
    
    echo ""
    print_success "TGF 安装成功!"
    echo ""
    echo -e "  ${CYAN}安装位置${NC}: $TGF_BIN"
    echo -e "  ${CYAN}数据目录${NC}: $TGF_DATA_DIR"
    echo ""
    echo -e "${YELLOW}下一步:${NC}"
    echo "  1. 创建配置文件: $TGF_DATA_DIR/.env"
    echo "     内容:"
    echo "       TGF_API_ID=你的API_ID"
    echo "       TGF_API_HASH=你的API_HASH"
    echo ""
    echo "  2. 登录: tgf login"
    echo ""
    echo -e "${CYAN}获取 API 凭证:${NC} https://my.telegram.org"
}

# 更新
update_tgf() {
    if [ ! -f "$TGF_BIN" ]; then
        print_error "TGF 未安装，请先安装"
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
    install_tgf
}

# 卸载
uninstall_tgf() {
    print_warning "即将卸载 TGF..."
    echo ""
    
    # 删除可执行文件
    if [ -f "$TGF_BIN" ]; then
        rm -f "$TGF_BIN"
        print_success "已删除: $TGF_BIN"
    else
        print_info "可执行文件不存在"
    fi
    
    # 询问是否删除数据
    echo ""
    if [ -d "$TGF_DATA_DIR" ]; then
        echo -n "是否删除数据目录 $TGF_DATA_DIR? [y/N] "
        read -r answer </dev/tty
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            rm -rf "$TGF_DATA_DIR"
            print_success "已删除数据目录"
        else
            print_info "保留数据目录"
        fi
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
    echo "TGF 安装脚本"
    echo ""
    echo "用法: bash $0 [command]"
    echo ""
    echo "命令:"
    echo "  install    直接安装 TGF"
    echo "  update     更新 TGF"
    echo "  uninstall  卸载 TGF"
    echo "  menu       显示交互式菜单"
    echo ""
    echo "如果不带参数运行，将显示交互式菜单"
}

# 主函数
main() {
    # 如果有参数，使用非交互模式
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
            # 无参数时显示交互式菜单
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
