# 钉钉 dingtalk deb → rpm 转换说明（Fedora / RHEL）

将钉钉官方 Linux 版 `.deb` 安装包（`com.alibabainc.dingtalk_8.2.8.260818002_amd64.deb`）
重新打包为 RPM，并针对 Fedora 45（及 RHEL 系）做了安装/卸载脚本适配，
保持客户端原有功能。

> 目录结构参考同仓库的 `atrust/`（单仓多包，CI 工作流位于仓库根目录）。

## 产物

| 文件 | 说明 |
| --- | --- |
| `com.alibabainc.dingtalk-8.2.8.260818002-1.fc45.x86_64.rpm` | 可直接安装的二进制 RPM（约 373 MiB，装后约 990 MiB） |
| `com.alibabainc.dingtalk-8.2.8.260818002-1.fc45.src.rpm` | 源码 RPM（内含 deb 原始数据包与适配脚本，可重新构建） |
| `rpm-packaging/SPECS/com.alibabainc.dingtalk.spec` | spec 文件 |
| `rpm-packaging/helpers/` | 从 deb 的 control 脚本移植并适配后的安装/卸载脚本 |
| `build-rpm.sh` | 一键从 deb 重新构建 RPM 的脚本 |

## 安装 / 卸载

```bash
# 安装（自动安装依赖）
sudo dnf install ./com.alibabainc.dingtalk-8.2.8.260818002-1.fc45.x86_64.rpm

# 卸载
sudo dnf remove com.alibabainc.dingtalk

# 启动
# 在应用菜单或桌面快捷方式点击“钉钉”，或执行：
/opt/apps/com.alibabainc.dingtalk/files/Elevator.sh
```

安装日志：`/var/log/dingtalk/rpm-install.log`

## 从 deb 重新构建（一键脚本，支持升级版本）

脚本会自动从 deb 的 control 里读取**版本号**和**架构**。默认读取本目录的 `version`
文件（内容为 deb 下载地址），升级时改 `version` 里的地址再跑一次即可：

```bash
./build-rpm.sh                                    # 读 version 文件里的 URL 下载并构建
./build-rpm.sh -d com.alibabainc.dingtalk_x.deb   # 指定本地 deb
./build-rpm.sh -u https://.../x.deb               # 指定 URL
./build-rpm.sh -v 8.2.9 -r 2                       # 覆盖版本号 / Release 号
./build-rpm.sh -a aarch64                          # 覆盖目标架构（需在对应架构主机上构建）
./build-rpm.sh --dist .fc45                        # 指定发布标签（默认用构建机/Fedora 镜像的 %dist）
./build-rpm.sh --dist none                         # 去掉标签，产出发行版无关的包名
```

产物输出到 `dist/`：二进制 RPM、源码 RPM、下载的 deb（统一重命名）、
`SHA256SUMS.txt`、`VERSION`、`ARCH`。

## version 文件

本目录的 `version` 文件是**版本来源的唯一入口**，单行内容为 deb 下载地址，例如：

```
https://dtapp-pub.dingtalk.com/dingtalk-desktop/xc_dingtalk_update/linux_deb/Release/com.alibabainc.dingtalk_8.2.8.260818002_amd64.deb
```

升级版本时只需改这一行并提交，CI 会自动构建。**下载后会统一重命名为
`com.alibabainc.dingtalk_<版本>_<架构>.deb`**，并连同 RPM 一起输出到 `dist/`。

## GitHub Actions 自动构建

本包已并入单仓多包（monorepo）结构，工作流统一放在**仓库根目录**
`.github/workflows/build-rpm.yml`（不在本目录内）：

- **push 到 main/master** 且本包的 `version` / `rpm-packaging/**` / `build-rpm.sh`
  （或工作流本身）发生变化 → 自动构建本包。
- **手动触发（Run workflow）** → 选择 `package`（可为 `dingtalk` 或 `all`），可勾选
  `force_release` 强制重发，并可选择构建镜像 (`fedora_image`，默认 `fedora:latest`)
  与发布标签 (`dist_tag`，如 `.fc45` / `none` / 留空)。
- 从 `version` 下载 deb 后统一命名为 `com.alibabainc.dingtalk_<版本>_<架构>.deb`。
- **发布策略**：本包 Release 的 tag 为 `dingtalk-v<版本>`；若已存在对应 Release，则
  **只上传 artifact、不重复发布**；只有版本变化时才创建新 Release。
- 构建后会用 `dnf install --setopt=tsflags=noscripts` 做依赖校验，确保依赖可解析。

### 目录结构（dingtalk 子目录）

```
dingtalk/
├── version                                        # deb 下载地址（改这里升级版本）
├── build-rpm.sh                                   # 一键构建脚本
├── rpm-packaging/
│   ├── SPECS/com.alibabainc.dingtalk.spec
│   └── helpers/                                   # 适配后的安装/卸载脚本
└── README.md
```

