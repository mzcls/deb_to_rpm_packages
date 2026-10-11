#-------------------------------------------------------------------------------
# Repackaging of the official Sangfor aTrust .deb into an RPM for Fedora/RHEL.
#
# The binary payload is taken verbatim from the upstream .deb (data.tar.xz) and
# the Debian maintainer scripts have been ported to RPM scriptlets while keeping
# the original behaviour (service setup, database config upgrade, tray, certs...).
#-------------------------------------------------------------------------------

# We repackage prebuilt vendor binaries: do not strip / rewrite / repath them.
%global __os_install_post %{nil}
%global debug_package %{nil}
%global _build_id_links none

# Drop requires for sonames that are only needed by the bundled (old) OpenLDAP
# client libraries and are not shipped by any current Fedora release.
%global __requires_exclude ^(libgcrypt\\.so\\.11|libgnutls\\.so\\.26|libsasl2\\.so\\.2).*

Name:           cn.com.sangfor.atrust
%{!?atrust_version:%global atrust_version 2.5.16.30}
%{!?atrust_release:%global atrust_release 1}
Version:        %{atrust_version}
Release:        %{atrust_release}%{?atrust_dist}%{!?atrust_dist:%{?dist}}
Summary:        Sangfor aTrust SDP/SSL VPN client (repackaged from official .deb)
Summary(zh_CN): 深信服 aTrust SDP/SSL VPN 客户端（官方 deb 重新打包为 rpm）
License:        Proprietary
URL:            http://www.sangfor.com.cn
Source0:        atrust-data.tar.xz
Source1:        atrust-rpm-helpers.tar.gz
%{!?atrust_arch:%global atrust_arch x86_64}
BuildArch:      %{atrust_arch}
# 用于清除 libmmkv.so 的可执行栈需求（见 %install 说明）
BuildRequires:  patchelf

# Runtime tools used by the client and by its maintainer scripts.
Requires:       bash
Requires:       coreutils
Requires:       gawk
Requires:       grep
Requires:       sed
Requires:       findutils
Requires:       psmisc
Requires:       procps-ng
Requires:       util-linux
Requires:       systemd
Requires:       glibc
Requires:       libxcrypt-compat
Requires:       at-spi2-core
Requires:       gtk3
Requires:       alsa-lib
Requires:       cups-libs
Requires:       mesa-libgbm
Requires:       libdrm
Requires:       libX11
Requires:       libX11-xcb
Requires:       libXcomposite
Requires:       libXcursor
Requires:       libXdamage
Requires:       libXext
Requires:       libXfixes
Requires:       libXi
Requires:       libXrandr
Requires:       libXrender
Requires:       libXScrnSaver
Requires:       libXtst
Requires:       libxcb
Requires:       xcb-util
Requires:       xcb-util-image
Requires:       xcb-util-keysyms
Requires:       xcb-util-renderutil
Requires:       xcb-util-wm
Requires:       libxkbcommon
Requires:       libxkbcommon-x11
Requires:       fontconfig
Requires:       freetype
Requires:       harfbuzz
Requires:       cairo
Requires:       pango
Requires:       gdk-pixbuf2
Requires:       glib2
Requires:       libglvnd-glx
Requires:       libSM
Requires:       libICE
Requires:       dbus-libs
Requires:       libproxy
Requires:       sqlite-libs
Requires:       libblkid
Requires:       e2fsprogs-libs
Requires:       systemd-libs
Requires:       zlib
# Fedora 只默认提供可变字体 Noto Sans CJK VF，旧版 Electron/Chromium 无法渲染，
# 依赖静态 CJK 字体；同时通过 /etc/fonts/atrust-fonts.conf 仅为 aTrust 屏蔽 VF 字体。
Requires:       google-noto-sans-cjk-fonts

Recommends:     lsb_release
Recommends:     iptables-nft
Recommends:     sudo
Recommends:     xdg-utils
Recommends:     pinentry

# The bundled libsqlite3.so (SONAME libsqlite3.so) does not carry a version
# definition node, but bundled libsoftokn3.so requires its SQLITE_3 symbols.
# Declare the capability so dependency resolution succeeds (runtime falls back
# to the unversioned symbol in the bundled library).
Provides:       libsqlite3.so(SQLITE_3)(64bit)

