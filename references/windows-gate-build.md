# Windows 宿主 + WSL 门禁编译环境

> **唯一门禁一致路线：Windows 上编辑，WSL Ubuntu 内用 Linux 工具链编译。**
> Windows 原生 hvigor/DevEco 只能做语法参考，不能作为门禁结论。

## 1. 门禁到底怎么编

```
test/xts/acts/build.sh
  └─ build.py（xts_acts）
       ├─ generate_accurate_targets（change_info.json；无变更信息则全量）
       └─ ./build.sh --build-only-gn ... --build-target <ActsXxx> deploy_testtools
            └─ OpenHarmony build.py / hb
                 ├─ gn gen（加载整个产品图）
                 ├─ gn desc deps --tree（筛出 //test/xts/acts 目标）
                 └─ ./build.sh --fast-rebuild（ninja）
                      └─ build/scripts/compile_app.py
                           ├─ ohpm install
                           ├─ 写 local.properties（sdk.dir / nodejs.dir）
                           └─ hvigorw ...
```

关键结论：

- `build.py` 用 `xts_acts/../../..` 定位 OpenHarmony 根目录，`gn gen` 会加载产品全图；**只靠 xts_acts 仓库跑不了全链路**。
- 真正编译 ArkTS 的是 `compile_app.py` 调用的 hvigor：
  - 动态（`test_hap = true`）：
    `hvigorw --mode module -p module=entry@ohosTest assembleHap -p debuggable=false -p hvigor-obfuscation=false --no-daemon`
  - 静态（`test_hap` 注释）：
    `hvigorw --mode project -p product=default assembleApp -p debuggable=false -p hvigor-obfuscation=false --no-daemon`
- 门禁工具版本（`build/prebuilts_config.json` / 构建脚本）：
  - dynamic：`prebuilts/tool/command-line-tools/26.x`（`command-line-tools.tar` v26.0.1.290，hvigor 6.26.21），node `v18.20.1`
  - static：`prebuilts/hvigor/7.26.0.static/hvigor`（公开镜像 `7.26.0-arkts1.2-0601-02`，解压即得，见 3.2）
  - SDK：`prebuilts/ohos-sdk/linux/<version>`（每日 `ohos-sdk-full[_Dyn_Sta]`）
  - Java：门禁构建环境自带

### 1.1 门禁目标选择

- 门禁用 `change_info.json` 计算变更影响的 XTS 目标；没有该文件时使用传入的 `suite`（可以是 target 或 group）。
- `build.py` 会额外追加 `deploy_testtools`，并先 `--build-only-gn` 再 `gn desc` 过滤 `//test/xts/acts` 下的目标。
- 未在 BUILD.gn/父 group/`test_targets.gni` 注册的 suite **不会被编**，日志里看不到 target 就是“假通过”。
- 本地叶子编译只验证 hvigor/HAP；它不替代门禁的 GN 目标计算与打包归档。
- system API 用例走 HITS 独立仓（闭源）；其构建/提交命令以 HITS 团队/CI 为准，**不要猜测**。WSL 叶子编译（hvigor 命令）本身与 acts 相同，但仓内注册/打包流程不同。
- 工程不得携带 `.hsp`/`.hap`/`.har`/`.so`/`.abc`/`.jar` 等预编译二进制；所有模块必须门禁源码编译。

## 2. 为什么必须在 WSL

| 维度 | 门禁 | Windows 原生 hvigor |
|------|------|---------------------|
| 宿主 | Linux | Windows |
| SDK | Linux SDK 26.1.0.x | Windows SDK，版本/布局可能不同 |
| hvigor | 6.26.21（动态）/ 7.26.0 ArkTS1.2（静态，包内 5.14.2-td-rc.2851） | DevEco 自带 6.x/5.14.2，schema/编译器不同 |
| 文件系统 | 大小写敏感 | 大小写不敏感，import 写错也能过 |
| 路径 | `/`、LF、符号链接 | `\`、CRLF、junction |
| 门禁检查 | BUILD.gn 注册、schema、syscap、hap 命名、Test.json、part 归属 | 完全不经过 |

因此：**Windows 原生 `BUILD SUCCESSFUL` 不能作为门禁证据**。WSL 内用 Linux 工具链得到的结论才可信。

## 3. WSL 环境

### 3.1 确认 WSL

```powershell
wsl -l -v
wsl -d Ubuntu -e bash -lc "uname -a && df -h /"
```

建议 Ubuntu 22.04/24.04，x86_64，至少 20 GB 可用空间。

### 3.2 组件（WSL 内）

```bash
# 统一放在 /root/ohos-gate（或任意 ext4 路径，不要放 /mnt/c）
/root/ohos-gate/
  toolchain/
    node-v18.20.1-linux-x64/
    clt-26.0.1.290/                  # command-line-tools 26.0.1.290
    hvigor-static/7.26.0.static/hvigor/  # 静态：7.26.0-arkts1.2 包，按门禁布局
  sdk/
    26.1.0/                          # 门禁 Linux SDK：{ets,js,native,previewer,toolchains}
