# aTrust deb → rpm 转换说明（Fedora / RHEL）

将深信服官方 aTrust 的 `.deb` 安装包（`aTrustInstaller_amd64.deb`，2.5.16.30）
重新打包为 RPM，并针对 Fedora 45（及 RHEL 系）做了安装/卸载脚本适配，
保持客户端原有功能。

## 产物

| 文件 | 说明 |
| --- | --- |
| `cn.com.sangfor.atrust-2.5.16.30-1.fc45.x86_64.rpm` | 可直接安装的二进制 RPM（约 149 MiB，装后约 516 MiB） |
| `cn.com.sangfor.atrust-2.5.16.30-1.fc45.src.rpm` | 源码 RPM（内含 deb 原始数据包与适配脚本，可重新构建） |
| `rpm-packaging/SPECS/cn.com.sangfor.atrust.spec` | spec 文件 |
| `rpm-packaging/helpers/` | 从 deb 的 control 脚本移植并适配后的安装/卸载脚本 |
| `build-rpm.sh` | 一键从 deb 重新构建 RPM 的脚本 |

## 安装 / 卸载

```bash
# 安装（自动安装依赖，含弱依赖 lsb_release）
sudo dnf install ./cn.com.sangfor.atrust-2.5.16.30-1.fc45.x86_64.rpm

# 卸载
sudo dnf remove cn.com.sangfor.atrust

# 查看服务
systemctl status aTrustDaemon
```

安装日志：`/root/.aTrust/logs/aTrustInstallOut.log`

## 从 deb 重新构建（一键脚本，支持升级版本）

脚本会自动从 deb 的 control 里读取**版本号**和**架构**。默认读取仓库根目录的 `version` 文件
（内容为 deb 下载地址），升级时改 `version` 里的地址再跑一次即可：

```bash
./build-rpm.sh                        # 读 version 文件里的 URL 下载并构建
./build-rpm.sh -d /path/new.deb       # 指定本地 deb
./build-rpm.sh -u https://.../x.deb   # 指定 URL
./build-rpm.sh -v 2.5.17.1 -r 2       # 覆盖版本号 / Release 号
./build-rpm.sh -a aarch64             # 覆盖目标架构（需在对应架构主机上构建）
./build-rpm.sh --dist .fc45           # 指定发布标签（默认用构建机/Fedora 镜像的 %dist）
./build-rpm.sh --dist none            # 去掉标签，产出发行版无关的包名
```

产物输出到 `dist/`：二进制 RPM、源码 RPM、`SHA256SUMS.txt`、`VERSION`、`ARCH`。

## version 文件

仓库根目录的 `version` 文件是**版本来源的唯一入口**，单行内容为 deb 下载地址，例如：

```
https://atrustcdn.sangfor.com/standard/linux/2.5.16.30/ubuntu/amd64/aTrustInstaller_amd64.deb
```

升级版本时只需改这一行并提交，CI 会自动构建。**下载后会统一重命名为
`aTrustInstaller_<版本>_amd64.deb`**（例如 `aTrustInstaller_2.5.16.30_amd64.deb`），
并连同 RPM 一起输出到 `dist/`。

## GitHub Actions 自动构建

工作流 `.github/workflows/build-rpm.yml`：

- **push 到 main/master 且 `version` 文件有变化** → 自动构建。
- **手动触发（Run workflow）** → 可勾选 `force_release` 强制重发，并可选择构建镜像
  (`fedora_image`，默认 `fedora:latest`) 与发布标签 (`dist_tag`，如 `.fc45` / `none` / 留空)。
- 从 `version` 下载 deb 后统一命名为 `aTrustInstaller_<版本>_amd64.deb`。
- **发布策略**：构建出的版本若已存在 `v<版本>` 的 Release，则**只上传 artifact、不重复发布**；
  只有版本变化时才创建新 Release（tag 为 `v<版本>`，附带 RPM、deb 与校验和）。
- 构建后会用 `dnf install --setopt=tsflags=noscripts` 做依赖校验，确保依赖可解析。

### 仓库目录结构

