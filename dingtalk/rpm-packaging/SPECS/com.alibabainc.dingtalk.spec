#-------------------------------------------------------------------------------
# Repackaging of the official DingTalk (钉钉) .deb into an RPM for Fedora/RHEL.
#
# The binary payload is taken verbatim from the upstream .deb (data.tar.xz);
# the Debian maintainer scripts are ported to RPM scriptlets. The bundled
# libraries that shadow / conflict with modern Fedora system libraries are
# pruned at build time (the upstream deb does the same at install time based on
# the detected glibc / distribution, see README for the rationale).
#-------------------------------------------------------------------------------

# We repackage prebuilt vendor binaries: do not strip / rewrite / repath them.
%global __os_install_post %{nil}
%global debug_package %{nil}
%global _build_id_links none

# 排除 Fedora 已不再提供的旧 soname：
#   - libpangox-1.0.so.0：仅被自带的旧 GTK2-glext 库依赖，现代 Fedora 无此库；
#     相关 GL 旧控件不可用，但不影响主界面（Qt/CEF）运行。
#   - liblber-2.4.so.2 / libldap_r-2.4.so.2：仅被自带的 libcurl.so.4（经
#     libDingGuard_SDK_UOS.so 间接使用）依赖。Fedora 只有 OpenLDAP 2.6，且
#     openldap-compat 并不提供 OPENLDAP_2.4_2 版本符号，故该依赖无法满足；
#     相关 curl/LDAP 功能不可用，但不影响主界面启动与会议/聊天。
%global __requires_exclude ^(libpangox-1\\.0\\.so\\.0|liblber-2\\.4\\.so\\.2|libldap_r-2\\.4\\.so\\.2|libldap-2\\.4\\.so\\.2).*

%global dt_appdir /opt/apps/com.alibabainc.dingtalk

Name:           com.alibabainc.dingtalk
%{!?dingtalk_version:%global dingtalk_version 8.2.8.260818002}
%{!?dingtalk_release:%global dingtalk_release 1}
Version:        %{dingtalk_version}
Release:        %{dingtalk_release}%{?dingtalk_dist}%{!?dingtalk_dist:%{?dist}}
Summary:        DingTalk client (repackaged from official .deb)
Summary(zh_CN): 钉钉客户端（官方 deb 重新打包为 rpm）
License:        Proprietary
URL:            https://www.dingtalk.com
Source0:        dingtalk-data.tar.xz
Source1:        dingtalk-rpm-helpers.tar.gz
%{!?dingtalk_arch:%global dingtalk_arch x86_64}
BuildArch:      %{dingtalk_arch}

# Runtime tools used by the client and by its maintainer scripts.
Requires:       bash
Requires:       coreutils
Requires:       gawk
Requires:       grep
Requires:       sed
Requires:       findutils
Requires:       procps-ng
Requires:       psmisc
Requires:       util-linux
Requires:       shadow-utils
Requires:       glibc
Requires:       zlib

Recommends:     xdg-utils
Recommends:     desktop-file-utils
Recommends:     gtk-update-icon-cache
Recommends:     libglvnd-glx
Recommends:     mesa-libgbm

%description
钉钉（DingTalk）是阿里巴巴推出的企业级通讯与协同办公客户端。本包由官方
Ubuntu/Debian 的 .deb 安装包（版本 %{dingtalk_version}）重新打包为 RPM，并对
安装/卸载脚本做了 Fedora、RHEL 系发行版适配。

%description -l zh_CN
钉钉（DingTalk）是阿里巴巴推出的企业级通讯与协同办公客户端。本包由官方
Ubuntu/Debian 的 .deb 安装包重新打包为 RPM。

%prep
rm -rf payload helpers
mkdir -p payload helpers
tar -xf %{SOURCE0} -C payload
tar -xf %{SOURCE1} -C .

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -a payload/. %{buildroot}/

# 产品版本目录名（内容同 files/version，例如 8.2.8-Release.260818002）
DT_PRODUCT="$(head -n1 %{buildroot}%{dt_appdir}/files/version | tr -d '[:space:]')"
[ -n "$DT_PRODUCT" ] || { echo "ERROR: 无法读取 %{dt_appdir}/files/version" >&2; exit 1; }
DT_BASE="%{buildroot}%{dt_appdir}/files/${DT_PRODUCT}"
echo "DingTalk product dir: ${DT_PRODUCT}"

