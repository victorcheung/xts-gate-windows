# XTS 工程完善规则

## 0. 选仓：acts 还是 HITS

| API 类型 | 仓 | 命名前缀 | 说明 |
|----------|----|---------|------|
| 普通 Public API | `xts_acts`（`test/xts/acts`） | `Acts` | 常规 XTS |
| `@systemapi` / 系统权限 | **HITS 独立仓（闭源）** | `Hits` | 仓名/构建/提交流程以 HITS 团队为准，不要猜 |

- system API 用例 **不要**提交到 `xts_acts`，也不要沿用 `Acts` 前缀。
- 普通 API 不要提交到 HITS。
- 同一需求同时覆盖 public/system 时按 spec 拆分。
- HITS 仓闭源，公开 manifest 看不到；只使用 `test/xts/hits` 这一公开路径线索，不要推测其内部构建命令/产物路径。

详见 `system-api-hits.md`。

## 1. 目录与注册

标准位置（全量源码树）：

```
test/xts/acts/<subsystem>/<part>/<suite>/
  BUILD.gn
  Test.json
  AppScope/app.json5
  build-profile.json5
  oh-package.json5
  hvigor/hvigor-config.json5
  entry/
    src/main/                 # 静态测试代码 + 模块配置
    src/ohosTest/             # 动态测试代码 + 模块配置
    src/main/src/test/        # 静态测试用例
```

### 父 group 注册

`<part>/BUILD.gn`：

```gn
group("<part>") {
  testonly = true
  if (is_standard_system) {
    deps = [
      "<Suite>:<Target>",
      ...
    ]
  }
}
```

### 顶层 group 注册

如果 suite 所在 subsystem 还没有进入 `test_targets.gni` 的 `all_test_targets`，追加：

```gn
"${ACTS_ROOT}/<subsystem>:<subsystem>"
```

> 门禁按 `change_info.json` 计算目标；未注册的 suite 不会被编，容易被误判为“通过”。

## 2. BUILD.gn

### 动态

```gn
import("//test/xts/tools/build/suite.gni")

ohos_js_app_suite("<Target>") {
  test_hap = true
  testonly = true
  certificate_profile = "./signature/openharmony_sx.p7b"
  hap_name = "Acts<SuiteName>"   # HITS 工程用 "Hits<SuiteName>"
  part_name = "<part_name>"
  subsystem_name = "<subsystem_name>"
}
```

### 静态

```gn
import("//test/xts/tools/build/suite.gni")

ohos_js_app_static_suite("<Target>") {
  # test_hap = true        # 静态没有 ohosTest，必须注释/删除
  testonly = true
  certificate_profile = "./signature/openharmony_sx.p7b"
  hap_name = "Acts<SuiteName>"   # HITS 工程用 "Hits<SuiteName>"
  part_name = "<part_name>"
  subsystem_name = "<subsystem_name>"
}
```

硬规则：

- 动态必须 `ohos_js_app_suite`；静态必须 `ohos_js_app_static_suite`。模板与 ETS 版本不匹配是静态编译失败的首要原因。
- `hap_name` 按仓用 `Acts`/`Hits` 前缀；`Test.json` 的 hap 文件名必须与它一致。
- `part_name`/`subsystem_name` 必须与对应 `bundle.json` 的 part/subsystem 一致，否则门禁的 `parts_config` 会把目标过滤掉。
- `certificate_profile` 指向工程内真实存在的 p7b。
- 目录名 ≠ target 名；门禁识别的是 `ohos_js_app_suite("...")` 里的 target。`suite=` 参数可传 target，也可传 group。

## 3. 配置字段

### build-profile.json5

```json5
{
  "app": {
    "products": [{
      "name": "default",
      "compileSdkVersion": "26.1.0",     // API >= 26 必须字符串
      "compatibleSdkVersion": "26.0.0",  // 同上；静态建议与 API 版本匹配
      "runtimeOS": "OpenHarmony",
      "buildOption": {
        "strictMode": {
          "caseSensitiveCheck": true,
          "useNormalizedOHMUrl": true
        }
      }
    }]
  },
  "modules": [
    { "name": "entry", "srcPath": "./entry",
      "targets": [{ "name": "default", "applyToProducts": ["default"] }] }
  ]
}
```

