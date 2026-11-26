# System API：HITS 仓、Hits 命名与系统签名

> 适用于被测 API 是 `@systemapi`、需要系统权限/系统应用能力、或 spec 明确要求 system 的 XTS 用例。

## 1. 已知事实（不推测闭源仓）

- HITS 仓是**独立仓且闭源**，公开 manifest 看不到；不要猜它的仓名、构建脚本、产物路径或 CI 命令。
- 公开的 `test/xts/tools/build/suite.gni` 里有 `HITS_ROOT = "//test/xts/hits"`，以及 `XTS_SUITENAME == "hits"` 的分支；这只能说明路径/suite 名，不能推断 HITS 仓的内部结构。
- 命名约定：HITS 用例使用 **`Hits` 前缀**（不是 `Acts`）。
- 提交目标：HITS 仓，而不是 `xts_acts`。
- HITS 仓的实际构建/提交流程以 HITS 团队/CI 提供的信息为准；本 skill 不提供猜测的命令。

## 2. 选仓规则

| API 类型 | 提交仓 | 路径（公开侧可见部分） | 命名前缀 | suite 名 |
|----------|--------|------------------------|---------|----------|
| 普通 Public API | `xts_acts` | `test/xts/acts/<subsystem>/<part>/<suite>` | `Acts` | `acts` |
| System API（`@systemapi`） | HITS 仓（闭源，实际仓名/流程以 HITS 团队为准） | `test/xts/hits/<subsystem>/<part>/<suite>` | `Hits` | `hits` |

硬规则：

- system API 用例**不要提交到 `xts_acts`**，也不要沿用 `Acts` 前缀。
- 普通 API 不要提交到 HITS 仓。
- 命名与仓必须一致：HITS 用 `Hits<SuiteName>`，acts 用 `Acts<SuiteName>`。
- 同一需求同时覆盖 public/system 时按 spec 拆分，分别提交。

## 3. 工程侧准备（与 acts 相同的部分）

HITS 工程同样需要：

- `BUILD.gn`：动态 `ohos_js_app_suite` + `test_hap = true`；静态 `ohos_js_app_static_suite` + `# test_hap = true`。
- `hap_name = "Hits<SuiteName>"`（不是 `Acts`）。
- `part_name`/`subsystem_name` 与部件 `bundle.json` 一致。
- `Test.json` 的 `test-file-name` 与 `hap_name.hap` 一致；`bundle-name`/`module-name` 与配置一致。
- `syscap.json` 包含被测 system API 的 `@syscap`。
- 动态/静态目录、hypium har、@tc 注解、清理逻辑等规则与 acts 相同。

HITS 仓内部如何注册 group、如何调用构建脚本，**以 HITS 团队提供的仓/CI 为准**；不要照搬本 skill 里 acts 的命令并将其称为 HITS 命令。

## 4. 系统签名

System API 用例的 HAP 必须系统签名：

1. `BUILD.gn` 的 `certificate_profile` 指向工程内真实存在的系统 profile（如 `./signature/openharmony_sx.p7b`）。
2. profile JSON 在签名前设置：
   - `bundle-info.apl` = `system_basic` 或 `system_core`
   - `bundle-info.app-feature` = `hos_system_app`
   - `app-distribution-type` = `os_integration`
3. `sign-profile` → `sign-app`（必要时 `verify-app`/`verify-profile`）。
4. `distribution-certificate` 末尾保留换行，且与 `-appCertFile` 的叶子证书字节一致。

系统签名不是换一张证书；是 profile 内容 + 证书链的组合。测试代码里出现 `WARN: '...' is system api` 是预期，不要删除系统 API 调用。

## 5. 上库前

- [ ] API 确认为 `@systemapi` / system 权限；spec 要求 HITS。
- [ ] 工程准备放在 `test/xts/hits/...`，目标仓是 HITS 仓（闭源，按 HITS 团队流程提交）。
- [ ] `hap_name` / Test.json / 目录名统一使用 `Hits` 前缀。
- [ ] `certificate_profile` 与系统 profile 正确。
- [ ] 没有把 HITS 用例提交到 `xts_acts`，也没有混用 `Acts`/`Hits`。
- [ ] 接口/权限依赖已确认；不要用“本地签名能跑”代替门禁编译。
- [ ] HITS 构建/提交命令、产物路径向 HITS 团队确认，**不要猜测**。

## 6. 检查器行为

`scripts/check_xts_project.py` 只根据公开路径做一致性检查：

- 路径含 `test/xts/hits` → 期望 `Hits` 前缀；
- 路径含 `test/xts/acts` 或 `xts_acts` → 期望 `Acts` 前缀；
- 不一致或前缀不对 → FAIL。

若工程在独立目录、路径无法推断，检查器接受 `Acts`/`Hits` 任一，但仍校验 Test.json/配置一致性。它不会推断 HITS 仓的内部构建流程。
