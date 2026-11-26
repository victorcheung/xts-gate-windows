# 门禁错误目录：原文 → 根因 → 修复

> 以下错误来自真实门禁等价编译的归纳；文件/API 名已泛化为占位示例，错误码与原文可直接用于日志检索。

## 1. Schema

### 1.1 extensionAbilities 的 process

```text
00303038 Configuration Error
Schema validate failed ... module.json5
instancePath: 'module.extensionAbilities[0]'
params: { propertyName: 'process' }
message: 'property name must be valid'
```

**根因**：`process` 只允许在 `abilities[]`，`extensionAbilities[]` 不允许。
**修复**：删除 `"process": "xxx"`；需要独立进程改用：

```json5
"extensionProcessMode": "instance"   // bundle | type | instance
```

### 1.2 compileSdkVersion 类型

```text
00306042 Specification Limit Violation
For API versions 10 to 25 ... numeric
For API version 26 and later ... string (for example,'26.0.0')
```

**修复**：API ≥26 用 `"26.1.0"`/`"26.0.0"`；<26 用数字。

静态工程还有一个组合坑：`modelVersion` 仍是 `"6.0.0"` 时，`compatibleSdkVersion: "22"`（字符串）会报同一 `00306042`。把 `hvigor-config.json5` 和 `oh-package.json5` 的 `modelVersion` 改成 `"26.0.0"`，保留 `compileSdkVersion "26.1.0"`、`compatibleSdkVersion "22"` 即通过（7.26.0 ArkTS 1.2 工具实测）。

### 1.3 modelVersion 与 hvigor

```text
00303028 Configuration Error
```

**根因**：`hvigor-config.json5`/`oh-package.json5` 的 `modelVersion` 与 hvigor 代际不匹配。
**修复**：门禁动态/静态 → `"26.0.0"`；仅老 5.14.2 近似环境 → `"6.1.1"`。

### 1.4 alternateModule 字段不被 SDK schema 接受

```text
00303038 Configuration Error
property name must be valid
propertyName: 'alternateModule'
```

**根因**：`alternateModule` 是 API 26.1.0 的 `module.json5` 字段（应用间共享 HSP 的备用模块），但 SDK 的 `toolchains/modulecheck/module.json` 旧版本（如 26.1.0.22 Canary1）没有这个字段；hvigor 6.26.21 和 7.26.0 都会报。

**修复**：使用包含该字段的 SDK。提交前检查：

```bash
grep -c alternateModule <sdk>/toolchains/modulecheck/module.json   # 必须 > 0
```

仅本地验证时可以在 schema 的 `propertyNames.enum` 与 `properties.module.properties` 里补 `alternateModule`（备份原文件）；门禁不能依赖本地改 SDK，必须用新 SDK。

## 2. 接口 / 类型

### 2.1 callback 重载缺失

```text
10505001 ArkTS Compiler Error
Expected 1 arguments, but got 2.
At .../entry/src/ohosTest/ets/.../<ExtAbility>.ets
```

**根因**：测试按 spec 调用了某个带 callback 的参数重载，但 `interface/sdk-js` master 只有 Promise/单参重载。
**修复**：

1. 对照 spec 与接口仓，确认参数个数/类型；接口补齐缺失重载，例如：
   ```ts
   // 示例：替换为实际接口
   foo(connection: long, callback: AsyncCallback<void>): void;
   ```
2. 合入后刷新门禁 SDK。
3. **不要**为了本地编译删掉 spec 要求的用例；这是接口问题，不是测试问题。

### 2.2 动态工程误用 MessageSequence

```text
10505001 ArkTS Compiler Error
Property 'onRemoteRequest' in type 'TestRemoteObject' is not assignable to ...
Type '(code: number, data: MessageSequence, reply: MessageSequence, option: MessageOption) => boolean'
is not assignable to ...
Type 'MessageParcel' is missing ...
```

**修复**：动态改为：

```ts
onRemoteRequest(code: number, data: rpc.MessageParcel, reply: rpc.MessageParcel,
  option: rpc.MessageOption): boolean
```

