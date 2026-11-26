#!/usr/bin/env bash
# 下载并解压门禁静态工具链（7.26.0 ArkTS 1.2），按门禁布局放到
#   <dest>/7.26.0.static/hvigor/bin/hvigorw
#
# 用法（在 WSL/Linux 内执行）:
#   ./fetch-static-toolchain.sh [--dest <dir>] [--dir <mirror-dir>] [--list]
#
# 默认从华为云镜像的 hvigor 目录列表里自动选最新的 7.26* 版本；
# 若镜像上出现 `7.26.0.static`，优先用它（门禁路径名）。
# --dir  指定镜像目录名（如 7.26.0-arkts1.2-0601-02）
# --list 只列出候选并退出，不下载
set -euo pipefail

LIST_URL="https://repo.huaweicloud.com/harmonyos/compiler/hvigor/"
DEST="/root/ohos-gate/toolchain/hvigor-static"
FORCE_DIR=""
LIST_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) DEST="$2"; shift 2 ;;
    --dir) FORCE_DIR="$2"; shift 2 ;;
    --list) LIST_ONLY=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 1 ;;
  esac
done

resolve_dir() {
  if [[ -n "$FORCE_DIR" ]]; then
    printf '%s\n' "$FORCE_DIR"
    return
  fi
  local html dirs
  html="$(curl -fsSL "$LIST_URL")"
  dirs="$(printf '%s' "$html" \
    | grep -oE 'href="7\.26[^"]*/"' \
    | sed -e 's/^href="//' -e 's#/"$##' \
    | sort -V || true)"
  if [[ -z "$dirs" ]]; then
    echo "ERROR: no 7.26* entry found at $LIST_URL" >&2
    return 1
  fi
  if printf '%s\n' "$dirs" | grep -qx '7.26.0.static'; then
    printf '%s\n' '7.26.0.static'
  else
    printf '%s\n' "$dirs" | tail -1
  fi
}

VER_DIR="$(resolve_dir)"
BASE_URL="https://repo.huaweicloud.com/harmonyos/compiler/hvigor/${VER_DIR}"

if [[ "$LIST_ONLY" -eq 1 ]]; then
  echo "7.26* candidates at $LIST_URL:"
  curl -fsSL "$LIST_URL" | grep -oE 'href="7\.26[^"]*/"' | sed -e 's/^href="//' -e 's#/"$##' | sort -V || true
  echo "resolved: $VER_DIR"
  exit 0
fi

echo ">>> using mirror dir: $VER_DIR"
mkdir -p "$DEST"
cd "$DEST"

echo ">>> download ${BASE_URL}/command-line-tools.tar"
curl -fL --retry 3 -o command-line-tools.tar "${BASE_URL}/command-line-tools.tar"
curl -fsSL -o command-line-tools.tar.sha256 "${BASE_URL}/command-line-tools.tar.sha256"

echo ">>> verify sha256"
EXPECTED="$(awk '{print $1}' command-line-tools.tar.sha256)"
ACTUAL="$(sha256sum command-line-tools.tar | awk '{print $1}')"
if [[ "$EXPECTED" != "$ACTUAL" ]]; then
  echo "ERROR: sha256 mismatch: expected $EXPECTED, got $ACTUAL" >&2
  exit 1
fi
echo "sha256 OK: $ACTUAL"

echo ">>> extract to $DEST/7.26.0.static/hvigor"
rm -rf 7.26.0.static/hvigor
mkdir -p 7.26.0.static/hvigor
tar -xf command-line-tools.tar -C 7.26.0.static/hvigor

[[ -x 7.26.0.static/hvigor/bin/hvigorw ]] || { echo "ERROR: bin/hvigorw missing" >&2; exit 1; }
echo "OK: $DEST/7.26.0.static/hvigor/bin/hvigorw"
echo
echo "静态工程配置（门禁模板）:"
echo '  build-profile.json5 : compileSdkVersion "26.1.0", compatibleSdkVersion "22", arkTSVersion "1.2"'
echo '  hvigor-config.json5 : modelVersion "26.0.0"'
echo '  oh-package.json5    : modelVersion "26.0.0"'
