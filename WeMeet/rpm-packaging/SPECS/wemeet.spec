#-------------------------------------------------------------------------------
# Repackaging of the official Tencent Meeting (Wemeet / 腾讯会议) .deb into an
# RPM for Fedora/RHEL.
#
# The binary payload is taken verbatim from the upstream .deb (data.tar.xz);
# the Debian maintainer scripts are ported to RPM scriptlets. The icon files
# that the upstream postinst would register with xdg-icon-resource are instead
# installed into the hicolor theme at build time.
#-------------------------------------------------------------------------------

# We repackage prebuilt vendor binaries: do not strip / rewrite / repath them.
%global __os_install_post %{nil}
%global debug_package %{nil}
%global _build_id_links none

%global wm_appdir /opt/wemeet

Name:           wemeet
%{!?wemeet_version:%global wemeet_version 3.26.10.401}
%{!?wemeet_release:%global wemeet_release 1}
Version:        %{wemeet_version}
Release:        %{wemeet_release}%{?wemeet_dist}%{!?wemeet_dist:%{?dist}}
Summary:        Tencent Meeting (Wemeet) client (repackaged from official .deb)
Summary(zh_CN): 腾讯会议客户端（官方 deb 重新打包为 rpm）
License:        Proprietary
URL:            https://wemeet.qq.com
Source0:        wemeet-data.tar.xz
Source1:        wemeet-rpm-helpers.tar.gz
%{!?wemeet_arch:%global wemeet_arch x86_64}
BuildArch:      %{wemeet_arch}

# Runtime tools used by the client and by its maintainer scripts.
Requires:       bash
Requires:       coreutils
Requires:       gawk
Requires:       grep
Requires:       sed
Requires:       findutils
Requires:       procps-ng
Requires:       psmisc
Requires:       glibc
Requires:       zlib

Recommends:     desktop-file-utils
Recommends:     gtk-update-icon-cache
Recommends:     xdg-utils

%description
腾讯会议（Tencent Meeting / Wemeet）是腾讯推出的云视频会议客户端。本包由官方
.deb 安装包（版本 %{wemeet_version}）重新打包为 RPM，并对安装/卸载脚本做了
Fedora、RHEL 系发行版适配。

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
install -d %{buildroot}%{_libexecdir}/wemeet
install -m 0755 helpers/wemeet.common   %{buildroot}%{_libexecdir}/wemeet/
install -m 0755 helpers/wemeet.postinst %{buildroot}%{_libexecdir}/wemeet/
install -m 0755 helpers/wemeet.prerm    %{buildroot}%{_libexecdir}/wemeet/

# 官方 deb postinst 用 xdg-icon-resource 把 /opt/wemeet/icons 下的图标注册到
# hicolor 主题；这里在构建阶段直接装入 /usr/share/icons/hicolor。
for size in 16 32 64 128 256; do
  src="%{buildroot}%{wm_appdir}/icons/hicolor/${size}x${size}/mimetypes/wemeetapp.png"
  if [ -f "$src" ]; then
    install -d "%{buildroot}/usr/share/icons/hicolor/${size}x${size}/mimetypes"
    install -m 0644 "$src" "%{buildroot}/usr/share/icons/hicolor/${size}x${size}/mimetypes/wemeetapp.png"
  fi
done

# 确保启动脚本与主程序可执行
chmod 0755 "%{buildroot}%{wm_appdir}/wemeetapp.sh" 2>/dev/null || true
chmod 0755 "%{buildroot}%{wm_appdir}/bin/wemeetapp" 2>/dev/null || true

%files
%defattr(-,root,root,-)
%{wm_appdir}
/usr/share/applications/wemeetapp.desktop
/usr/share/icons/hicolor/16x16/mimetypes/wemeetapp.png
/usr/share/icons/hicolor/32x32/mimetypes/wemeetapp.png
/usr/share/icons/hicolor/64x64/mimetypes/wemeetapp.png
/usr/share/icons/hicolor/128x128/mimetypes/wemeetapp.png
/usr/share/icons/hicolor/256x256/mimetypes/wemeetapp.png
%{_libexecdir}/wemeet

%pre
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/var/log/wemeet/rpm-install.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null
log() { echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] $*" >> "$LOG_PATH"; }

log "wemeet rpm pre-install begin, arg=$*"

# 结束正在运行的客户端（与官方 deb 在安装阶段 pkill wemeetapp 的意图一致）
if pgrep -f 'wemeetapp' >/dev/null 2>&1; then
    log "killing running wemeetapp"
    pkill -f 'wemeetapp' >/dev/null 2>&1 || true
fi

log "wemeet rpm pre-install end"
exit 0

%post
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
HELPER=%{_libexecdir}/wemeet
if [ -x "$HELPER/wemeet.postinst" ]; then
    bash "$HELPER/wemeet.postinst" "$@"
else
    echo "wemeet: helper postinst not found" >&2
fi
exit 0

%preun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
HELPER=%{_libexecdir}/wemeet
ACTION="upgrade"
[ "$1" -eq 0 ] 2>/dev/null && ACTION="remove"
if [ -x "$HELPER/wemeet.prerm" ]; then
    bash "$HELPER/wemeet.prerm" "$ACTION"
fi
exit 0

%postun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/var/log/wemeet/rpm-install.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null
echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] wemeet rpm post-uninstall, arg=$*" >> "$LOG_PATH" 2>&1
# 文件已删除后刷新桌面/图标缓存（沿用官方 postrm 的 update-desktop-database）
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0

%changelog
* Sun Oct 11 2026 Repackager <root@localhost> - %{wemeet_version}-%{wemeet_release}
- Repackage official Tencent Meeting / Wemeet .deb %{wemeet_version} into RPM.
- Port Debian maintainer scripts to Fedora/RHEL compatible RPM scriptlets.
- Install application icons into the hicolor theme at build time.