%description
Sangfor aTrust 是深信服推出的 SDP/SSL 零信任客户端。本包由官方 Ubuntu/Debian
的 .deb 安装包（版本 %{atrust_version}）重新打包为 RPM，并对安装/卸载脚本做了
Fedora、RHEL 系发行版适配，保持原有功能（系统服务、数据库升级、托盘、证书信任、
SPA 地址解析等）。

注意：安装过程中会强制关闭正在运行的浏览器，并会重启 aTrust 相关服务。

%prep
rm -rf payload helpers
mkdir -p payload helpers
tar -xf %{SOURCE0} -C payload
tar -xf %{SOURCE1} -C .

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a payload/. %{buildroot}/

# Ported maintainer scripts (Debian control scripts -> RPM helpers).
install -d %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust
install -m 0755 helpers/cn.com.sangfor.atrust.common   %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust/
install -m 0755 helpers/cn.com.sangfor.atrust.create_dir %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust/
install -m 0755 helpers/cn.com.sangfor.atrust.postinst %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust/
install -m 0755 helpers/cn.com.sangfor.atrust.prerm    %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust/
install -m 0755 helpers/run-tray                       %{buildroot}%{_libexecdir}/cn.com.sangfor.atrust/run-tray

# /usr/share/applications entry: keep the upstream regular desktop file during
# build; the post-install script turns it into a symlink to the app entry (same
# final state as the official .deb postinst).

# Install icons into the hicolor theme so GNOME/KDE can resolve Icon=aTrust.
install -d %{buildroot}/usr/share/icons/hicolor/48x48/apps
install -d %{buildroot}/usr/share/icons/hicolor/256x256/apps
install -m 0644 %{buildroot}/opt/apps/cn.com.sangfor.atrust/entries/icons/hicolor/48x48/apps/aTrust.png \
       %{buildroot}/usr/share/icons/hicolor/48x48/apps/aTrust.png
install -m 0644 %{buildroot}/usr/share/sangfor/aTrust/resources/aTrust.png \
       %{buildroot}/usr/share/icons/hicolor/256x256/apps/aTrust.png

# Fedora/VM compatibility: on machines without a usable GPU process (VMs,
# remote sessions) the Electron tray aborts with "GPU process isn't usable".
# Adding --disable-gpu-sandbox keeps it running (the client already runs with
# --no-sandbox). This affects both the launcher and the daemon-started tray.
sed -i 's#--no-sandbox --disable-gpu#--no-sandbox --disable-gpu-sandbox --disable-gpu#' \
    %{buildroot}/opt/apps/cn.com.sangfor.atrust/entries/applications/cn.com.sangfor.atrust.desktop \
    %{buildroot}/usr/share/applications/cn.com.sangfor.atrust.desktop
sed -i '/arr_parameter\[0\]="--no-sandbox"/a arr_parameter[1]="--disable-gpu-sandbox"' \
    %{buildroot}/usr/share/sangfor/aTrust/resources/shell/aTrustTrayStart.sh