静态保持 `rpc.MessageSequence`。

### 2.3 parameters 可能为 undefined

```text
10605999 ArkTS Compiler Error
'data.parameters' is possibly 'undefined'. At .../entry/src/.../<Utils>.ets
'eventData.parameters' is possibly 'undefined'. At .../entry/src/.../<ExtAbility>.ets
```

**修复**：

```ts
const params = data.parameters;
if (params === undefined) {
  return;
}
const caseName = params['case'] as string;
```

### 2.4 globalThis

```text
ArkTS:WARN ... "globalThis" is not supported (arkts-no-globalthis)
```

**修复**：删除 `globalThis.xxx`；用 `AppStorage`、成员变量或参数传递。

## 3. 环境

### 3.1 node spawn ENOENT（SDK 布局）

```text
00308018 Unknown Error
spawn /.../node ENOENT
Failed :entry:ohosTest@OhosTestBuildArkTS
```

**根因**：hvigor 6.26.21 以 `ets/build-tools/ets-loader` 为 cwd 启动 node；26.1.0.22 SDK 只有 `ets/dynamic/build-tools`，cwd 不存在。
**修复**：用 26.1.0.27+ 门禁 SDK；或在 WSL 的 SDK 内建兼容链接：

```bash
ln -sfn dynamic/build-tools <sdk>/26.1.0/ets/build-tools
```

### 3.2 java ENOENT（打包）

```text
00308018 Unknown Error
spawn java ENOENT
Failed :entry:ohosTest@PackageHap
```

**修复**：在 WSL 内安装 JDK 17 并设置 `JAVA_HOME`（如 `/usr/lib/jvm/java-17-openjdk-amd64`）；确保 `$JAVA_HOME/bin/java` 存在。

### 3.3 ohpm ERR_REQUIRE_ESM

```text
ERR_REQUIRE_ESM
```

**根因**：ohpm 26.0.1 与 node 18 不匹配。
**修复**：用新版 node/ohpm；或按 `windows-gate-build.md` §4.4 手动安装 hypium har。

### 3.4 ohpm NOTFOUND hypium / missing hamock

```text
ERROR: NOTFOUND package '@ohos/hypium@1.0.25' not found from all the registries ...
ERROR: missing: @ohos/hamock@1.0.0, required by @
```

**根因**：7.26 包内 ohpm 的默认 registry 是华为内网（`cmc.centralrepo.rnd.huawei.com`、`mirrors.tools.huawei.com`），外网 `ENOTFOUND`；不是包不存在（公开 ohpm 有 hypium 1.0.25 和 hamock 1.0.0）。

**修复**：工程根 `.ohpmrc` 写 `registry=https://ohpm.openharmony.cn/ohpm/`，或 `ohpm config set registry https://ohpm.openharmony.cn/ohpm/`。HSP 夹具模块源码不 import hypium/hamock，无外网时也可删掉这两个 `devDependencies`（无 `oh_modules` 也能 `assembleHsp`）。

## 4. ArkTS-Sta（静态）

### 4.1 Double / Int

```text
ESE0046 Type 'Double' is not compatible with type 'Int' at index 1
ESE0127 No matching call signature for info(Double, String, ...)
```

**根因**：`const DOMAIN: number = 0x0000`、`msSleep(number)`、`startId: number` 等把 `number`（Double）传给了要求 `int` 的静态 API。
**修复**：

```ts
const DOMAIN: int = 0x0000;
const SLEEP_INTERVAL: int = 200;
onRequest(want: Want, startId: int): void
```

### 4.2 联合类型未收窄

```text
ESE0046 Type 'CommonEventSubscriber|undefined' is not compatible with type 'CommonEventSubscriber'
ESE0010 Value is possibly nullish.
```

**修复**：

```ts
const sub = subscriber;
if (sub === undefined) { return; }
commonEventManager.subscribe(sub, ...);

const abilityContext = AppStorage.get<common.UIAbilityContext>('UIAbilityContext');
if (abilityContext === undefined) { ... }
await abilityContext.startAbility(want);
```