```
.
├── .github/workflows/build-rpm.yml   # CI 工作流
├── version                           # deb 下载地址（改这里升级版本）
├── build-rpm.sh                      # 一键构建脚本
├── rpm-packaging/
│   ├── SPECS/cn.com.sangfor.atrust.spec
│   └── helpers/                      # 适配后的安装/卸载脚本
└── README.md
```


## 转换方式

- 数据载荷：直接复用 deb 内的 `data.tar.xz`，二进制文件按原样安装（不 strip、
  不改写、不重定位 rpath）。
- 维护脚本：deb 的 `preinst/postinst/prerm/postrm`、`common`、`create_dir`
  被移植到 RPM 的 `%pre/%post/%preun/%postun` 脚本片段，并作为
  `/usr/libexec/cn.com.sangfor.atrust/` 下的脚本随包安装（`%post` 等调用它们）。
- 依赖：由 rpm 自动从 ELF 生成（包内自带 Qt5/OpenSSL1.1/NSS/boost 等库，
  通过包内 Provides 满足），并显式排除 Fedora 已不再提供的旧 soname。

## 针对 Fedora/RHEL 的适配点

1. **发行版检测**：优先使用 `/etc/os-release`，`lsb_release` 作为兜底
   （`lsb_release` 作为弱依赖，缺失也不影响安装）。
2. **C++ 运行库**：官方脚本会在系统 libstdc++ 较新时删除包内自带的
   `libstdc++.so.6`。原脚本用 `dpkg-query` 查询版本，这里改为读取系统
   `libstdc++` 的最高 `GLIBCXX` 版本判断（Fedora 上结果一致，会删除自带库）。
3. **服务管理**：`aTrustDaemon` 通过 systemd 启用并启动，与 Ubuntu 版一致。
4. **以普通用户启动托盘**：RPM 环境通常没有 `sudo`，改用 util-linux 的
   `runuser`（无则回退 `sudo`）。
5. **证书**：原 deb 只把 `sangfor2024.crt` 放进 deepin 应用商店证书目录；
   这里额外将其安装到 Fedora 系统信任库
   `/etc/pki/ca-trust/source/anchors/` 并执行 `update-ca-trust`，
   保证本地 `https://localhost.sangfor.com.cn`（已写入 `/etc/hosts`）可信。
6. **GPU 兼容**：在虚拟机 / 远程桌面等没有可用 GPU 进程的环境下，Electron
   托盘会因 “GPU process isn't usable” 崩溃。已在桌面快捷方式和
   `aTrustTrayStart.sh` 中为启动参数增加 `--disable-gpu-sandbox`（客户端本就
   使用 `--no-sandbox`），避免托盘崩溃。
7. **升级时序**：修正 dpkg 与 rpm 的升级脚本执行顺序差异——升级时不再由旧包
   `%preun` 停止服务（避免把新包 `%post` 刚启动的服务杀掉），真正停服只在卸载时。
8. **字体方框（重要）**：Fedora 默认只提供**可变字体** `Noto Sans CJK VF`，
   而客户端内置的旧版 Electron/Chromium 无法渲染可变字体，导致界面所有文字
   （含英文、数字）显示为方框。处理方式：
   - 依赖静态 CJK 字体 `google-noto-sans-cjk-fonts`；
   - 随包提供 `/etc/fonts/atrust-fonts.conf`，仅在 aTrust 进程内屏蔽
     `*-cjk-vf-fonts`，回退到静态 `Noto Sans CJK`；
   - 在桌面快捷方式和 `aTrustTrayStart.sh` 中为 aTrust 设置
     `FONTCONFIG_FILE=/etc/fonts/atrust-fonts.conf`（不影响系统其他程序）。
9. **图标**：额外把 `aTrust.png` 安装到 `hicolor` 主题，便于 GNOME/KDE 显示图标。
10. **桌面项**：保留官方 deb 的最终行为（`/usr/share/applications/...` 指向
    `/opt/apps/...`）。对没有内嵌主题名的通用安装包，官方脚本会保留原桌面文件，
    此处行为一致。