- API < 26：`compileSdkVersion`/`compatibleSdkVersion` 用数字（如 `12`）。
- 静态：`"arkTSVersion": "1.2"`。
- 静态门禁模板（当前）：`compileSdkVersion "26.1.0"`、`compatibleSdkVersion "22"`、`arkTSVersion "1.2"`，同时 `hvigor-config.json5` 与 `oh-package.json5` 的 `modelVersion` 用 `"26.0.0"`。三处必须一致，否则 7.26.0 工具报 `00306042`。老的 5.14.2 近似环境（`26`/`22` 数字、`modelVersion "6.1.1"`）只用于 scratch，不要写进交付工程。

### hvigor/hvigor-config.json5 与 oh-package.json5

```json5
{
  "modelVersion": "26.0.0",   // 门禁 26.x
  "dependencies": {},
  "properties": { "ohos.byteCodeHar.integratedOptimization": true }
}
```

- 门禁动态/静态都用 `26.0.0`；仅老 5.14.2 近似环境用 `6.1.1`。
- 不要在里面写与本机相关的绝对路径。

### oh-package.json5

```json5
{
  "modelVersion": "26.0.0",
  "devDependencies": {
    "@ohos/hypium-dynamic": "file:../../../../../tools/hypium_prepare/hypium-dynamic.har"
  }
}
```

静态换成 `@ohos/hypium-static` 和 `hypium-static.har`。不要改成 registry 版本，门禁用固定 har。

### Test.json

```json
{
  "driver": {
    "type": "OHJSUnitTest",
    "test-timeout": "600000",
    "bundle-name": "com.example.xxx",
    "module-name": "entry_test",
    "shell-timeout": "600000",
    "testcase-timeout": "30000"
  },
  "kits": [
    { "test-file-name": ["ActsXxxTest.hap"], "type": "AppInstallKit", "cleanup-apps": true }
  ]
}
```

- 动态 `module-name` = `entry_test`；静态 = `entry`，分别与对应 module.json5 的 `module.name` 一致。
- `bundle-name` 与 `AppScope/app.json5` 的 `bundleName` 一致。
- `test-file-name` 与 BUILD.gn 的 `hap_name.hap` 一致。

### module.json5（动态 `entry/src/ohosTest`，静态 `entry/src/main`）

- `extensionAbilities[]` **不允许** `process`；`process` 只能在 `abilities[]`。
- 需要独立进程：`"extensionProcessMode": "bundle" | "type" | "instance"`。测试要观察扩展进程被 kill 后连接清理，通常用 `"instance"`。
- 带 `@systemapi` 的 ExtendedAbility/Context 等系统 API 需要系统签名 profile；`syscap` 与 API 的 `@syscap` 一致。
- `srcEntry` 路径大小写必须与真实文件一致（Windows 不敏感，门禁敏感）。

### syscap.json

动态：`entry/src/ohosTest/syscap.json`；静态：`entry/src/main/syscap.json`。

```json
{
  "devices": { "general": [], "custom": [{ "xts": [
    "SystemCapability.Ability.AbilityRuntime.Core"
  ]}]}
}
```

`custom[].xts` 至少包含被测 API 的 `@syscap`。调用 `bundleManager` 的用例还要加 `SystemCapability.BundleManager.BundleFramework.Core` 等实际用到的能力。

## 4. 动态 vs 静态

| 项 | 动态（ArkTS-Dyn） | 静态（ArkTS-Sta） |
|----|------------------|-------------------|
| BUILD.gn | `ohos_js_app_suite` | `ohos_js_app_static_suite` |
| `test_hap` | `= true` | 注释/删除 |
| 测试目录 | `entry/src/ohosTest/ets/test` | `entry/src/main/src/test` |
| build-profile | 无 `arkTSVersion` | `"arkTSVersion": "1.2"` |
| hvigor 命令（WSL/Linux） | `--mode module -p module=entry@ohosTest assembleHap` | `--mode project -p product=default assembleApp` |
| RPC 类型 | `rpc.MessageParcel` | `rpc.MessageSequence` |
| 数值类型 | `number` | `int` / `long`，`number` 只用于浮点 |
| 回调 | 可写单参 | `AsyncCallback<T> = (err: BusinessError\|null, data: T\|undefined) => void`，建议用类型推断 |
| hypium | `hypium-dynamic.har` | `hypium-static.har` |
| 产物 | `entry-ohosTest-unsigned.hap` | `entry-default-unsigned.hap` |

