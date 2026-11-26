#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""XTS 工程门禁前检查器（零依赖，Windows / WSL / Linux 均可运行）。

用法:
  python check_xts_project.py <suite_dir> [--syntax auto|dyn|sta] [--strict] [--json]

检查范围:
  BUILD.gn 模板 / test_hap / hap_name（acts=Acts / hits=Hits）/ part / 父 group 注册
  build-profile / hvigor-config / oh-package / Test.json / module.json5 / syscap
  动态/静态 RPC 类型、parameters 判空、globalThis、@tc.number 重复
  相对 import 大小写、srcEntry 大小写、预编译二进制、构建残留、License 头

退出码: 有 FAIL -> 1；否则 0。--strict 时 WARN 也返回 1。
"""

import argparse
import json
import os
import re
import sys

FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"


class Finding(object):
    def __init__(self, level, code, message, file="", line=0):
        self.level = level
        self.code = code
        self.message = message
        self.file = file
        self.line = line

    def __str__(self):
        loc = ""
        if self.file:
            loc = " (%s:%s)" % (self.file, self.line) if self.line else " (%s)" % self.file
        return "[%s] %s %s%s" % (self.level, self.code, self.message, loc)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def strip_json_comments(text):
    out = []
    i = 0
    n = len(text)
    quote = ""
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                in_str = False
            i += 1
            continue
        if c in "\"'":
            in_str = True
            quote = c
            out.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def load_json5(path):
    text = strip_json_comments(read_text(path))
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(text)
    except ValueError:
        return None


def get_quoted(text, key, default=None):
    m = re.search(r"[\"']?%s[\"']?\s*:\s*[\"']([^\"']+)[\"']" % re.escape(key), text)
    return m.group(1) if m else default


def get_assigned(text, key, default=None):
    """GN style: key = "value"."""
    m = re.search(r"%s\s*=\s*\"([^\"]+)\"" % re.escape(key), text)
    return m.group(1) if m else default


def get_raw_value(text, key):
    """Return (value, quoted) for 'key: value' where value is string/number/bool."""
    m = re.search(
        r"[\"']?%s[\"']?\s*:\s*(?:\"([^\"]*)\"|'([^']*)'|([0-9]+)|(true|false))" % re.escape(key),
        text,
    )
    if not m:
        return None, False
    for idx in (1, 2):
        if m.group(idx) is not None:
            return m.group(idx), True
    if m.group(3) is not None:
        return m.group(3), False
    return m.group(4), False


def api_major(value):
    if value is None:
        return None
    m = re.match(r"(\d+)", str(value))
    return int(m.group(1)) if m else None


def exact_exists(base, rel):
    """Case-sensitive existence check by walking directory entries."""
    cur = base
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            cur = os.path.dirname(cur)
            continue
        try:
            names = os.listdir(cur)
        except OSError:
            return False
        if part not in names:
            return False
        cur = os.path.join(cur, part)
    return os.path.exists(cur)


def find_exact(base, rel, suffixes=("", ".ets", ".ts", ".d.ets", ".d.ts")):
    for suffix in suffixes:
        cand = rel + suffix
        if exact_exists(base, cand):
            return cand
    return None


class Checker(object):
    def __init__(self, project, syntax="auto", strict=False):
        self.project = os.path.abspath(project)
        self.syntax = syntax
        self.strict = strict
        self.findings = []
        self.repo_kind = "unknown"
        self.target = ""
        self.hap_name = ""
        self.part_name = ""
        self.subsystem_name = ""
        self.bundle_name = ""
        self.module_name = ""
        self.module_json = ""
        self.test_json = ""
        self.syscap_paths = []
        self.test_root = ""
        self.build_gn = os.path.join(self.project, "BUILD.gn")
        self.build_profile = os.path.join(self.project, "build-profile.json5")
        self.oh_package = os.path.join(self.project, "oh-package.json5")
        self.hvigor_config = os.path.join(self.project, "hvigor", "hvigor-config.json5")

    def add(self, level, code, message, file="", line=0):
        if file and os.path.isabs(file):
            file = os.path.relpath(file, self.project)
        self.findings.append(Finding(level, code, message, file, line))

    def relpath(self, p):
        return os.path.relpath(p, self.project)

    # ---------- repo ----------
    def detect_repo_kind(self):
        p = self.project.replace("\\", "/").rstrip("/") + "/"
        if "/test/xts/hits/" in p or p.endswith("/xts/hits/"):
            self.repo_kind = "hits"
        elif "/test/xts/acts/" in p or p.endswith("/xts_acts/"):
            self.repo_kind = "acts"

    # ---------- syntax ----------
    def detect_syntax(self):
        if self.syntax in ("dyn", "sta"):
            return
        text = read_text(self.build_profile)
        if re.search(r"[\"']?arkTSVersion[\"']?\s*:\s*[\"']1\.2[\"']", text):
            self.syntax = "sta"
        else:
            self.syntax = "dyn"

    # ---------- BUILD.gn ----------
    def check_build_gn(self):
        if not os.path.isfile(self.build_gn):
            self.add(FAIL, "GN001", "BUILD.gn 不存在")
            return
        text = read_text(self.build_gn)
        uncommented = "\n".join(
            line for line in text.splitlines() if not line.strip().startswith("#")
        )
        m = re.search(r'ohos_(js_app_suite|js_app_static_suite)\s*\(\s*"([^"]+)"\s*\)', uncommented)
        if not m:
            self.add(FAIL, "GN002", "BUILD.gn 未找到 ohos_js_app_suite / ohos_js_app_static_suite")
        else:
            template, self.target = m.group(1), m.group(2)
            expected = "js_app_suite" if self.syntax == "dyn" else "js_app_static_suite"
            if template != expected:
                self.add(
                    FAIL,
                    "GN003",
                    "模板 %s 与语法 %s 不匹配，应为 %s" % (template, self.syntax, expected),
                    self.build_gn,
                )
        self.hap_name = get_assigned(uncommented, "hap_name", "") or ""
        self.part_name = get_assigned(uncommented, "part_name", "") or ""
        self.subsystem_name = get_assigned(uncommented, "subsystem_name", "") or ""
        if not self.hap_name:
            self.add(FAIL, "GN004", "BUILD.gn 缺少 hap_name")
        else:
            if self.repo_kind == "hits" and not self.hap_name.startswith("Hits"):
                self.add(FAIL, "GN005", "HITS 工程 hap_name 必须以 Hits 开头: %s" % self.hap_name, self.build_gn)
            elif self.repo_kind == "acts" and not self.hap_name.startswith("Acts"):
                self.add(FAIL, "GN005", "acts 工程 hap_name 必须以 Acts 开头（门禁 R014）: %s" % self.hap_name, self.build_gn)
            elif self.repo_kind == "unknown" and not (
                self.hap_name.startswith("Acts") or self.hap_name.startswith("Hits")
            ):
                self.add(FAIL, "GN005", "hap_name 必须按仓使用 Acts/Hits 前缀: %s" % self.hap_name, self.build_gn)
        if not self.part_name:
            self.add(FAIL, "GN006", "BUILD.gn 缺少 part_name")
        if not self.subsystem_name:
            self.add(FAIL, "GN007", "BUILD.gn 缺少 subsystem_name")
        has_test_hap = bool(re.search(r"^\s*test_hap\s*=\s*true", uncommented, re.M))
        if self.syntax == "dyn" and not has_test_hap:
            self.add(FAIL, "GN008", "动态套件必须 test_hap = true", self.build_gn)
        if self.syntax == "sta" and has_test_hap:
            self.add(FAIL, "GN009", "静态套件不能使用 test_hap = true（静态没有 ohosTest）", self.build_gn)
        cert = get_assigned(uncommented, "certificate_profile", "")
        if cert:
            if not exact_exists(self.project, cert.lstrip("./")):
                self.add(FAIL, "GN010", "certificate_profile 文件不存在: %s" % cert, self.build_gn)
        else:
            self.add(WARN, "GN011", "BUILD.gn 未设置 certificate_profile（系统 API 需要系统签名）", self.build_gn)
        self.check_parent_registration()

    def check_parent_registration(self):
        parent = os.path.dirname(self.project)
        parent_gn = os.path.join(parent, "BUILD.gn")
        if not os.path.isfile(parent_gn):
            self.add(WARN, "REG001", "父目录没有 BUILD.gn，无法确认 group 注册: %s" % parent)
            return
        if not self.target:
            return
        text = read_text(parent_gn)
        if self.target not in text:
            self.add(
                FAIL,
                "REG002",
                "父 BUILD.gn 未注册 target '%s'（门禁不会编译该 suite）" % self.target,
                parent_gn,
            )

    # ---------- configs ----------
    def check_build_profile(self):
        text = read_text(self.build_profile)
        if not text:
            self.add(FAIL, "CFG001", "build-profile.json5 不存在")
            return
        compile_v, compile_q = get_raw_value(text, "compileSdkVersion")
        compat_v, compat_q = get_raw_value(text, "compatibleSdkVersion")
        major = api_major(compile_v)
        if major is not None and major >= 26:
            if not compile_q:
                self.add(FAIL, "CFG002", "API >= 26 时 compileSdkVersion 必须是字符串（如 \"26.1.0\"）")
        elif major is not None and major < 26:
            if compile_q:
                self.add(WARN, "CFG004", "API < 26 时 compileSdkVersion 建议用数字")
        # compatibleSdkVersion 按自己的 API 等级判断；门禁静态模板允许 "22" 字符串
        compat_major = api_major(compat_v)
        if compat_major is not None and compat_major >= 26 and not compat_q:
            self.add(FAIL, "CFG003", "compatibleSdkVersion >= 26 时必须是字符串（如 \"26.0.0\"）")
        runtime = get_quoted(text, "runtimeOS", "")
        if runtime and runtime != "OpenHarmony":
            self.add(WARN, "CFG006", "runtimeOS 不是 OpenHarmony: %s" % runtime)
        if self.syntax == "sta":
            ark = get_quoted(text, "arkTSVersion", "")
            if ark != "1.2":
                self.add(FAIL, "CFG007", "静态工程 build-profile.json5 必须 arkTSVersion: \"1.2\"")
        strict = re.search(r"caseSensitiveCheck\s*:\s*(true|false)", text)
        if not strict:
            self.add(WARN, "CFG008", "建议开启 strictMode.caseSensitiveCheck")

    def check_model_version(self):
        for path in (self.hvigor_config, self.oh_package):
            text = read_text(path)
            mv = get_quoted(text, "modelVersion", "")
            if not mv:
                self.add(WARN, "CFG010", "%s 缺少 modelVersion" % self.relpath(path), path)
            elif self.syntax == "dyn" and mv != "26.0.0":
                self.add(
                    WARN,
                    "CFG011",
                    "%s modelVersion=%s；门禁 26.x 套件应为 26.0.0" % (self.relpath(path), mv),
                    path,
                )

    def check_oh_package(self):
        text = read_text(self.oh_package)
        if not text:
            self.add(FAIL, "PKG001", "oh-package.json5 不存在")
            return
        hypium = "@ohos/hypium-dynamic" if self.syntax == "dyn" else "@ohos/hypium-static"
        if hypium not in text:
            static_hypium_src = os.path.isdir(os.path.join(self.project, "entry", "src", "hypium"))
            if self.syntax == "sta" and static_hypium_src:
                pass  # 静态模板常把 hypium 源码放在 entry/src/hypium
            elif self.syntax == "dyn" and re.search(r'"@ohos/hypium"\s*:', text):
                self.add(WARN, "PKG002",
                         "使用 registry @ohos/hypium；门禁模板用 hypium-dynamic har（确认 HITS 仓 hypium_prepare 相对路径后再切换）")
            else:
                self.add(FAIL, "PKG002", "oh-package.json5 缺少 %s 依赖" % hypium)
        if "hypium_prepare" not in text or ".har" not in text:
            self.add(
                WARN,
                "PKG003",
                "%s 依赖未指向 tools/hypium_prepare/*.har；门禁使用固定 har" % hypium,
            )
        if re.search(r'"@ohos/hypium[^"]*"\s*:\s*"\^?[0-9]', text):
            self.add(WARN, "PKG004", "hypium 依赖写了 registry 版本；门禁使用本地 har")
        for m in re.finditer(r"file:([^\"']+)", text):
            dep = m.group(1)
            if re.search(r"\.(hsp|har)$", dep) and "hypium_prepare" not in dep:
                self.add(
                    FAIL,
                    "BIN002",
                    "工程引用了预编译 %s；门禁要求源码模块编译，不能携带 HSP/HAR" % dep,
                    self.oh_package,
                )

    # ---------- Test.json / module.json5 ----------
    def locate_files(self):
        entry = os.path.join(self.project, "entry")
        if self.syntax == "dyn":
            self.module_json = os.path.join(entry, "src", "ohosTest", "module.json5")
            self.test_json = os.path.join(self.project, "Test.json")
            self.syscap_paths = [
                os.path.join(entry, "src", "ohosTest", "syscap.json"),
                os.path.join(entry, "src", "main", "syscap.json"),
            ]
            self.test_root = os.path.join(entry, "src", "ohosTest", "ets", "test")
        else:
            self.module_json = os.path.join(entry, "src", "main", "module.json5")
            self.test_json = os.path.join(self.project, "Test.json")
            self.syscap_paths = [os.path.join(entry, "src", "main", "syscap.json")]
            self.test_root = os.path.join(entry, "src", "main", "src", "test")
        app_json = os.path.join(self.project, "AppScope", "app.json5")
        app_text = read_text(app_json)
        self.bundle_name = get_quoted(app_text, "bundleName", "")
        module_text = read_text(self.module_json)
        m = re.search(r'"module"\s*:\s*\{', module_text)
        if m:
            self.module_name = get_quoted(module_text[m.start():], "name", "")
        if not self.module_name:
            m = re.search(r'"name"\s*:\s*"([^"]+)"', module_text)
            self.module_name = m.group(1) if m else ""

    def check_test_json(self):
        if not os.path.isfile(self.test_json):
            self.add(FAIL, "TST001", "Test.json 不存在")
            return
        try:
            with open(self.test_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as e:
            self.add(FAIL, "TST002", "Test.json 不是合法 JSON: %s" % e, self.test_json)
            return
        driver = data.get("driver", {})
        b = driver.get("bundle-name", "")
        if self.bundle_name and b != self.bundle_name:
            self.add(FAIL, "TST003", "Test.json bundle-name=%s，app.json5=%s" % (b, self.bundle_name), self.test_json)
        m = driver.get("module-name", "")
        if self.module_name and m != self.module_name:
            self.add(FAIL, "TST004", "Test.json module-name=%s，module.json5=%s" % (m, self.module_name), self.test_json)
        haps = []
        for kit in data.get("kits", []):
            haps.extend(kit.get("test-file-name", []) or [])
        expected = (self.hap_name + ".hap") if self.hap_name else ""
        if expected and expected not in haps:
            self.add(FAIL, "TST005", "Test.json 未引用 %s（当前: %s）" % (expected, haps), self.test_json)

    def check_module_json(self):
        if not os.path.isfile(self.module_json):
            self.add(FAIL, "MOD001", "module.json5 不存在: %s" % self.relpath(self.module_json))
            return
        text = read_text(self.module_json)
        ext = re.search(r'"extensionAbilities"\s*:\s*\[', text)
        if ext:
            end = text.find("]", ext.end())
            block = text[ext.end(): end if end > 0 else len(text)]
            if re.search(r'"process"\s*:', block):
                line = text[: ext.start()].count("\n") + 1
                self.add(
                    FAIL,
                    "MOD002",
                    "extensionAbilities 不允许 process；改用 extensionProcessMode（bundle|type|instance）",
                    self.module_json,
                    line,
                )
            for mode in re.findall(r'"extensionProcessMode"\s*:\s*"([^"]+)"', block):
                if mode not in ("bundle", "type", "instance"):
                    self.add(WARN, "MOD003", "未知 extensionProcessMode: %s" % mode, self.module_json)
        for entry in re.findall(r'"srcEntry"\s*:\s*"([^"]+)"', text):
            if entry.startswith("$"):
                continue
            if not exact_exists(os.path.dirname(self.module_json), entry.lstrip("./")):
                self.add(FAIL, "MOD004", "srcEntry 文件不存在（注意大小写）: %s" % entry, self.module_json)

    def check_syscap(self):
        checked = 0
        for path in self.syscap_paths:
            if not os.path.isfile(path):
                continue
            checked += 1
            data = load_json5(path)
            if data is None:
                self.add(WARN, "SYS001", "syscap.json 解析失败: %s" % self.relpath(path), path)
                continue
            caps = []
            try:
                for dev in data.get("devices", {}).get("custom", []):
                    caps.extend(dev.get("xts", []) or [])
            except AttributeError:
                pass
            if not caps:
                self.add(FAIL, "SYS002", "syscap.json 的 custom[].xts 为空: %s" % self.relpath(path), path)
        if checked == 0:
            self.add(WARN, "SYS003", "未找到 syscap.json（动态检查 ohosTest/main，静态检查 main）")

    # ---------- code ----------
    def iter_sources(self):
        root = os.path.join(self.project, "entry", "src")
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ("oh_modules", "build", ".hvigor")]
            for f in fn:
                if f.endswith((".ets", ".ts")):
                    yield os.path.join(dp, f)

    def check_code(self):
        tc_numbers = {}
        for path in self.iter_sources():
            text = read_text(path)
            lines = text.splitlines()
            rel = self.relpath(path)
            for i, line in enumerate(lines, 1):
                if "globalThis" in line:
                    self.add(FAIL, "COD001", "ArkTS 禁止 globalThis", rel, i)
                if re.search(r"rpc\.MessageSequence", line) and self.syntax == "dyn" and "onRemoteRequest" in text:
                    self.add(FAIL, "COD002", "动态 onRemoteRequest 必须用 rpc.MessageParcel", rel, i)
                if re.search(r"rpc\.MessageParcel", line) and self.syntax == "sta" and "onRemoteRequest" in text:
                    self.add(FAIL, "COD003", "静态 onRemoteRequest 必须用 rpc.MessageSequence", rel, i)
                if ".parameters[" in line and "parameters" not in line.split(".parameters[")[0]:
                    # AbilityDelegatorRegistry.getArguments().parameters 在 SDK 中非可选，跳过
                    if "getArguments().parameters" in line or "abilityDelegatorArguments.parameters" in line:
                        continue
                    window = "\n".join(lines[max(0, i - 16): i])
                    if "parameters === undefined" not in window and "params === undefined" not in window:
                        self.add(WARN, "COD004", "parameters 可能为 undefined；先判空再取", rel, i)
                if "console.log" in line:
                    self.add(WARN, "COD006", "测试代码不建议使用 console.log（用 hilog）", rel, i)
                if re.search(r"[\"'](C:|D:|/data/)[^\"']*[\"']", line):
                    self.add(WARN, "COD007", "疑似硬编码设备/宿主路径", rel, i)
                for m in re.finditer(r"@tc\.number\s+(\S+)", line):
                    tc_numbers.setdefault(m.group(1), []).append("%s:%s" % (rel, i))
                for m in re.finditer(r"\bit\(\s*[\"']([^\"']+)[\"']", line):
                    if not m.group(1).startswith("SUB_"):
                        self.add(WARN, "COD008", "it() 名称建议以 SUB_ 开头: %s" % m.group(1), rel, i)
            if "Apache License" not in "\n".join(lines[:30]):
                self.add(WARN, "COD009", "文件缺少 Apache 2.0 License 头", rel)
            self.check_imports(path, text)
        for num, locs in tc_numbers.items():
            if len(locs) > 1:
                self.add(FAIL, "COD010", "@tc.number 重复: %s -> %s" % (num, ", ".join(locs)))

    def check_imports(self, path, text):
        base = os.path.dirname(path)
        rel = self.relpath(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"(?:from\s+|import\s*)['\"](\.[^'\"]+)['\"]", line):
                imp = m.group(1)
                if find_exact(base, imp) is None:
                    self.add(
                        FAIL,
                        "IMP001",
                        "相对 import 不存在或大小写不匹配: %s（门禁 Linux 大小写敏感）" % imp,
                        rel,
                        line_no,
                    )

    # ---------- binaries ----------
    def check_binaries(self):
        binary_exts = {
            ".hsp", ".hap", ".har", ".so", ".a", ".abc",
            ".jar", ".bin", ".exe", ".dll", ".dylib",
        }
        skip_dirs = {"oh_modules", "build", ".hvigor", ".git", "out", ".idea"}
        for dp, dn, fn in os.walk(self.project):
            dn[:] = [d for d in dn if d not in skip_dirs]
            for f in fn:
                ext = os.path.splitext(f)[1].lower()
                if ext in binary_exts:
                    self.add(
                        FAIL,
                        "BIN001",
                        "工程携带预编译二进制/包 %s；所有模块必须在门禁中从源码编译" % f,
                        os.path.join(dp, f),
                    )

    # ---------- hygiene ----------
    def check_hygiene(self):
        for name in ("oh_modules", "build", ".hvigor", "oh-package-lock.json5", "local.properties", "out"):
            p = os.path.join(self.project, name)
            if os.path.exists(p):
                self.add(WARN, "HYG001", "存在构建残留 %s；提交前删除并加入 .gitignore" % name)
        gitignore = read_text(os.path.join(self.project, ".gitignore"))
        for name in ("oh_modules", "build", ".hvigor", "local.properties"):
            if name not in gitignore:
                self.add(WARN, "HYG002", ".gitignore 未包含 %s" % name)

    # ---------- run ----------
    def run(self):
        if not os.path.isdir(self.project):
            print("ERROR: project dir not found: %s" % self.project)
            return 2
        self.detect_repo_kind()
        self.detect_syntax()
        self.locate_files()
        self.check_build_gn()
        self.check_build_profile()
        self.check_model_version()
        self.check_oh_package()
        self.check_test_json()
        self.check_module_json()
        self.check_syscap()
        self.check_code()
        self.check_binaries()
        self.check_hygiene()
        return 0

    def report(self, as_json=False):
        level_order = {FAIL: 0, WARN: 1, INFO: 2}
        self.findings.sort(key=lambda f: (level_order.get(f.level, 9), f.code, f.file, f.line))
        counts = {FAIL: 0, WARN: 0, INFO: 0}
        for f in self.findings:
            counts[f.level] = counts.get(f.level, 0) + 1
        if as_json:
            print(json.dumps({
                "project": self.project,
                "syntax": self.syntax,
                "repo_kind": self.repo_kind,
                "target": self.target,
                "hap_name": self.hap_name,
                "counts": counts,
                "findings": [f.__dict__ for f in self.findings],
            }, ensure_ascii=False, indent=2))
        else:
            print("XTS project: %s" % self.project)
            print("syntax: %s  repo: %s  target: %s  hap_name: %s" % (self.syntax, self.repo_kind, self.target, self.hap_name))
            for f in self.findings:
                print(f)
            print("\nSummary: FAIL=%d WARN=%d INFO=%d" % (counts[FAIL], counts[WARN], counts[INFO]))
        if counts[FAIL]:
            return 1
        if self.strict and counts[WARN]:
            return 1
        return 0


def main():
    parser = argparse.ArgumentParser(description="XTS 工程门禁前检查器")
    parser.add_argument("project", help="suite 根目录（含 BUILD.gn）")
    parser.add_argument("--syntax", choices=["auto", "dyn", "sta"], default="auto")
    parser.add_argument("--strict", action="store_true", help="WARN 也返回非 0")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    checker = Checker(args.project, args.syntax, args.strict)
    rc = checker.run()
    if rc:
        return rc
    return checker.report(args.json)


if __name__ == "__main__":
    sys.exit(main())
