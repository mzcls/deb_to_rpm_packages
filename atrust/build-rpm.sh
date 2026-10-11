#!/bin/bash
#-------------------------------------------------------------------------------
# build-rpm.sh
#
# 从深信服官方 aTrust 的 .deb 安装包一键构建 Fedora/RHEL 的 RPM。
# 版本号、架构会自动从 deb 的 control 中读取，升级只需替换 deb 后重新运行。
#
# 用法:
#   ./build-rpm.sh                       # 用同目录下的 aTrustInstaller*.deb
#   ./build-rpm.sh -d aTrust.deb         # 指定 deb 文件
#   ./build-rpm.sh -u https://.../x.deb  # 从 URL 下载 deb
#   ./build-rpm.sh -v 2.5.17.1 -r 2      # 覆盖版本号 / Release
#
# 依赖(Fedora/RHEL): rpm-build, binutils(ar), xz, curl
#-------------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$HERE/rpm-packaging"
TOP="$HERE/rpmbuild"
OUTDIR="$HERE/dist"

DEB="${ATRUST_DEB:-}"
DEB_URL="${ATRUST_DEB_URL:-}"
RELEASE="${ATRUST_RELEASE:-1}"
VER_OVERRIDE="${ATRUST_VERSION:-}"
ARCH_OVERRIDE="${ATRUST_ARCH:-}"
DIST_REQ=""
DIST_GIVEN=0

usage() {
  cat <<EOF
用法: $0 [选项]

选项:
  -d, --deb PATH|URL    deb 文件路径或下载地址 (默认: 同目录 aTrustInstaller*.deb)
  -u, --url URL         从 URL 下载 deb
  -r, --release N       RPM Release 号 (默认 1)
  -v, --version VER     强制版本号 (默认自动从 deb control 读取)
  -a, --arch ARCH       强制 RPM 架构 (默认按 deb 架构自动映射)
  --dist TAG            覆盖发布标签, 如 --dist .fc45; --dist none 表示去掉标签
  -o, --outdir DIR      产物输出目录 (默认 ./dist)
  -h, --help            显示帮助

可用环境变量: ATRUST_DEB / ATRUST_DEB_URL / ATRUST_RELEASE / ATRUST_VERSION / ATRUST_ARCH / ATRUST_DIST
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--deb)     DEB="${2:-}"; shift 2;;
    -u|--url)     DEB_URL="${2:-}"; shift 2;;
    -r|--release) RELEASE="${2:-}"; shift 2;;
    -v|--version) VER_OVERRIDE="${2:-}"; shift 2;;
    -a|--arch)    ARCH_OVERRIDE="${2:-}"; shift 2;;
    --dist)       DIST_REQ="${2:-}"; DIST_GIVEN=1; shift 2;;
    -o|--outdir)  OUTDIR="${2:-}"; shift 2;;
    -h|--help)    usage; exit 0;;
    *) echo "未知参数: $1" >&2; usage; exit 1;;
  esac
done

# ATRUST_DIST: 覆盖发布标签(如 .fc45)；值为 none 表示去掉标签(发行版无关)
if [ "$DIST_GIVEN" = 0 ] && [ -n "${ATRUST_DIST:-}" ]; then
  DIST_REQ="$ATRUST_DIST"
  DIST_GIVEN=1
fi

for cmd in rpmbuild ar xz patchelf; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "错误: 缺少命令 '$cmd'，请先安装: sudo dnf install -y rpm-build binutils xz patchelf" >&2; exit 1; }
done