```

下载来源（已授权时）：

```bash
curl -L -o node-v18.20.1-linux-x64.tar.gz \
  https://repo.huaweicloud.com/nodejs/v18.20.1/node-v18.20.1-linux-x64.tar.gz

curl -L -o command-line-tools-26.0.1.290.tar \
  https://repo.huaweicloud.com/harmonyos/compiler/hvigor/26.0.1.290/command-line-tools.tar

# 静态：7.26.0 ArkTS 1.2 工具包（约 313 MB，sha256 见同目录 .sha256）
curl -L -o command-line-tools-7.26.0.tar \
  https://repo.huaweicloud.com/harmonyos/compiler/hvigor/7.26.0-arkts1.2-0601-02/command-line-tools.tar
mkdir -p /root/ohos-gate/toolchain/hvigor-static/7.26.0.static/hvigor
tar -xf command-line-tools-7.26.0.tar -C /root/ohos-gate/toolchain/hvigor-static/7.26.0.static/hvigor
```

SDK 优先用本地已有 Linux SDK；没有则从每日构建 `ohos-sdk-full[_Dyn_Sta]` 包解压 linux 组件。

### 3.3 SDK 解压（保留 Linux 权限位）

Windows 解压会丢可执行位。在 WSL 里用 Python `zipfile` 按 `external_attr` 恢复权限：

```bash
python3 -I extract_sdk.py /root/ohos-gate/sdk/26.1.0 \
  /mnt/e/HW/projects/linux/ets-linux-x64-*.zip \
  /mnt/e/HW/projects/linux/js-linux-x64-*.zip \
  /mnt/e/HW/projects/linux/native-linux-x64-*.zip \
  /mnt/e/HW/projects/linux/previewer-linux-x64-*.zip \
  /mnt/e/HW/projects/linux/toolchains-linux-x64-*.zip
```

`extract_sdk.py` 参考实现见本文件 §3.6。

解压后确认：

```bash
ls -l /root/ohos-gate/sdk/26.1.0/toolchains/restool   # 应有 x 位
ls /root/ohos-gate/sdk/26.1.0/ets/static/build-tools/driver/build-system/dist/entry.js
```

### 3.4 26.1.0.22 的布局坑

hvigor 6.26.21 期望 `ets/build-tools/ets-loader`；26.1.0.22 是 `ets/dynamic/build-tools/ets-loader`。建兼容链接：

```bash
ln -sfn dynamic/build-tools /root/ohos-gate/sdk/26.1.0/ets/build-tools
```

否则 `OhosTestBuildArkTS` 会报 `spawn .../node ENOENT`（cwd 不存在）。26.1.0.27+ 通常已是新布局。

### 3.5 Java

```bash
sudo apt-get update -qq
sudo apt-get install -y openjdk-17-jre-headless   # 或 jdk
java -version
```

仅 HAP 打包阶段需要；没有会报 `spawn java ENOENT`。

### 3.6 extract_sdk.py 参考实现

```python
import os, sys, zipfile
dest = sys.argv[1]
for zp in sys.argv[2:]:
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            name = info.filename
            if name.startswith('/') or '..' in name.split('/'):
                raise SystemExit('unsafe path: ' + name)
            target = os.path.join(dest, name)
            mode = (info.external_attr >> 16) & 0o7777
            if name.endswith('/'):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                link = z.read(info).decode()
                if os.path.lexists(target):
                    os.remove(target)
                os.symlink(link, target)
            else:
                with z.open(info) as src, open(target, 'wb') as out:
                    while True:
                        b = src.read(1024 * 1024)
                        if not b:
                            break
                        out.write(b)
                if mode:
                    os.chmod(target, mode)
```

### 3.7 ohpm 依赖与 registry（hypium / hamock）

7.26 静态工具包自带的 ohpm 5.3.2，默认 registry 是华为内网地址：

```text
https://cmc.centralrepo.rnd.huawei.com/artifactory/api/npm/product_npm/
https://mirrors.tools.huawei.com/ohpm/
https://cmc.centralrepo.rnd.huawei.com/artifactory/api/ohpm/ohpm-center/
https://cmc.centralrepo.rnd.huawei.com/artifactory/api/npm/npm-central-repo/
```

外网解析不到（`getaddrinfo ENOTFOUND`），`ohpm install` 会报成包缺失：

```text
ERROR: NOTFOUND package '@ohos/hypium@1.0.25' not found from all the registries ...
ERROR: missing: @ohos/hamock@1.0.0, required by @
```

**包本身存在**：公开 registry 有 `@ohos/hypium` 1.0.25 和 `@ohos/hamock` 1.0.0（含 1.0.0-rc），tarball 可下载。修复是改 registry：

```bash
# 工程根目录 .ohpmrc
registry=https://ohpm.openharmony.cn/ohpm/