# 删除与新版 Fedora 系统库冲突的包内自带库（等价于官方 deb postinst 在
# “较新 glibc + 非麒麟/国产发行版”下的处理，另按 aTrust 的经验补充删除自带的
# 旧版 libstdc++，避免其抢占系统库导致 GLIBCXX 版本不足）：
#   - libstdc++.so.6*：自带为 GCC6(最高 GLIBCXX_3.4.25)，会挡住系统较新库
#   - libm.so.6、libgbm.so*、libGLX.so*、libGLdispatch.so*：统一用系统实现
for f in \
    libstdc++.so.6 \
    libstdc++.so.6.0.25 \
    libm.so.6 \
    libgbm.so \
    libgbm.so.1 \
    libgbm.so.1.0.0 \
    libGLX.so \
    libGLX.so.0 \
    libGLX.so.0.0.0 \
    libGLdispatch.so \
    libGLdispatch.so.0 \
    libGLdispatch.so.0.0.0 ; do
  if [ -e "${DT_BASE}/${f}" ]; then
    echo "prune bundled ${f}"
    rm -f "${DT_BASE}/${f}"
  fi
done

# CEF 沙箱需要 chrome-sandbox 具备 setuid 权限（RPM 会记录 4755 并在安装时恢复）。
# 属主/属组统一由 %files 的 %defattr 设为 root:root（非 root 用户构建时无法 chown）。
DT_SANDBOX="${DT_BASE}/plugins/dtwebview/chrome-sandbox"
if [ -f "${DT_SANDBOX}" ]; then
  chmod 4755 "${DT_SANDBOX}"
  echo "setuid chrome-sandbox: ${DT_SANDBOX#%{buildroot}}"
fi

# Ported maintainer scripts (Debian control scripts -> RPM helpers).
install -d %{buildroot}%{_libexecdir}/com.alibabainc.dingtalk
install -m 0755 helpers/com.alibabainc.dingtalk.common   %{buildroot}%{_libexecdir}/com.alibabainc.dingtalk/
install -m 0755 helpers/com.alibabainc.dingtalk.postinst %{buildroot}%{_libexecdir}/com.alibabainc.dingtalk/
install -m 0755 helpers/com.alibabainc.dingtalk.prerm    %{buildroot}%{_libexecdir}/com.alibabainc.dingtalk/
install -m 0755 helpers/com.alibabainc.dingtalk.postrm   %{buildroot}%{_libexecdir}/com.alibabainc.dingtalk/

%files
%defattr(-,root,root,-)
%{dt_appdir}
/usr/share/applications/com.alibabainc.dingtalk.desktop
%{_libexecdir}/com.alibabainc.dingtalk

%pre
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/var/log/dingtalk/rpm-install.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null
log() { echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] $*" >> "$LOG_PATH"; }

log "dingtalk rpm pre-install begin, arg=$*"

# 关闭正在运行的钉钉进程（与官方 deb preinst 行为一致）
if pgrep -f 'com.alibabainc.dingtalk --' >/dev/null 2>&1; then
    log "killing running dingtalk processes"
    pkill -f 'com.alibabainc.dingtalk --' >/dev/null 2>&1 || true
fi

log "dingtalk rpm pre-install end"
exit 0

%post
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
HELPER=%{_libexecdir}/com.alibabainc.dingtalk
if [ -x "$HELPER/com.alibabainc.dingtalk.postinst" ]; then
    bash "$HELPER/com.alibabainc.dingtalk.postinst" "$@"
else
    echo "dingtalk: helper postinst not found" >&2
fi
exit 0

%preun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
HELPER=%{_libexecdir}/com.alibabainc.dingtalk
if [ "$1" -eq 0 ] 2>/dev/null; then
    # 完全卸载：停止进程并清理用户桌面的快捷方式
    [ -x "$HELPER/com.alibabainc.dingtalk.prerm" ] \
        && bash "$HELPER/com.alibabainc.dingtalk.prerm" remove
    [ -x "$HELPER/com.alibabainc.dingtalk.postrm" ] \
        && bash "$HELPER/com.alibabainc.dingtalk.postrm" 0
else
    # 升级：仅停止旧进程，新包的 %post 会重新发放桌面快捷方式
    [ -x "$HELPER/com.alibabainc.dingtalk.prerm" ] \
        && bash "$HELPER/com.alibabainc.dingtalk.prerm" upgrade
fi
exit 0

%postun
#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
LOG_PATH="/var/log/dingtalk/rpm-install.log"
mkdir -p "$(dirname "$LOG_PATH")" 2>/dev/null
echo "[$(date '+%%Y-%%m-%%d %%H:%%M:%%S')] [Infor] dingtalk rpm post-uninstall, arg=$*" >> "$LOG_PATH" 2>&1
exit 0

%changelog
* Sun Oct 11 2026 Repackager <root@localhost> - %{dingtalk_version}-%{dingtalk_release}
- Repackage official DingTalk .deb %{dingtalk_version} into RPM.
- Port Debian maintainer scripts to Fedora/RHEL compatible RPM scriptlets.
- Prune bundled libraries that conflict with modern Fedora system libraries.
