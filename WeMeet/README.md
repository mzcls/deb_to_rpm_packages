# 腾讯会议 WeMeet deb → rpm 转换说明（Fedora / RHEL）

将腾讯会议官方 Linux 版 `.deb` 安装包
（`TencentMeeting_0300000000_3.26.10.401_x86_64_default.publish.officialwebsite.deb`）
重新打包为 RPM，并针对 Fedora 45（及 RHEL 系）做了安装/卸载脚本适配，
保持客户端原有功能。

> 目录结构参考同仓库的 `atrust/`、`dingtalk/`（单仓多包，CI 工作流位于仓库根目录）。

## 产物

| 文件 | 说明 |
| --- | --- |
| `wemeet-3.26.10.401-2.fc45.x86_64.rpm` | 可直接安装的二进制 RPM（约 201 MiB，装后约 662 MiB） |
| `wemeet-3.26.10.401-2.fc45.src.rpm` | 源码 RPM（内含 deb 原始数据包与适配脚本，可重新构建） |
| `rpm-packaging/SPECS/wemeet.spec` | spec 文件 |
| `rpm-packaging/helpers/` | 从 deb 的 control 脚本移植并适配后的安装/卸载脚本 |
| `rpm-packaging/patches/wemeet-dbus-race-fix.py` | Wayland 屏幕共享修复补丁（见下） |
| `build-rpm.sh` | 一键从 deb 重新构建 RPM 的脚本 |

## 安装 / 卸载

```bash
# 安装
sudo dnf install ./wemeet-3.26.10.401-2.fc45.x86_64.rpm

# 卸载
sudo dnf remove wemeet

# 启动
# 在应用菜单点击“腾讯会议”，或执行：
/opt/wemeet/wemeetapp.sh
```

安装日志：`/var/log/wemeet/rpm-install.log`

## Wayland 屏幕共享（重要：本包已修复）

官方客户端在 Wayland 下共享屏幕存在缺陷：`libscreen_share_module.so` 在
`xdg-desktop-portal` 的 ScreenCast 流程里，发出 `SelectSources` 后**未等待其
Response** 就调用 `Start`，属于竞态（未定义行为）。GNOME 的 portal 后端
（`xdg-desktop-portal-gnome`）恰好在 `SelectSources` 阶段同步设置参数、把选区
弹窗放到 `Start`，因而“掩盖”了该缺陷；但在部分后端上会导致共享直接失败或黑屏。

