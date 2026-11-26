#!/usr/bin/env bash
# XTS 门禁叶子编译（WSL/Linux）
#
# 用法:
#   ./run-gate-build.sh --project <suite> --mode dyn|sta \
#     --node-home <node18> --sdk <sdk-root> --hvigor-home <hvigor-dir> \
#     [--java-home <jdk>] [--ohpm <ohpm>] [--skip-install]
#
# 说明:
#   - hvigor-home 是包含 bin/hvigorw 的目录。
#   - 动态用门禁 command-line-tools 的 hvigor（6.26.21）。
#   - 静态用 7.26.0 ArkTS 1.2 工具（解压为 7.26.0.static/hvigor）；
#     本地 hvigor 5.14.2 只能做老近似，不能作为门禁证据。
#   - 只在 WSL/Linux 内运行；不要在 Windows 原生 bash 里跑。
set -euo pipefail

PROJECT=""
MODE="dyn"
NODE_HOME=""
SDK_ROOT=""
HVIGOR_HOME=""
JAVA_HOME_ARG=""
OHPM=""
SKIP_INSTALL=0

usage() {
  cat <<'EOF'
XTS gate leaf build (WSL/Linux)

Usage:
  run-gate-build.sh --project <suite> --mode dyn|sta \
    --node-home <node18> --sdk <sdk-root> --hvigor-home <hvigor-dir> \
    [--java-home <jdk>] [--ohpm <ohpm>] [--skip-install]

Required:
  --project       suite directory (contains BUILD.gn)
  --mode          dyn | sta
  --node-home     node 18.20.1 home (contains bin/node)
  --sdk           SDK root (contains <version>/{ets,js,native,previewer,toolchains})
  --hvigor-home   directory containing bin/hvigorw

Optional:
  --java-home     JAVA_HOME for HAP packaging
  --ohpm          ohpm executable; default: <clt>/ohpm/bin/ohpm or PATH
  --skip-install  skip ohpm install
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --node-home) NODE_HOME="$2"; shift 2 ;;
    --sdk) SDK_ROOT="$2"; shift 2 ;;
    --hvigor-home) HVIGOR_HOME="$2"; shift 2 ;;
    --java-home) JAVA_HOME_ARG="$2"; shift 2 ;;
    --ohpm) OHPM="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT" ]] || die "--project is required"
[[ -d "$PROJECT" ]] || die "project not found: $PROJECT"
[[ "$MODE" == "dyn" || "$MODE" == "sta" ]] || die "--mode must be dyn or sta"
[[ -n "$NODE_HOME" && -x "$NODE_HOME/bin/node" ]] || die "node not found: $NODE_HOME/bin/node"
[[ -n "$SDK_ROOT" && -d "$SDK_ROOT" ]] || die "sdk not found: $SDK_ROOT"
[[ -n "$HVIGOR_HOME" && -x "$HVIGOR_HOME/bin/hvigorw" ]] || die "hvigorw not found: $HVIGOR_HOME/bin/hvigorw"

export DEVECO_NODE_HOME="$NODE_HOME"
export PATH="$NODE_HOME/bin:$PATH"
export OHOS_BASE_SDK_HOME="$SDK_ROOT"
if [[ -n "$JAVA_HOME_ARG" ]]; then
  export JAVA_HOME="$JAVA_HOME_ARG"
  export PATH="$JAVA_HOME/bin:$PATH"
fi

# 门禁 compile_app.py 会写 local.properties；这里备份/恢复，避免污染工程
LOCAL_PROPS="$PROJECT/local.properties"
BACKUP=""
if [[ -f "$LOCAL_PROPS" ]]; then
  BACKUP="$(mktemp)"
  cp "$LOCAL_PROPS" "$BACKUP"
fi
cleanup() {
  if [[ -n "$BACKUP" && -f "$BACKUP" ]]; then
    cp "$BACKUP" "$LOCAL_PROPS"
    rm -f "$BACKUP"
  else
    rm -f "$LOCAL_PROPS"
  fi
}
trap cleanup EXIT

printf 'sdk.dir=%s\n' "$SDK_ROOT" > "$LOCAL_PROPS"

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  if [[ -z "$OHPM" ]]; then
    # 优先同目录 command-line-tools 的 ohpm
    CLT_ROOT="$(cd "$HVIGOR_HOME/.." && pwd)"
    if [[ -x "$CLT_ROOT/ohpm/bin/ohpm" ]]; then
      OHPM="$CLT_ROOT/ohpm/bin/ohpm"
    elif command -v ohpm >/dev/null 2>&1; then
      OHPM="$(command -v ohpm)"
    fi
  fi
  if [[ -n "$OHPM" && -x "$OHPM" ]]; then
    echo ">>> ohpm install ($OHPM)"
    ( cd "$PROJECT" && "$OHPM" install ) || {
      echo "WARN: ohpm install failed; retry with --skip-install if oh_modules is already prepared" >&2
      exit 1
    }
  else
    echo "WARN: ohpm not found; skip install (use --ohpm or prepare oh_modules manually)" >&2
  fi
fi

cd "$PROJECT"
if [[ "$MODE" == "dyn" ]]; then
  echo ">>> dynamic gate build"
  "$HVIGOR_HOME/bin/hvigorw" --mode module -p module=entry@ohosTest assembleHap \
    -p debuggable=false -p hvigor-obfuscation=false --no-daemon
  HAP_DIR="entry/build/default/outputs/ohosTest"
else
  echo ">>> static build (7.26.0 ArkTS 1.2 tool root; 5.14.2 is legacy-approximate)"
  "$HVIGOR_HOME/bin/hvigorw" --mode project -p product=default assembleApp \
    -p debuggable=false -p hvigor-obfuscation=false --no-daemon
  HAP_DIR="entry/build/default/outputs/default"
fi

HAP="$(find "$HAP_DIR" -maxdepth 2 -name '*-unsigned.hap' -print -quit 2>/dev/null || true)"
if [[ -z "$HAP" ]]; then
  echo "ERROR: no unsigned HAP under $HAP_DIR" >&2
  exit 1
fi
echo "BUILD OK: $PROJECT/$HAP"
