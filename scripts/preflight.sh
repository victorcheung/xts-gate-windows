#!/usr/bin/env bash
# XTS 门禁叶子编译环境自检（只检查，不下载）
#
# 用法（WSL/Linux 内）:
#   ./preflight.sh [--json]
#
# 退出码: 0 = 四件套齐全；1 = 有缺失（按输出里的地址补，禁止拉整仓）
set -u

NODE_HOME="${NODE_HOME:-/root/ohos-gate/toolchain/node-v18.20.1-linux-x64}"
CLT="${CLT:-/root/ohos-gate/toolchain/clt-26.0.1.290}"
STA="${STA:-/root/ohos-gate/toolchain/hvigor-static/7.26.0.static/hvigor}"
SDK="${OHOS_BASE_SDK_HOME:-/root/ohos-gate/sdk}"
JAVA_HOME_DIR="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"

missing=0
ok() { echo "[OK]   $*"; }
miss() { echo "[MISS] $*"; missing=$((missing + 1)); }

echo "== XTS gate leaf-build preflight =="
[[ -x "$NODE_HOME/bin/node" ]] && ok "node: $NODE_HOME ($("$NODE_HOME/bin/node" -v 2>/dev/null))" \
  || miss "node 18.20.1: $NODE_HOME"
[[ -x "$CLT/bin/hvigorw" ]] && ok "dynamic hvigor: $CLT/bin/hvigorw" \
  || miss "command-line-tools 26.0.1.290: $CLT/bin/hvigorw"
[[ -x "$STA/bin/hvigorw" ]] && ok "static hvigor 7.26.0: $STA/bin/hvigorw" \
  || miss "static toolchain 7.26.0: $STA/bin/hvigorw"
[[ -d "$SDK" ]] && ok "SDK root: $SDK" || miss "Linux SDK root: $SDK"
[[ -d "$SDK/26.1.0/ets/static/build-tools" ]] && ok "SDK static build-tools: $SDK/26.1.0/ets/static/build-tools" \
  || miss "SDK 26.1.0 ets/static/build-tools under $SDK"
[[ -x "$JAVA_HOME_DIR/bin/java" ]] && ok "JDK: $JAVA_HOME_DIR" || miss "JDK 17: $JAVA_HOME_DIR"

cat <<'EOF'

缺失时的官方下载（只补缺的，单次 >200MB 先问用户）:
  node:   https://repo.huaweicloud.com/nodejs/v18.20.1/node-v18.20.1-linux-x64.tar.gz
  dyn:    https://repo.huaweicloud.com/harmonyos/compiler/hvigor/26.0.1.290/command-line-tools.tar
  static: bash scripts/fetch-static-toolchain.sh   # 自动选镜像最新 7.26*
  SDK:    本地已有 Linux SDK 优先；没有再用每日 ohos-sdk-full[_Dyn_Sta] 的 linux 组件

禁止: repo init / repo sync / git clone OpenHarmony 整仓 / build/prebuilts_download.sh
EOF

if [[ $missing -gt 0 ]]; then
  echo "RESULT: missing=$missing"
  exit 1
fi
echo "RESULT: OK (all four components present)"