本包在**构建阶段**对 `libscreen_share_module.so` 应用社区补丁的
**Hunk 0**（`rpm-packaging/patches/wemeet-dbus-race-fix.py`），把 `Start` 调用移动到
`SelectSources` 的响应回调中，修复异步链。补丁来源：
[Matheritasiv/wemeet-screenshare-patch](https://github.com/Matheritasiv/wemeet-screenshare-patch)。

**为什么不打颜色格式补丁（Hunk 1a/1b）**：该补丁会把请求的 `BGRx` 篡改为
`RGBx` 并需要额外 `LD_PRELOAD` hook。而 GNOME 的 portal 后端原生支持 `BGRx`、
不提供 `RGBx`，打上后反而协商失败导致**白屏/黑屏**（见上游 issue #2、#3）。
因此本包**只应用 Hunk 0**，不引入 hook，也不会改动启动脚本。

使用前提（RPM 已声明依赖 / 建议）：

- `pipewire-libs`、`xdg-desktop-portal`（`Requires`）；
- GNOME 会话需 `xdg-desktop-portal-gnome`（`Recommends`，Fedora Workstation 默认已装）；
- 若共享时选区弹窗不出现或黑屏，请确认上述组件已安装且
  `systemctl --user status xdg-desktop-portal` 正常。

> 注意：该补丁的字节偏移针对 **wemeet 3.26.10.401**。升级到新版本后字节可能不再
> 匹配，构建日志会出现 `[wemeet-patch] WARNING: unrecognised WeMeet build` 并
> **跳过错补丁**（不会中断构建）——此时需要按上游补丁更新
> `rpm-packaging/patches/wemeet-dbus-race-fix.py` 中的偏移。

## 从 deb 重新构建（一键脚本，支持升级版本）

脚本会自动从 deb 的 control 里读取**版本号**和**架构**。默认读取本目录的 `version`
文件（内容为 deb 下载地址），升级时改 `version` 里的地址再跑一次即可：

```bash
./build-rpm.sh                              # 读 version 文件里的 URL 下载并构建
./build-rpm.sh -d TencentMeeting_*.deb      # 指定本地 deb
./build-rpm.sh -u https://.../x.deb         # 指定 URL
./build-rpm.sh -v 3.26.11 -r 2              # 覆盖版本号 / Release 号
./build-rpm.sh -a aarch64                   # 覆盖目标架构（需在对应架构主机上构建）
./build-rpm.sh --dist .fc45                 # 指定发布标签（默认用构建机/Fedora 镜像的 %dist）
./build-rpm.sh --dist none                  # 去掉标签，产出发行版无关的包名
```

产物输出到 `dist/`：二进制 RPM、源码 RPM、下载的 deb（统一重命名）、
`SHA256SUMS.txt`、`VERSION`、`ARCH`。

## version 文件

本目录的 `version` 文件是**版本来源的唯一入口**，单行内容为 deb 下载地址，例如：

```
https://updatecdn.meeting.qq.com/cos/72e0e0023e1d1e6d4123fba28821aea1/TencentMeeting_0300000000_3.26.10.401_x86_64_default.publish.officialwebsite.deb
```

该直链来自腾讯会议官网下载接口
`https://meeting.tencent.com/web-service/query-download-info`（参数 `q` 为
`[{"package-type":"app","channel":"0300000000","platform":"linux","arch":"x86_64","decorators":["deb"]}]`，
并带一个随机 `nonce`）。升级版本时改这一行并提交，CI 会自动构建。
**下载后会统一重命名为 `wemeet_<版本>_<架构>.deb`**，并连同 RPM 一起输出到 `dist/`。

## GitHub Actions 自动构建

本包已并入单仓多包（monorepo）结构，工作流统一放在**仓库根目录**
`.github/workflows/build-rpm.yml`（不在本目录内）：

- **push 到 main/master** 且本包的 `version` / `rpm-packaging/**` / `build-rpm.sh`
  （或工作流本身）发生变化 → 自动构建本包。
- **手动触发（Run workflow）** → 选择 `package`（可为 `wemeet` 或 `all`），可勾选
  `force_release` 强制重发，并可选择构建镜像 (`fedora_image`，默认 `fedora:latest`)
  与发布标签 (`dist_tag`，如 `.fc45` / `none` / 留空)。
- **发布策略**：本包 Release 的 tag 为 `wemeet-v<版本>`；若已存在对应 Release，则
  **只上传 artifact、不重复发布**；只有版本变化时才创建新 Release。
- 构建后会用 `dnf install --setopt=tsflags=noscripts` 做依赖校验，确保依赖可解析。

### 目录结构（WeMeet 子目录）

```
WeMeet/
├── version                                # deb 下载地址（改这里升级版本）
├── build-rpm.sh                           # 一键构建脚本
├── rpm-packaging/
│   ├── SPECS/wemeet.spec
│   ├── helpers/                           # 适配后的安装/卸载脚本
│   └── patches/                           # Wayland 屏幕共享修复补丁
└── README.md
```

> CI 工作流见仓库根目录 `.github/workflows/build-rpm.yml`。

## 转换方式

- 数据载荷：直接复用 deb 内的 `data.tar.xz`，二进制文件按原样安装（不 strip、
  不改写、不重定位 rpath）。
- 维护脚本：deb 的 `preinst/postinst/prerm/postrm` 被移植到 RPM 的
  `%pre/%post/%preun/%postun` 脚本片段，并作为 `/usr/libexec/wemeet/` 下的脚本
  随包安装（`%post`/`%preun` 调用它们）。
- 依赖：以 rpm 自动从 ELF 生成（包内自带 Qt5/WebEngine/ICU/OpenSSL1.1 等库，
  通过包内 Provides 满足）。

## 针对 Fedora/RHEL 的适配点

1. **图标**：官方 deb 的 `postinst` 用 `xdg-icon-resource` 把
   `/opt/wemeet/icons/hicolor/<size>/mimetypes/wemeetapp.png` 注册到系统
   `hicolor` 主题。这里在构建阶段直接安装到
   `/usr/share/icons/hicolor/<size>/mimetypes/wemeetapp.png`（16/32/64/128/256），
   卸载时由 RPM 自动清理，行为与官方一致。
2. **库加载路径**：主程序 `bin/wemeetapp` 的 `RUNPATH` 是一段厂商 CI 的绝对路径
   （不存在），实际依赖启动脚本 `wemeetapp.sh` 设置 `LD_LIBRARY_PATH=/opt/wemeet/lib`
   加载包内自带库。保持原样，未做改动。
3. **进程管理**：官方在安装阶段会 `pkill wemeetapp`。这里在 `%pre`（安装/升级前）
   结束旧进程，避免把正在运行的新版本误杀。
4. **桌面数据库/图标缓存**：安装后在 `%post`、卸载后在 `%postun` 调用
   `update-desktop-database` 与 `gtk-update-icon-cache` 刷新缓存（对应官方脚本里的
   `update-desktop-database`）。
5. **Wayland 屏幕共享**：构建阶段对 `libscreen_share_module.so` 应用 Hunk 0 补丁，
   修复 xdg-desktop-portal ScreenCast 的 D-Bus 竞态（详见「Wayland 屏幕共享」一节）。

## 已验证

- `dnf install` / `dnf remove` 均成功，退出码 0；`rpm -V` 校验无差异。
- 桌面快捷方式、hicolor 图标（5 个尺寸）随包安装并在卸载时清理。
- `wemeetapp.sh` 与 `bin/wemeetapp` 具备可执行权限。
- 依赖在 Fedora 上可解析（`dnf install` 依赖校验通过，无需额外下载系统库）。

## 已知限制

- 包内自带旧版库（`libcrypto.so.1.1`、`libicuuc.so.60`、`libjpeg.so.8`、
  `libpcre.so.3`、`libffi.so.6` 等），依赖启动脚本设置 `LD_LIBRARY_PATH` 优先加载。
  请通过应用菜单 / `wemeetapp.sh` 启动；直接执行 `bin/wemeetapp` 可能因找不到自带库
  而失败（与官方 deb 行为一致）。
- 大批量下载/会议等网络功能依赖系统 `libnss3`、`libgcrypt`、`libpulse` 等，
  这些已在上游 deb 的 `Depends` 中声明，rpm 会自动从 ELF 生成对应依赖。
- Wayland 屏幕共享补丁的偏移**仅匹配 wemeet 3.26.10.401**；升级版本后若字节不匹配会
  自动跳过（构建日志有告警），需要同步更新 `rpm-packaging/patches/`。
- 本包只修复共享屏幕的 D-Bus 竞态，不涉及颜色格式转换；在**非 GNOME** 且 pipewire
  协商不支持 `BGRx` 的后端上仍可能需要上游的颜色补丁（Hunk 1a/1b + hook）。