11. **接入地址无法记住（重要）**：客户端自带的 `libmmkv.so` 带有**可执行栈**
    (`PT_GNU_STACK=RWE`) 标记，新版 Fedora 内核/glibc 会拒绝加载
    （`cannot enable executable stack as shared object requires: Invalid argument`），
    导致历史/地址数据库（libmmkv）加载失败，表现为“接入地址重启后为空”。
    构建时用 `patchelf --clear-execstack` 去掉该标记即可（mmkv 并不需要可执行栈）。
    涉及 `BuildRequires: patchelf`，CI 与本地构建都会自动安装。
12. **库符号抢占导致崩溃（重要）**：客户端自带一些旧版库（`libsqlite3.so`=
    SQLCipher、`libcurl.so`、`libcrypto.so.1.1`），Fedora 上进程同时会加载系统同名
    库（`libtinysparql` 需要系统 `libsqlite3.so.0`；系统 `libcurl.so.4`/OpenSSL4），
    产生符号抢占，导致 SEGV（`sqlcipher_activate -> NULL`、SSL 回调 ABI 不一致）。
    处理方式（沿用官方对 aTrustCore 的 `LD_PRELOAD` 思路）：
    - 托盘：`/usr/libexec/cn.com.sangfor.atrust/run-tray` 包装脚本 + `aTrustTrayStart.sh`
      统一设置 `LD_PRELOAD=<内置 libsqlite3.so 内置 libcurl.so>`；
    - 守护进程：`aTrustDaemon.service` 的 `Environment=LD_PRELOAD=<内置 libcurl.so>`；
    - 所有 Qt 组件（aTrustTray2、uem_dialog 等）需要
      `QT_QPA_PLATFORM_PLUGIN_PATH=/usr/share/sangfor/aTrust/resources/lib`，
      否则会因找不到内置平台插件而 Abort；该变量在包装脚本、托盘脚本、守护进程内均设置。
    另外，为了让修复**不依赖启动方式**（桌面图标、菜单、守护进程等任何入口），
    构建时还给 `aTrustTray`/`aTrustTray2`/`aTrustAgent` 直接加入
    `DT_NEEDED`（`libcurl.so`、`libsqlite3.so`），使内置库在加载顺序上必然优先。

## 已验证

- `dnf install` / `dnf reinstall`（升级路径）均成功，退出码 0。
- `aTrustDaemon.service` 已 enable 且 active，`aTrustAgent`、`aTrustXtunnel-64`
  正常拉起。
- `/etc/hosts` 写入 `127.0.0.1 localhost.sangfor.com.cn`，证书已进系统信任库。
- 包内所有 ELF 依赖均可解析（`ldd` 无 missing）。
- Electron 托盘在虚拟显示（Xvfb）下可正常启动运行，界面中英文/数字均能正常显示（无方框）。
- `libmmkv.so` 可被 dlopen 加载；`visitHistory -q` 能返回已保存的接入地址
  （如 `https://vpn.xxx.com`），接入地址可持久化。
- 守护进程 `aTrustDaemon` 不再 SEGV 崩溃重启（MainPID 稳定、NRestarts=0）。
- Electron 托盘不再 SEGV；Qt 工作台 `aTrustTray2` 不再 Abort；托盘可正常连上服务器。

## 已知限制

- 客户端自带的老版本 OpenLDAP 库（`libldap_r-2.4.so.2`）依赖
  `libgcrypt.so.11`、`libgnutls.so.26`、`libsasl2.so.2`，这些 soname 已不在
  当前 Fedora 中。相关依赖已被排除，普通的 HTTPS/SPA 登录不受影响；
  若使用「LDAP 认证」相关功能可能缺少运行库。
- SPA 种子/服务器地址是官方安装器从「安装包文件名」中解析的。通用命名的
  包名不包含该信息（与 deb 一致）；如需从文件名携带地址，请在安装前按官方
  命名规则重命名 RPM（安装脚本会尽力从父进程命令行取回包名）。

## 手动安装后如需指定服务器地址

直接打开托盘客户端，在界面中填写服务器地址即可（与 deb 版行为一致）。
