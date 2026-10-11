# Linux 客户端 deb → rpm 打包仓库

把厂商提供的 Ubuntu/Debian `.deb` 安装包重新打包为 Fedora / RHEL 系的 RPM，
并针对 rpm 发行版做安装/卸载脚本适配。仓库采用**单仓多包**结构：每个应用一个
子目录，各自包含打包脚本与 spec，仓库根目录的 GitHub Actions 工作流可按需
构建任意一个（或全部）包。

## 包列表

| 子目录 | RPM 包名 | 说明 |
| --- | --- | --- |
| [`atrust/`](atrust/) | `cn.com.sangfor.atrust` | 深信服 aTrust SDP/SSL VPN 客户端 |
| [`dingtalk/`](dingtalk/) | `com.alibabainc.dingtalk` | 钉钉（DingTalk）客户端 |
| [`WeMeet/`](WeMeet/) | `wemeet` | 腾讯会议（Tencent Meeting）客户端 |

## 目录结构

```
.
├── .github/workflows/build-rpm.yml   # 单仓多包 CI：可选构建 atrust / dingtalk / 全部
├── atrust/
│   ├── version                       # deb 下载地址（改这里升级版本）
│   ├── build-rpm.sh                  # 一键构建脚本
│   ├── rpm-packaging/
│   │   ├── SPECS/*.spec
│   │   └── helpers/                  # 适配后的安装/卸载脚本
│   ├── README.md
│   └── .gitignore
├── dingtalk/
│   ├── version
│   ├── build-rpm.sh
│   ├── rpm-packaging/
│   │   ├── SPECS/com.alibabainc.dingtalk.spec
│   │   └── helpers/
│   ├── README.md
│   └── .gitignore
└── WeMeet/
    ├── version
    ├── build-rpm.sh
    ├── rpm-packaging/
    │   ├── SPECS/wemeet.spec
    │   └── helpers/
    ├── README.md
    └── .gitignore
```

## 本地构建

各包独立构建，进入对应目录执行：

```bash
cd atrust    && ./build-rpm.sh      # 或 ./build-rpm.sh -d /path/to.deb
cd dingtalk  && ./build-rpm.sh      # 或 ./build-rpm.sh -d /path/to.deb
```

产物输出到各包的 `dist/`：二进制 RPM、源码 RPM、下载的 deb（统一重命名）、
`SHA256SUMS.txt`、`VERSION`、`ARCH`。

## GitHub Actions 自动构建

工作流位于仓库根目录 `.github/workflows/build-rpm.yml`：

- **push 到 main/master** 且某个包的 `version` / `rpm-packaging/**` / `build-rpm.sh`
  （或工作流本身）发生变化 → 自动构建**受影响的包**；仅工作流变化时构建全部。
- **手动触发（Run workflow）**：可选择 `package`（`all` / `atrust` / `dingtalk` / `wemeet`），
  并可选 `force_release` 强制重发、`fedora_image` 构建镜像、`dist_tag` 发布标签。
- **发布策略**：每个包独立打 tag（`<包名>-v<版本>`）。该版本若已存在对应 Release，
  则只上传 artifact、不重复发布；版本变化时才创建新 Release。
- 构建后使用 `dnf install --setopt=tsflags=noscripts` 做依赖校验。

> 提示：本仓库根目录需是一个 GitHub 仓库；`atrust/` 与 `dingtalk/` 作为普通子目录
> 提交（不要把某个应用再作为独立的嵌套 git 仓库提交，否则 CI 检出的将是空的
> gitlink 目录）。