> CI 工作流见仓库根目录 `.github/workflows/build-rpm.yml`。

## 转换方式

- 数据载荷：直接复用 deb 内的 `data.tar.xz`，二进制文件按原样安装（不 strip、
  不改写、不重定位 rpath）。
- 维护脚本：deb 的 `preinst/postinst/prerm/postrm` 被移植到 RPM 的
  `%pre/%post/%preun/%postun` 脚本片段，并作为
  `/usr/libexec/com.alibabainc.dingtalk/` 下的脚本随包安装（`%post`/`%preun` 调用它们）。
- 依赖：以 rpm 自动从 ELF 生成（包内自带 Qt5/CEF/ffmpeg/NSS 等库，通过包内
  Provides 满足），并显式排除 Fedora 已不再提供的旧 soname。

## 针对 Fedora/RHEL 的适配点

1. **自带库裁剪（重要）**：官方 deb 的 `postinst` 会在安装时按系统 glibc/
   发行版删除包内自带的部分库。这里把同样的意图放到**构建阶段**处理，并统一为
   现代 Fedora/RHEL 的规则：
   - 删除自带的 `libstdc++.so.6*`（自带为 GCC6，最高 `GLIBCXX_3.4.25`）。
     主程序 `RUNPATH` 为 `./plugins/dtwebview/:./`，会优先加载同目录自带库，
     若保留旧 `libstdc++` 会挡住系统较新库，导致依赖它新符号的组件加载失败。
   - 删除自带的 `libm.so.6`、`libgbm.so*`、`libGLX.so*`、`libGLdispatch.so*`，
     统一使用系统实现（与 deb 在“较新 glibc + 非麒麟/国产发行版”下的行为一致）。
2. **chrome-sandbox 权限**：CEF 沙箱需要 `plugins/dtwebview/chrome-sandbox` 具备
   setuid 权限。构建时将其置为 `4755`，由 RPM 记录并在安装时自动恢复
   （`%post` 中再做一次兜底），保证沙箱可用。
3. **桌面集成**：沿用官方行为，把 `com.alibabainc.dingtalk.desktop` 复制到各用户
   的桌面目录（优先读取 `~/.config/user-dirs.dirs` 的 `XDG_DESKTOP_DIR`，并兼容
   中文“桌面”目录）；卸载时清理。安装/卸载脚本会尝试刷新桌面与图标缓存。
4. **包名/路径**：RPM 包名沿用上游 `com.alibabainc.dingtalk`，安装路径与 deb 一致
   （`/opt/apps/com.alibabainc.dingtalk`），便于与应用内的绝对路径引用保持一致。
5. **旧 soname 依赖排除**：排除 Fedora 已不再提供的旧 soname（`libpangox-1.0.so.0`、
   `liblber-2.4.so.2`、`libldap_r-2.4.so.2`），使依赖在 Fedora/RHEL 上可解析
   （见「已知限制」）。

## 已验证

- `dnf install` / `dnf remove` 均成功，退出码 0；`rpm -V` 校验无差异。
- 主程序 `com.alibabainc.dingtalk` 在安装目录下 `ldd` 无 missing。
- `chrome-sandbox` 安装后为 `-rwsr-xr-x`（root:root，setuid 生效）。
- 桌面快捷方式正确安装到 `/usr/share/applications/`，并在卸载时清理。
- 排除旧 soname 后，RPM 元数据依赖在干净的 Fedora 上可解析（`dnf install` 依赖校验通过）。

## 已知限制

- 自带的旧 GTK2-glext 库（`libgtkglext-x11-1.0.so.0` 等）依赖 Fedora 已不再提供的
  `libpangox-1.0.so.0`，相关依赖已被排除。普通的聊天/会议主界面（Qt/CEF）不受影响；
  仅使用极老旧的 GTK2 GL 控件时可能缺少该库。
- **自带 `libcurl.so.4` 依赖 OpenLDAP 2.4**（经 `libDingGuard_SDK_UOS.so` 间接使用）：
  它需要 `liblber-2.4.so.2`/`libldap_r-2.4.so.2` 的 `OPENLDAP_2.4_2` 版本符号，而
  Fedora 只提供 OpenLDAP 2.6（`openldap-compat` 也没有该版本符号）。因此这两个依赖
  已被排除，`libcurl`/DingGuard 相关功能在 Fedora 上不可用（主界面、会议、聊天不受
  影响，它们不加载该库）。如需该功能，可把 Ubuntu `libldap-2.4-2` 的三个 `.so`
  一并打入 `/opt/apps/com.alibabainc.dingtalk/files/<版本>/`（其 `RUNPATH` 为 `./`）。
- 未对 Wayland 下的全局快捷键、通知等桌面集成做额外适配，行为与官方 deb 一致。