# 字体兼容：Fedora 默认只有可变字体 Noto Sans CJK VF，旧版 Electron/Chromium
# 无法渲染（全部显示为方框）。为 aTrust 单独提供 fontconfig，屏蔽 VF 字体，
# 回退到静态的 Noto Sans CJK。
install -d %{buildroot}/etc/fonts
cat > %{buildroot}/etc/fonts/atrust-fonts.conf <<'FONTCONF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <selectfont>
    <rejectfont>
      <glob>/usr/share/fonts/google-noto-sans-cjk-vf-fonts/*</glob>
      <glob>/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/*</glob>
      <glob>/usr/share/fonts/google-noto-serif-cjk-vf-fonts/*</glob>
    </rejectfont>
  </selectfont>
</fontconfig>
FONTCONF

# 让 aTrust 的所有 GUI 进程使用上述 fontconfig，并统一修复 Fedora 下的
# 库符号抢占问题（详见 helpers/run-tray）：
#   - LD_PRELOAD 内置 libsqlite3.so / libcurl.so，避免系统同名库抢占
#   - QT_QPA_PLATFORM_PLUGIN_PATH 指向内置 Qt 平台插件目录
# 桌面项改为调用包装脚本；托盘启动脚本与守护进程内联设置同样的环境变量。
sed -i 's#^Exec=/usr/share/sangfor/aTrust/aTrustTray#Exec=%{_libexecdir}/cn.com.sangfor.atrust/run-tray#' \
    %{buildroot}/opt/apps/cn.com.sangfor.atrust/entries/applications/cn.com.sangfor.atrust.desktop \
    %{buildroot}/usr/share/applications/cn.com.sangfor.atrust.desktop
sed -i \
  -e '/^export PATH$/a export LD_PRELOAD="/usr/share/sangfor/aTrust/resources/bin/libsqlite3.so /usr/share/sangfor/aTrust/resources/bin/libcurl.so"' \
  -e '/^export PATH$/a export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/share/sangfor/aTrust/resources/lib' \
  -e '/^export PATH$/a export FONTCONFIG_FILE=/etc/fonts/atrust-fonts.conf' \
    %{buildroot}/usr/share/sangfor/aTrust/resources/shell/aTrustTrayStart.sh

# 守护进程同样需要：让内置 libcurl 优先，避免系统 libcurl.so.4(OpenSSL4) 与
# 内置 OpenSSL1.1 的 SSL 回调 ABI 不一致导致守护进程 SEGV；同时给其拉起的
# Qt 工具提供平台插件路径与字体配置。
sed -i '/^\[Service\]/a Environment=LD_PRELOAD=/usr/share/sangfor/aTrust/resources/bin/libcurl.so\nEnvironment=QT_QPA_PLATFORM_PLUGIN_PATH=/usr/share/sangfor/aTrust/resources/lib\nEnvironment=FONTCONFIG_FILE=/etc/fonts/atrust-fonts.conf' \
    %{buildroot}/usr/lib/systemd/system/aTrustDaemon.service
sed -i '/^APPHOME=/a export LD_PRELOAD=/usr/share/sangfor/aTrust/resources/bin/libcurl.so' \
    %{buildroot}/usr/share/sangfor/aTrust/resources/shell/aTrustDaemon.sh

# 清理“可执行栈(execstack)”需求。
# 客户端自带的 libmmkv.so 带有 PT_GNU_STACK=RWE 标记，新版内核/glibc 会拒绝加载
# （报错：cannot enable executable stack as shared object requires: Invalid argument），
# 导致历史/地址数据库(libmmkv)无法加载，表现为“接入地址无法记住/重启后为空”。
# mmkv 并不真的需要可执行栈，这里统一去掉该标记。
command -v patchelf >/dev/null 2>&1 || { echo "ERROR: 需要 patchelf 来清除 libmmkv.so 的 execstack 标记" >&2; exit 1; }
for d in \
    usr/share/sangfor/aTrust/resources/bin \
    usr/share/sangfor/aTrust/resources/lib \
    usr/share/sangfor/aTrust/uem/bin \
    usr/share/sangfor/aTrust/uem/lib ; do
  [ -d "%{buildroot}/$d" ] || continue
  for f in "%{buildroot}/$d"/*; do
    [ -f "$f" ] || continue
    if LC_ALL=C readelf -lW "$f" 2>/dev/null | grep -q 'GNU_STACK.*RWE'; then
      echo "clear execstack: ${f#%{buildroot}}"
      patchelf --clear-execstack "$f"
    fi
  done
done

# 让关键程序“直接依赖”内置的 libcurl/libsqlite3，避免被系统同名库符号抢占：
#   - 系统 GTK3 会带出 libtinysparql -> 系统 libsqlite3.so.0，与内置 SQLCipher
#     抢占符号导致 sqlcipher_activate 崩溃；
#   - 系统 libcurl.so.4(OpenSSL4) 与内置 OpenSSL1.1 的 SSL 回调 ABI 不一致。
# 通过给主程序加 DT_NEEDED（排在最前）让内置库优先加载，从而不依赖启动脚本的
# 环境变量（桌面/菜单/守护进程任何方式启动都生效）。
add_needed() {
  local f="$1"; shift
  [ -f "$f" ] || return 0
  local lib
  for lib in "$@"; do
    if ! LC_ALL=C readelf -d "$f" | grep -q "NEEDED.*\[$lib\]"; then
      patchelf --add-needed "$lib" "$f"
      echo "add-needed $lib -> ${f#%{buildroot}}"
    fi
  done
}
add_needed %{buildroot}/usr/share/sangfor/aTrust/aTrustTray                libcurl.so libsqlite3.so
add_needed %{buildroot}/usr/share/sangfor/aTrust/resources/bin/aTrustTray2 libcurl.so libsqlite3.so
add_needed %{buildroot}/usr/share/sangfor/aTrust/resources/bin/aTrustAgent libcurl.so libsqlite3.so

%files
/usr/share/sangfor
/opt/apps
/usr/libexec/cn.com.sangfor.atrust
/usr/lib/systemd/system/aTrustDaemon.service
/usr/lib/systemd/system/aTrustShell.service
/usr/lib/systemd/system/aTrustTray@.service
/usr/lib/systemd/user/aTrustShell.service
/usr/lib/systemd/user/aTrustTray.service
/usr/share/applications/cn.com.sangfor.atrust.desktop
/usr/share/pixmaps/aTrust.png
/usr/share/icons/hicolor/48x48/apps/aTrust.png
/usr/share/icons/hicolor/256x256/apps/aTrust.png
/etc/fonts/atrust-fonts.conf

%pre
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/root/.aTrust/logs/aTrustInstallOut.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null
log() { echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] $*" >> "$LOG_PATH"; }

log "aTrust rpm pre-install begin"
echo "all argv $*"

# 记录安装包文件名，供 %post 解析 SPA/地址使用（放到临时文件里）
rm -f /tmp/.atrust_rpm_name
p=$PPID
i=0
while [ -n "$p" ] && [ "$p" -gt 0 ] 2>/dev/null && [ "$i" -lt 12 ]; do
    cl=$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null)
    for tok in $cl; do
        case "$tok" in
            *.rpm)
                if [ -e "$tok" ]; then
                    printf '%%s' "$tok" > /tmp/.atrust_rpm_name
                fi
                ;;
        esac
    done
    [ -s /tmp/.atrust_rpm_name ] && break
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    i=$((i+1))
done
[ -s /tmp/.atrust_rpm_name ] || printf '%%s' "aTrustInstaller_amd64.rpm" > /tmp/.atrust_rpm_name

shared_dir="/usr/share/sangfor/.aTrust"
if [ ! -e "$shared_dir" ]; then
    mkdir -p "$shared_dir"
    chmod 777 "$shared_dir"
fi
if ! touch "${shared_dir}/tray_not_auto_launch"; then
    log "touch ${shared_dir}/tray_not_auto_launch fail"
fi
log "first install, tray need not auto launch"

# 停止旧服务
{
    systemctl daemon-reload 2>/dev/null
    systemctl stop aTrustDaemon 2>/dev/null
    systemctl disable aTrustDaemon 2>/dev/null
} >> "$LOG_PATH" 2>&1

# 杀掉可能存在的 aTrust 进程
for p in uem_dialog aTrustDiagnosisTool aTrustTray aTrustTray2 aTrustAgent aTrustXtunnel-64; do
    if pidof "$p" >/dev/null 2>&1; then
        killall "$p" >> "$LOG_PATH" 2>&1
        sleep 0.2
        killall -9 "$p" >> "$LOG_PATH" 2>&1
    fi
done
if [ -x /usr/share/sangfor/aTrust/resources/shell/aTrustTrayStart.sh ]; then
    /usr/share/sangfor/aTrust/resources/shell/aTrustTrayStart.sh -- -s stop >> "$LOG_PATH" 2>&1
fi

# 清理 aTrust 的 iptables 规则
iptables_name="iptables"
ip6tables_name="ip6tables"
if command -v iptables-legacy >/dev/null 2>&1; then
    iptables_name="iptables-legacy"
    ip6tables_name="ip6tables-legacy"
fi
if command -v "$iptables_name" >/dev/null 2>&1; then
    if [ "$($iptables_name -nvL -t nat 2>/dev/null | grep -w ATRUST_DNS | wc -l)" -gt 0 ]; then
        $iptables_name -t nat -F ATRUST_DNS 2>>"$LOG_PATH"
        $iptables_name -t nat -D OUTPUT -j ATRUST_DNS 2>>"$LOG_PATH"
        $iptables_name -t nat -X ATRUST_DNS 2>>"$LOG_PATH"
    fi
    if [ "$($iptables_name -nvL -t filter 2>/dev/null | grep -w ATRUST_BLOCK_DNS | wc -l)" -gt 0 ]; then
        $iptables_name -t filter -F ATRUST_BLOCK_DNS 2>>"$LOG_PATH"
        $iptables_name -t filter -D OUTPUT -j ATRUST_BLOCK_DNS 2>>"$LOG_PATH"
        $iptables_name -t filter -X ATRUST_BLOCK_DNS 2>>"$LOG_PATH"
    fi
fi
if command -v "$ip6tables_name" >/dev/null 2>&1; then
    if [ "$($ip6tables_name -nvL -t mangle 2>/dev/null | grep -w ATRUST_DNS | wc -l)" -gt 0 ]; then
        $ip6tables_name -t mangle -F ATRUST_DNS 2>>"$LOG_PATH"
        $ip6tables_name -t mangle -D OUTPUT -j ATRUST_DNS 2>>"$LOG_PATH"
        $ip6tables_name -t mangle -X ATRUST_DNS 2>>"$LOG_PATH"
    fi
    if [ "$($ip6tables_name -nvL -t nat 2>/dev/null | grep -w ATRUST_DNS | wc -l)" -gt 0 ]; then
        $ip6tables_name -t nat -F ATRUST_DNS 2>>"$LOG_PATH"
        $ip6tables_name -t nat -D OUTPUT -j ATRUST_DNS 2>>"$LOG_PATH"
        $ip6tables_name -t nat -X ATRUST_DNS 2>>"$LOG_PATH"
    fi
fi

log "aTrust rpm pre-install end"
exit 0

%post
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
export LANG=${LANG:-zh_CN.UTF-8}
export LANGUAGE=${LANGUAGE:-zh_CN}
HELPER=/usr/libexec/cn.com.sangfor.atrust
if [ -x "$HELPER/cn.com.sangfor.atrust.postinst" ]; then
    bash "$HELPER/cn.com.sangfor.atrust.postinst" "$@" >>/root/.aTrust/logs/aTrustInstallOut.log 2>&1
else
    echo "aTrust: helper postinst not found" >&2
fi
exit 0

%preun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
HELPER=/usr/libexec/cn.com.sangfor.atrust
ACTION="upgrade"
[ "$1" -eq 0 ] 2>/dev/null && ACTION="remove"
if [ -x "$HELPER/cn.com.sangfor.atrust.prerm" ]; then
    bash "$HELPER/cn.com.sangfor.atrust.prerm" "$ACTION" >>/root/.aTrust/logs/aTrustInstallOut.log 2>&1
fi
exit 0

%postun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/root/.aTrust/logs/aTrustInstallOut.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null

{
  echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] aTrust rpm post-uninstall begin, arg=$*"
  kill -9 $(pidof aTrustDiagnosisTool) 2>/dev/null

  if [ "$1" -eq 0 ] 2>/dev/null; then
      # 完全卸载：清理运行时数据（保留日志），与官方 postrm 行为一致
      rm -f /usr/share/sangfor/.aTrust/var/run/InstallLocation 2>/dev/null
      rm -rf /usr/share/sangfor/.aTrust 2>/dev/null

      for user in $(/usr/bin/users 2>/dev/null); do
          home_dir=$(getent passwd "$user" | awk -F ':' '{print $6}')
          [ -z "$home_dir" ] && continue
          desktop_path=""
          if [ -f "$home_dir/.config/user-dirs.dirs" ]; then
              desktop_path=$(awk -F'"' '/^XDG_DESKTOP_DIR/{print $2}' "$home_dir/.config/user-dirs.dirs")
              desktop_path=$(eval echo "$desktop_path")
          fi
          if [ -n "$desktop_path" ] && [ -f "$desktop_path/cn.com.sangfor.atrust.desktop" ]; then
              rm -f "$desktop_path/cn.com.sangfor.atrust.desktop"
          fi
          if [ -d "$home_dir/.aTrust" ]; then
              find "$home_dir/.aTrust" -mindepth 1 -not -path '*/logs' -not -path '*/logs/*' -delete 2>/dev/null
          fi
      done

      if [ -d /root/.aTrust ]; then
          find /root/.aTrust -mindepth 1 -not -path '*/logs' -not -path '*/logs/*' -delete 2>/dev/null
      fi
      echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] aTrust data cleaned, logs kept"
  fi
  echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] aTrust rpm post-uninstall end"
} >> "$LOG_PATH" 2>&1

exit 0

%changelog
* Sun Oct 11 2026 Repackager <root@localhost> - %{atrust_version}-%{atrust_release}
- Repackage official Sangfor aTrust .deb %{atrust_version} into RPM.
- Port Debian maintainer scripts to Fedora/RHEL compatible RPM scriptlets.
- Install sangfor CA into the Fedora system trust store.