# --- 检查仓库内的打包文件 ---------------------------------------------------
echo "[*] 脚本目录: $HERE"
missing=0
if [ ! -d "$PKG_DIR/SPECS" ] || ! ls "$PKG_DIR"/SPECS/*.spec >/dev/null 2>&1; then
  echo "错误: 缺少 spec 文件: $PKG_DIR/SPECS/*.spec" >&2
  missing=1
fi
if [ ! -d "$PKG_DIR/helpers" ] || ! ls "$PKG_DIR"/helpers/* >/dev/null 2>&1; then
  echo "错误: 缺少维护脚本: $PKG_DIR/helpers/" >&2
  echo "      需要以下文件:" >&2
  echo "        cn.com.sangfor.atrust.common" >&2
  echo "        cn.com.sangfor.atrust.create_dir" >&2
  echo "        cn.com.sangfor.atrust.postinst" >&2
  echo "        cn.com.sangfor.atrust.prerm" >&2
  missing=1
fi
if [ "$missing" = 1 ]; then
  echo "提示: 请确认这些文件已提交到 git（git ls-files rpm-packaging）。" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# --- 获取 deb ---------------------------------------------------------------
# 优先级: -d/--deb > -u/--url > 环境变量 > 同目录 version 文件 > 同目录 aTrustInstaller*.deb

# version 文件: 单行内容，为 deb 下载地址(URL)或本地路径
VERSION_FILE="$HERE/version"
if [ -z "$DEB" ] && [ -z "$DEB_URL" ] && [ -f "$VERSION_FILE" ]; then
  src="$(head -n1 "$VERSION_FILE" | tr -d '[:space:]')"
  case "$src" in
    http://*|https://*) DEB_URL="$src";;
    "") : ;;
    /*) DEB="$src";;
    *)  DEB="$HERE/$src";;
  esac
  [ -n "$src" ] && echo "[*] 从 version 文件读取: $src"
fi

if [ -z "$DEB" ] && [ -n "$DEB_URL" ]; then
  command -v curl >/dev/null 2>&1 || { echo "错误: 需要 curl 才能下载 deb" >&2; exit 1; }
  echo "[*] 下载 deb: $DEB_URL"
  DEB="$tmp/download.deb"
  curl -fL --retry 3 --retry-delay 2 -o "$DEB" "$DEB_URL"
  DOWNLOADED=1
else
  DOWNLOADED=0
fi
if [ -n "$DEB" ] && [ ! -f "$DEB" ]; then
  echo "错误: 找不到 deb 文件: $DEB" >&2
  exit 1
fi
if [ -z "$DEB" ]; then
  DEB="$(ls "$HERE"/aTrustInstaller*.deb 2>/dev/null | head -1 || true)"
fi
[ -n "$DEB" ] && [ -f "$DEB" ] || {
  echo "错误: 未找到 deb。请用 -d 指定，或设置 version 文件 / ATRUST_DEB_URL，或放到 $HERE。" >&2
  exit 1
}
# 转为绝对路径（后续解包会 cd 到临时目录）
DEB="$(cd "$(dirname "$DEB")" && pwd)/$(basename "$DEB")"
echo "[*] 使用 deb: $DEB ($(du -h "$DEB" 2>/dev/null | cut -f1))"

# --- 解析 deb ---------------------------------------------------------------
( cd "$tmp" && ar x "$DEB" )
control_tar="$(cd "$tmp" && ls control.tar.* 2>/dev/null | head -1 || true)"
data_tar="$(cd "$tmp" && ls data.tar.* 2>/dev/null | head -1 || true)"
[ -n "$control_tar" ] && [ -n "$data_tar" ] || { echo "错误: $DEB 不是有效的 deb 包" >&2; exit 1; }

mkdir -p "$tmp/control"
tar -xf "$tmp/$control_tar" -C "$tmp/control"
DEB_PKG="$(awk -F': ' '/^Package:/{print $2; exit}' "$tmp/control/control")"
DEB_VERSION="$(awk -F': ' '/^Version:/{print $2; exit}' "$tmp/control/control")"
DEB_ARCH="$(awk -F': ' '/^Architecture:/{print $2; exit}' "$tmp/control/control")"

VERSION="${VER_OVERRIDE:-$DEB_VERSION}"
case "${ARCH_OVERRIDE:-$DEB_ARCH}" in
  amd64) RPM_ARCH="x86_64";;
  arm64) RPM_ARCH="aarch64";;
  i386)  RPM_ARCH="i686";;
  armhf) RPM_ARCH="armv7hl";;
  *)     RPM_ARCH="${ARCH_OVERRIDE:-$DEB_ARCH}";;
esac
# rpm 的 Version 不能含 '-'，用 '_' 代替
RPM_VERSION="${VERSION//-/_}"

# 下载得到的文件统一命名为 aTrustInstaller_<版本>_<deb架构>.deb（默认为 amd64）
CANON_DEB="aTrustInstaller_${DEB_VERSION}_${DEB_ARCH:-amd64}.deb"

echo "[*] 包名=$DEB_PKG  deb版本=$DEB_VERSION  deb架构=$DEB_ARCH"
echo "[*] 构建 => 版本=$RPM_VERSION  架构=$RPM_ARCH  Release=$RELEASE"
[ "$DOWNLOADED" = "1" ] && echo "[*] 下载文件将统一命名为: $CANON_DEB"

HOST_ARCH="$(uname -m)"
if [ "$RPM_ARCH" != "$HOST_ARCH" ]; then
  echo "[!] 警告: 目标架构 $RPM_ARCH 与本机 $HOST_ARCH 不一致，rpmbuild 可能拒绝构建；" >&2
  echo "    建议在对应架构的主机/CI runner 上构建（如 arm64 用 ubuntu-latest-arm）。" >&2
fi

# --- 组装 rpmbuild 工作区 ---------------------------------------------------
rm -rf "$TOP"
mkdir -p "$TOP"/BUILD "$TOP"/BUILDROOT "$TOP"/RPMS "$TOP"/SOURCES "$TOP"/SPECS "$TOP"/SRPMS

cp "$tmp/$data_tar" "$TOP/SOURCES/atrust-data.tar.xz"
mkdir -p "$tmp/stage/helpers"
cp "$PKG_DIR"/helpers/* "$tmp/stage/helpers/"
( cd "$tmp/stage" && tar czf "$TOP/SOURCES/atrust-rpm-helpers.tar.gz" helpers )
cp "$PKG_DIR"/SPECS/*.spec "$TOP/SPECS/"

DEFINES=(
  --define "_topdir $TOP"
  --define "atrust_version $RPM_VERSION"
  --define "atrust_release $RELEASE"
  --define "atrust_arch $RPM_ARCH"
)
if [ "$DIST_GIVEN" = 1 ]; then
  if [ "$DIST_REQ" = "none" ]; then
    DEFINES+=(--define "atrust_dist %{nil}")
    echo "[*] 发布标签: 已去除 (dist-neutral)"
  else
    DEFINES+=(--define "atrust_dist $DIST_REQ")
    echo "[*] 发布标签: $DIST_REQ"
  fi
fi

# --- 构建 -------------------------------------------------------------------
echo "[*] 构建二进制 RPM ..."
rpmbuild "${DEFINES[@]}" -bb "$TOP/SPECS/cn.com.sangfor.atrust.spec"
echo "[*] 构建源码 RPM ..."
rpmbuild "${DEFINES[@]}" -bs "$TOP/SPECS/cn.com.sangfor.atrust.spec"

# --- 收集产物 ---------------------------------------------------------------
mkdir -p "$OUTDIR"
rm -f "$OUTDIR"/*.rpm "$OUTDIR"/*.deb "$OUTDIR"/SHA256SUMS.txt "$OUTDIR"/VERSION "$OUTDIR"/ARCH 2>/dev/null || true
cp "$TOP"/RPMS/*/*.rpm "$OUTDIR"/
cp "$TOP"/SRPMS/*.rpm "$OUTDIR"/
# 下载的 deb 统一命名为 aTrustInstaller_<版本>_<架构>.deb 一并产出
if [ "$DOWNLOADED" = "1" ]; then
  cp -f "$DEB" "$OUTDIR/$CANON_DEB"
fi
(
  cd "$OUTDIR"
  sha256sum ./*.rpm > SHA256SUMS.txt
  for d in ./*.deb; do
    if [ -e "$d" ]; then sha256sum "$d" >> SHA256SUMS.txt; fi
  done
)
printf '%s\n' "$RPM_VERSION" > "$OUTDIR/VERSION"
printf '%s\n' "$RPM_ARCH"    > "$OUTDIR/ARCH"

echo
echo "==================== 构建完成 ===================="
(cd "$OUTDIR" && ls -l)
echo "产物目录: $OUTDIR"
