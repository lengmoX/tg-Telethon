#!/bin/bash
#
# TGF 安装脚本
# 适用于 Debian/Ubuntu 系统
#
# 使用方法:
#   curl -fsSL https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | bash
#   或
#   wget -qO- https://raw.githubusercontent.com/lengmoX/tg-Telethon/master/install.sh | bash
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
GITHUB_REPO="lengmoX/tg-Telethon"
INSTALL_DIR="/usr/local/bin"
TGF_BIN="$INSTALL_DIR/tgf"
TGF_DATA_DIR="$HOME/.tgf"

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
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 获取最新版本号
get_latest_version() {
    curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/'
}

# 获取当前安装版本
get_current_version() {
    if [ -f "$TGF_BIN" ]; then
        $TGF_BIN --version 2>/dev/null | head -1 || echo "unknown"
    else
        echo "not installed"
    fi
}

# 下载并安装
install_tgf() {
    print_info "正在获取最新版本..."
    
    local version=$(get_latest_version)
    if [ -z "$version" ]; then
        print_error "无法获取最新版本"
        exit 1
    fi
    
    print_info "最新版本: $version"
    
    # 下载 artifact (从 GitHub Actions)
    local download_url="https://github.com/$GITHUB_REPO/releases/download/$version/tgf-linux"
    
    # 如果没有 release，尝试从 GitHub Actions artifact 下载
    # 注意: GitHub Actions artifacts 需要认证，这里使用 releases
    
    print_info "正在下载..."
    
    # 创建临时目录
    local tmp_dir=$(mktemp -d)
    local tmp_file="$tmp_dir/tgf"
    
    # 尝试下载
    if ! curl -fsSL -o "$tmp_file" "$download_url" 2>/dev/null; then
        print_warning "Release 下载失败，尝试从 Actions artifact..."
        
        # 备选: 直接从最新 workflow run 获取
        # 这需要 GitHub API，这里简化处理
        print_error "请手动下载: https://github.com/$GITHUB_REPO/actions"
        print_info "下载后执行: sudo cp tgf /usr/local/bin/ && sudo chmod +x /usr/local/bin/tgf"
        rm -rf "$tmp_dir"
        exit 1
    fi
    
    # 安装
    chmod +x "$tmp_file"
    mv "$tmp_file" "$TGF_BIN"
    
    # 清理
    rm -rf "$tmp_dir"
    
    # 创建数据目录
    mkdir -p "$TGF_DATA_DIR"
    
    print_success "TGF 安装成功!"
    print_info "安装位置: $TGF_BIN"
    print_info "数据目录: $TGF_DATA_DIR"
    echo ""
    print_info "使用方法:"
    echo "  tgf --help           # 查看帮助"
    echo "  tgf login            # 登录"
    echo "  tgf rule add ...     # 添加规则"
}

# 更新
update_tgf() {
    if [ ! -f "$TGF_BIN" ]; then
        print_error "TGF 未安装，请先安装"
        exit 1
    fi
    
    local current=$(get_current_version)
    local latest=$(get_latest_version)
    
    print_info "当前版本: $current"
    print_info "最新版本: $latest"
    
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
    
    # 删除可执行文件
    if [ -f "$TGF_BIN" ]; then
        rm -f "$TGF_BIN"
        print_success "已删除: $TGF_BIN"
    else
        print_info "可执行文件不存在"
    fi
    
    # 询问是否删除数据
    echo ""
    read -p "是否删除数据目录 $TGF_DATA_DIR? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$TGF_DATA_DIR"
        print_success "已删除数据目录"
    else
        print_info "保留数据目录"
    fi
    
    print_success "TGF 已卸载"
}

# 显示菜单
show_menu() {
    clear
    echo "================================================"
    echo -e "${BLUE}       TGF - Telegram Forwarder 安装器${NC}"
    echo "================================================"
    echo ""
    echo "  当前状态: $(get_current_version)"
    echo ""
    echo "  1) 安装 TGF"
    echo "  2) 更新 TGF"
    echo "  3) 卸载 TGF"
    echo "  0) 退出"
    echo ""
    echo "================================================"
}

# 主函数
main() {
    # 如果有参数，直接执行
    case "${1:-}" in
        install)
            check_root
            install_tgf
            exit 0
            ;;
        update)
            check_root
            update_tgf
            exit 0
            ;;
        uninstall)
            check_root
            uninstall_tgf
            exit 0
            ;;
    esac
    
    # 交互式菜单
    while true; do
        show_menu
        read -p "请选择 [0-3]: " choice
        
        case $choice in
            1)
                check_root
                install_tgf
                read -p "按回车键继续..."
                ;;
            2)
                check_root
                update_tgf
                read -p "按回车键继续..."
                ;;
            3)
                check_root
                uninstall_tgf
                read -p "按回车键继续..."
                ;;
            0)
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

main "$@"
