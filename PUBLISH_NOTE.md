# 给邱老师的说明

这是 Claude Code 的 **XTS 门禁 Windows 编译 + 上库前检查** skill。

## 为什么强调 WSL

门禁是 Linux 上的 `build.py → GN/ninja → hvigor`。Windows 原生 hvigor 的 schema、SDK 版本、文件系统大小写规则都与门禁不同，**Windows 上编过不能作为门禁结论**。

本 skill 的唯一门禁一致路线是：

```text
Windows 编辑 → WSL Ubuntu → Linux SDK + 门禁 hvigor + node 18.20.1 → 门禁同款 hvigor 命令
```

## 安装

```powershell
npx -y xts-gate-windows@latest install
```

默认安装到 `%USERPROFILE%\.claude\skills\xts-gate-windows`。自定义目录：

```powershell
npx -y xts-gate-windows@latest install --dest D:\claude-skills
```

也可以解压后手动放到 `%USERPROFILE%\.claude\skills\xts-gate-windows\`。新开 Claude Code 会话即可被识别。

## 前置

- WSL2 Ubuntu 22.04/24.04
- WSL 内：门禁同版本 Linux SDK、`command-line-tools 26.0.1.290`（hvigor 6.26.21）、`node 18.20.1-linux-x64`、JDK 17
- 静态：华为云镜像的 `7.26.0-arkts1.2-0601-02` 工具包（约 313 MB），解压到 `7.26.0.static/hvigor`，与门禁 `prebuilts/hvigor/7.26.0.static/hvigor` 布局一致

## 两条上库规范（本 skill 已内置检查）

1. **system API 用例**：走 HITS 独立仓（闭源，仓名/构建/提交流程以 HITS 团队/CI 为准，不要猜），命名用 `Hits` 前缀，测试 HAP 必须系统签名；不要提交到 `xts_acts`。
2. **禁止预编译二进制**：工程内不得携带 `.hsp`、`.hap`、`.har`、`.so`、`.abc`、`.jar` 等；所有模块必须在门禁中从源码编译，HSP 依赖改为源码模块。

## 最快验证

```powershell
python .\scripts\check_xts_project.py <suite_dir>
```

```powershell
.\scripts\run-gate-build.ps1 -Distro Ubuntu `
  -Project /root/ohos-gate/ws/test/xts/acts/.../<suite> `
  -Mode dyn `
  -NodeHome /root/ohos-gate/toolchain/node-v18.20.1-linux-x64 `
  -SdkRoot /root/ohos-gate/sdk `
  -HvigorHome /root/ohos-gate/toolchain/clt-26.0.1.290/hvigor `
  -JavaHome /usr/lib/jvm/java-17-openjdk-amd64
```

## 验证状态

- WSL + 门禁 hvigor 6.26.21 + node 18.20.1：动态 `BUILD SUCCESSFUL`。
- WSL + 公开 7.26.0 ArkTS 1.2 工具 + Linux SDK 26.1.0 + 门禁静态模板配置：静态 `BUILD SUCCESSFUL`。
- `check_xts_project.py` 已用真实工程 + 反例夹具验证：BUILD.gn、schema、Test.json、syscap、大小写 import、`@tc.number`、`globalThis`、RPC 类型等均能报出。

## 先读

1. `SKILL.md`
2. `references/windows-gate-build.md`
3. `references/pre-submit-checklist.md`
4. `references/system-api-hits.md`（system API 用例）
5. `references/gate-error-catalog.md`