# 或写入用户配置
ohpm config set registry https://ohpm.openharmony.cn/ohpm/
```

实测（`business_1`，7.26 包内 ohpm）：默认 registry 失败；加 `.ohpmrc` 后 0.6 s 安装成功，`oh_modules/@ohos/{hamock,hypium}` 就位。

另外两点：

- 48 个 HSP 夹具模块的 `oh-package.json5` 里 `devDependencies` 的 `@ohos/hypium` / `@ohos/hamock` 在源码中没有 import，HSP 库本身不需要；门禁环境无外网时可直接删掉这两个 devDependencies（本会话 `assembleHsp` 在无 `oh_modules` 时也 `BUILD SUCCESSFUL`）。测试套（entry）才需要 hypium。
- command-line-tools 26.0.1.290 的 ohpm 在 node 18.20.1 下会 `ERR_REQUIRE_ESM`（`uuid` 是 ESM）；用 7.26 包内的 ohpm 5.3.2 或 DevEco 自带 ohpm。

## 4. 工程布局

门禁编译要求工程能解析到 hypium har：

```
<ws>/test/xts/acts/.../<suite>/
<ws>/test/xts/tools/hypium_prepare/hypium-{dynamic,static}.har
```

`oh-package.json5` 里是 `file:../../../../../tools/hypium_prepare/*.har`，从 suite 目录向上 5 级必须正好是 `test/xts`。如果不满足，把工程放到正确的深度，或在 WSL 内建同样的目录结构（不要改交付工程的相对路径）。

## 5. 编译命令（WSL 内）

```bash
export DEVECO_NODE_HOME=/root/ohos-gate/toolchain/node-v18.20.1-linux-x64
export PATH=$DEVECO_NODE_HOME/bin:$PATH
export OHOS_BASE_SDK_HOME=/root/ohos-gate/sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

cd <suite>
# 动态
/root/ohos-gate/toolchain/clt-26.0.1.290/bin/hvigorw \
  --mode module -p module=entry@ohosTest assembleHap \
  -p debuggable=false -p hvigor-obfuscation=false --no-daemon
# 产物：entry/build/default/outputs/ohosTest/entry-ohosTest-unsigned.hap

# 静态（门禁 7.26.0 ArkTS 1.2 工具链）
/root/ohos-gate/toolchain/hvigor-static/7.26.0.static/hvigor/bin/hvigorw \
  --mode project -p product=default assembleApp \
  -p debuggable=false -p hvigor-obfuscation=false --no-daemon
# 产物：entry/build/default/outputs/default/entry-default-unsigned.hap
#       <suite>/build/outputs/default/<suite>-default-unsigned.app
```

静态工程配置必须与当前门禁静态模板一致（三者要一起改）：

```json5
// build-profile.json5（products[0]）
"compatibleSdkVersion": "22",
"compileSdkVersion": "26.1.0",
"arkTSVersion": "1.2"

// hvigor/hvigor-config.json5 与 oh-package.json5
"modelVersion": "26.0.0"
```

> 用 7.26.0 工具链实测：`modelVersion` 仍是 `6.0.0` 时，字符串 `compatibleSdkVersion "22"` 会触发 `00306042`；改到 `26.0.0` 后同一工程 `BUILD SUCCESSFUL`。本地 hvigor 5.14.2 的 `modelVersion "6.1.1"` / 数字版本号只适用于老的近似环境，不要写进交付工程。

## 6. Windows 侧包装

```powershell
# 从 Windows 调 WSL 编译（脚本内部只调用 wsl，不跑 Windows hvigor）
.\scripts\run-gate-build.ps1 -Distro Ubuntu -Project /root/ohos-gate/ws/.../<suite> -Mode dyn
```

脚本参数见 `scripts/run-gate-build.ps1 -Help`。

## 7. 故障速查

| 报错 | 根因 | 修复 |
|------|------|------|
| `spawn .../node ENOENT` | hvigor 找不到 SDK `ets/build-tools/ets-loader`（旧 SDK 布局） | 换 26.1.0.27+ 或建 `ets/build-tools` 链接 |
| `spawn java ENOENT` | WSL 无 JDK | `apt install openjdk-17-jre-headless` |
| `00306042` | API ≥26 用数字 compileSdkVersion；或 modelVersion 6.0.0 下用了字符串 compatibleSdkVersion | 静态模板：`modelVersion "26.0.0"` + `"26.1.0"` + `"22"`；动态：`"26.1.0"` |
| `00303028` | modelVersion 与 hvigor 不匹配 | 门禁动态/静态都用 `26.0.0`；老 5.14.2 近似环境才用 `6.1.1` |
| `Unable to find components ... 26.1.0` | SDK 目录名不是 `26.1.0` | SDK 根下建 `26.1.0/` |
| `ERR_REQUIRE_ESM`（ohpm） | node 18 与 ohpm 版本不匹配 | 用新版 node/ohpm，或手动安装 har |
| `F0019 Not supported path` | SDK 根用了 junction/symlink | 用真实目录或硬链接镜像 |
| `HAP 未生成` | `test_hap`/模板/输出路径不匹配 | 动态 `test_hap=true`；静态主模块 |