## 5. 代码规则（门禁会抓）

1. **`@tc` 注解**：每个 `it` 前有 `@tc.name`/`@tc.number`/`@tc.desc`/`@tc.type`；`@tc.number` 全局唯一。
2. **命名**：`it('SUB_<Subsystem>_<Module>_<Api>_<Type>_<Seq>', ...)`；`describe` 与套件名一致。
3. **空值**：`CommonEventData.parameters` 在新 SDK 中可选，先判空再取；不要 `data.parameters['x']` 裸访问。
4. **禁止 `globalThis`**：用 `AppStorage`、参数传递或成员变量。
5. **静态语言**：
   - 用 `int` 表示错误码/hilog domain/计数；`long` 表示 connectionId；
   - 显式回调签名容易与 `AsyncCallback` 不匹配，优先用推断（`(err, data) => {}`），并处理 `data === undefined`；
   - 联合类型先赋本地常量再判空，静态不对成员属性做跨语句收窄；
   - `.catch` 的参数是 `Error`，取 `code` 前转 `BusinessError`。
6. **动态语言**：
   - `onRemoteRequest` 用 `MessageParcel`；
   - 连接 ID 用 `number`；
   - callback 重载必须真实存在于 SDK；不存在时不要为了本地编过删用例，先补接口。
7. **异步/清理**：`await` 放 `try`；`afterAll` 用 `try/finally` 清理 subscriber、connection、启动的 ability；失败也要清理。
8. **错误码断言**：用 `Number(error.code)` 或 `error.code as number`；不要只断言 `error !== undefined`。
9. **不硬编码**：设备路径、bundle 名、pid、时间不要写死；bundle 名从 `AppScope` 或常量取。
10. **License header**：新增 `.ets`/`.ts`/`.gn` 文件保留 Apache 2.0 头。

## 6. 系统 API 与签名

- 被测 API 标 `@systemapi` 时，用例属于 **HITS 仓**，使用 `Hits` 前缀；测试 HAP 必须系统签名，`BUILD.gn` 的 `certificate_profile` 指向 `signature/openharmony_sx.p7b`。
- 需要 `system_basic`/`system_core` 权限时，profile 的 `bundle-info.apl`、`app-feature`、`app-distribution-type` 要在签名前设置（参考 `openharmony-arkts12-system-signing`）。
- 系统签名不是换一张证书，而是改 profile JSON 后重新 `sign-profile` + `sign-app`：
  - `bundle-info.apl` = `system_basic` 或 `system_core`
  - `bundle-info.app-feature` = `hos_system_app`
  - `app-distribution-type` = `os_integration`
  - `distribution-certificate` 末尾保留换行，且与 `-appCertFile` 的叶子证书字节一致
- 测试代码里调用系统 API 会出 `WARN: '...' is system api`，这是预期；不要当错误删掉。

## 7. 接口与 spec

- 新接口的 XTS 用例必须与 `interface/sdk-js` 的声明一致。spec 要求 callback + Promise 双重重载时，接口必须同时提供，例如：
  ```ts
  // 示例：替换为实际接口名
  foo(connection: long, callback: AsyncCallback<void>): void;
  foo(connection: long): Promise<void>;
  ```
- 本地可以 patch SDK 验证，但**不能把“删掉某个重载的用例”当作修复**；真实门禁 SDK 由 master 构建，接口未合入就会失败。
- 提交前确认：接口 PR 已合入，门禁 SDK 已刷新到包含该声明。

## 8. 禁止预编译二进制

门禁要求所有工程从源码编译，不允许把现成二进制塞进工程：

- 禁止提交 `.hsp`、`.hap`、`.har`、`.so`、`.a`、`.abc`、`.jar`、`.bin`、`.exe`、`.dll`、`.dylib`。
- HSP 依赖必须改成源码模块，由门禁一起编译；不能提交 `file:../xxx.hsp` 这类预编译依赖。
- `oh-package.json5` 的 `file:` 依赖只应指向门禁提供的 hypium har（`tools/hypium_prepare/*.har`）；其他 `.har`/`.hsp` 会被检查器判 FAIL。
- 图片、字体等资源不算代码二进制；但不要把整个 `build/`、`oh_modules/`、`out/` 提交上去。
