# xts-gate-windows

给 Claude Code 的 XTS 门禁编译 + 上库前检查 skill。

## 它解决什么

1. **在 Windows 上得到与门禁一致的编译条件**：Windows 负责编辑，WSL Ubuntu 内用**门禁 Linux 工具链**（Linux SDK / Linux hvigor / node 18.20.1）编译。Windows 原生 hvigor 只做语法参考，不作为门禁结论。
2. **完善 XTS 工程**：BUILD.gn、module.json5、Test.json、syscap、hypium、动态/静态目录与类型规则；system API 用例走 HITS 独立仓（闭源，流程以 HITS 团队为准）+ `Hits` 前缀 + 系统签名。
3. **上库前检查**：可运行的 `check_xts_project.py`，覆盖门禁最容易拦的工程/配置/代码问题，包括仓/前缀不一致、工程携带 `.hsp` 等预编译二进制。

## 安装

### npm（推荐）

```powershell
npx -y xts-gate-windows@latest install
```

默认安装到 `%USERPROFILE%\.claude\skills\xts-gate-windows`；自定义目录：

```powershell
npx -y xts-gate-windows@latest install --dest D:\claude-skills
```

### 手动

把整个目录放到 Claude Code 的 skills 目录：

```text
%USERPROFILE%\.claude\skills\xts-gate-windows\
  SKILL.md
  references\
  scripts\
  templates\
```

或解压 `xts-gate-windows.zip` 到该目录。重启/新开 Claude Code 会话后，描述里出现 “XTS 门禁 / WSL 编译 / XTS 上库” 即会被加载。

## 前置

- Windows 10/11 + WSL2（Ubuntu 22.04/24.04）
- WSL 内：Linux SDK（门禁同版本，如 26.1.0.x）、`command-line-tools 26.0.1.290`（hvigor 6.26.21）、`node 18.20.1-linux-x64`、JDK 17
- 静态还需要 `7.26.0-arkts1.2-0601-02` 工具包（华为云镜像可下，解压为 `7.26.0.static/hvigor`，与门禁布局一致）

## 快速开始

```powershell
# 1) 工程检查（Windows 或 WSL 均可）
python .\scripts\check_xts_project.py E:\path\to\ActsXxxTest

# 2) WSL 门禁编译（Windows 侧包装）
.\scripts\run-gate-build.ps1 -Distro Ubuntu `
  -Project /root/ohos-gate/ws/test/xts/acts/.../ActsXxxTest `
  -Mode dyn `
  -NodeHome /root/ohos-gate/toolchain/node-v18.20.1-linux-x64 `
  -SdkRoot /root/ohos-gate/sdk `
  -HvigorHome /root/ohos-gate/toolchain/clt-26.0.1.290/hvigor `
  -JavaHome /usr/lib/jvm/java-17-openjdk-amd64
```

静态：`-Mode sta`，`-HvigorHome` 指向 `.../hvigor-static/7.26.0.static/hvigor`；工程需用门禁静态模板配置（`modelVersion "26.0.0"`、`compileSdkVersion "26.1.0"`、`compatibleSdkVersion "22"`）。

## 文件

```
SKILL.md
references/
  windows-gate-build.md      WSL + Linux 工具链、SDK 解压、命令、坑位
  project-completion.md      BUILD.gn/配置/代码/注册规则
  pre-submit-checklist.md    上库前逐项清单
  system-api-hits.md         system API：HITS 仓、Hits 命名、系统签名（闭源仓不推测）
  gate-error-catalog.md      门禁错误原文 → 根因 → 修复
scripts/
  check_xts_project.py       工程检查器
  run-gate-build.sh          WSL 内编译
  run-gate-build.ps1         Windows 调用 WSL
  fetch-static-toolchain.sh  自动选镜像最新 7.26* 并下载/解压（--list 查看候选）
  preflight.sh               四件套自检（只检查，不下载）
templates/
  BUILD.gn.dynamic / BUILD.gn.static
  Test.json / module.json5.snippet
  local.properties.example / hvigor-config.json5.example
  CLAUDE.md.snippet                 整仓下载禁令（复制到项目/全局 CLAUDE.md）
  block-full-repo-download.js       PreToolUse hook，拦截 repo sync / prebuilts_download
  claude-settings.hooks.json.example
```

## 验证状态

- 2026-11-26，一对真实动态/静态 XTS suite 在 WSL + 门禁 hvigor 6.26.21 + node 18.20.1 下动态 `BUILD SUCCESSFUL`。
- 同批静态 suite 在 WSL + 公开 `7.26.0-arkts1.2-0601-02` 工具（解为 `7.26.0.static/hvigor`）+ Linux SDK 26.1.0 + 门禁静态模板配置下 `BUILD SUCCESSFUL`（`.hap` 472902 B、`.app` 240239 B）。
- 该公开包与门禁 `7.26.0.static` 属同一 7.26.0 ArkTS 1.2 线，但文件名不同，字节一致性未证明；最终以门禁 CI 为准。
- Windows 原生 hvigor 路径未作为门禁一致方案；本 skill 不使用它下结论。

## 发布

把本目录（或同内容 zip）发给邱老师即可。建议同时附上：

- `references/windows-gate-build.md`
- `scripts/check_xts_project.py`
- 一个真实套件的检查输出示例