### 4.3 AsyncCallback 签名

```text
ESE0127 No matching call signature for publish(...)
ESE0046 Type '((p1: BusinessError<undefined>) => undefined)' is not compatible with
'((p1: BusinessError<undefined>|null, p2: undefined) => undefined)'
```

**根因**：静态 `AsyncCallback<T, E=void> = (err: BusinessError<E> | null, data: T | undefined) => void;` 要求两个参数（第二个可为 `undefined`）。手写单参/非空 `err` 会不匹配。
**修复**：优先用类型推断：

```ts
commonEventManager.publish(EVENT, data, (err, _data) => {
  if (err) { ... }
});
```

`createSubscriber`/`subscribe` 同理；`createSubscriber` 也可用 Promise 版。

### 4.4 Double / Long（connectionId）

```text
ESE0046 Type 'Double' is not compatible with type 'Long' at index 1
```

**修复**：静态 connectionId 用 `long`：

```ts
private connectionId: long = -1;
private publishResult(caseName: string, code: int, connectionId: long): void
```

### 4.5 回调重载未匹配

```text
ESE0124 Expected 1 arguments, got 2.
ESE0127 No matching call signature for <method>(Long, ((...)))
```

**根因**：`connectionId` 是 `number`（Double），与 `long` 重载不匹配，编译器退回单参 Promise 重载。
**修复**：`connectionId` 改 `long`；回调用推断的 `(err, _data) => {}`。

### 4.6 catch 参数

```text
ESE0127 No matching call signature for catch((p1: BusinessError|null) => undefined)
ESE0046 ... not compatible with '(((p1: Error) => PromiseLike<undefined>|undefined))|undefined'
```

**修复**：

```ts
}).catch((err) => {
  const be = err as BusinessError;
  ...
});
```

### 4.7 非阻断告警

```text
W369037 Cast expression `as BusinessError` is type unsafe.
W71336 Exported function 'testsuite' requires type annotation.
```

**修复**：W369037 可保留（告警）；W71336 可写 `export default function testsuite(): void`。

## 5. 仓/命名/二进制

### 5.1 system API 用例放进 acts / 前缀错误

```text
工程在 test/xts/acts，hap_name 却是 Hits...；或 system API 用例提交到 acts
```

**根因**：选错仓/命名。system API 用例属于 **HITS 独立仓（闭源）**，使用 `Hits` 前缀；普通 API 才用 `xts_acts` + `Acts`。
**修复**：

- 移到 HITS 仓（仓名/构建/提交流程以 HITS 团队/CI 为准，不要猜）。
- `hap_name`、Test.json、目录名统一 `Hits` 前缀。
- 系统签名：`certificate_profile` 指向系统 profile；profile 设 `apl`/`app-feature`/`app-distribution-type`。

### 5.2 工程携带 HSP/预编译二进制

```text
工程内出现 *.hsp / *.hap / *.har / *.so / *.abc / *.jar
oh-package.json5: "file:../xxx.hsp"
```

**根因**：把预编译产物塞进工程，门禁要求所有模块从源码编译。
**修复**：

- 删除预编译二进制；HSP/HAR 依赖改为源码模块，由门禁一起编译。
- `oh-package.json5` 的 `file:` 依赖只保留 `tools/hypium_prepare/*.har`；其他 `.hsp`/`.har` 删除。
- 不要提交 `build/`、`oh_modules/`、`out/`。

## 6. 门禁“没编”的假通过

| 现象 | 根因 | 修复 |
|------|------|------|
| 日志里没有你的 target | BUILD.gn 未注册 / part 不在产品 | 父 group + `test_targets.gni` + `part_name` 核对 |
| 编译成功但没有 HAP | `test_hap`/模板/输出路径不匹配 | 动态 `test_hap=true`；静态主模块；核对 `entry/build/default/outputs/...` |
| 本地 HAP 有、门禁没有 | 门禁只编变更目标；`change_info.json` 未命中 | 确认 PR 变更路径在该 suite 下；或 `suite=<Target>` 显式构建 |
