# Windows 侧调用 WSL 的 XTS 门禁编译包装。
#
# 该脚本不运行 Windows 原生 hvigor；它把参数传给 WSL 内的 run-gate-build.sh，
# 保证编译发生在 Linux 工具链上。
#
# 用法示例:
#   .\run-gate-build.ps1 -Distro Ubuntu `
#     -Project /root/ohos-gate/ws/test/xts/acts/.../ActsXxx `
#     -Mode dyn `
#     -NodeHome /root/ohos-gate/toolchain/node-v18.20.1-linux-x64 `
#     -SdkRoot /root/ohos-gate/sdk `
#     -HvigorHome /root/ohos-gate/toolchain/clt-26.0.1.290/hvigor `
#     -JavaHome /usr/lib/jvm/java-17-openjdk-amd64
#
# 若 run-gate-build.sh 在 Windows 目录，脚本会自动转成 /mnt/<drive>/... 路径。

param(
    [string]$Distro = "Ubuntu",
    [Parameter(Mandatory = $true)][string]$Project,
    [ValidateSet("dyn", "sta")][string]$Mode = "dyn",
    [Parameter(Mandatory = $true)][string]$NodeHome,
    [Parameter(Mandatory = $true)][string]$SdkRoot,
    [Parameter(Mandatory = $true)][string]$HvigorHome,
    [string]$JavaHome = "",
    [string]$Ohpm = "",
    [string]$ScriptPath = "",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

function To-WslPath([string]$Path) {
    if ($Path -match '^([A-Za-z]):[\\/]*(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    return $Path
}

function Quote-Bash([string]$Value) {
    # 单引号包裹，内部单引号用 '\'' 转义
    return "'" + ($Value -replace "'", "'\''") + "'"
}

if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Join-Path $PSScriptRoot "run-gate-build.sh"
}
$ScriptInWsl = To-WslPath $ScriptPath

$cmdParts = @(
    "bash", (Quote-Bash $ScriptInWsl),
    "--project", (Quote-Bash $Project),
    "--mode", (Quote-Bash $Mode),
    "--node-home", (Quote-Bash $NodeHome),
    "--sdk", (Quote-Bash $SdkRoot),
    "--hvigor-home", (Quote-Bash $HvigorHome)
)
if (-not [string]::IsNullOrWhiteSpace($JavaHome)) {
    $cmdParts += @("--java-home", (Quote-Bash $JavaHome))
}
if (-not [string]::IsNullOrWhiteSpace($Ohpm)) {
    $cmdParts += @("--ohpm", (Quote-Bash $Ohpm))
}
if ($SkipInstall) {
    $cmdParts += "--skip-install"
}

$bashCmd = $cmdParts -join " "
Write-Host ">>> wsl -d $Distro -- bash -lc $bashCmd" -ForegroundColor Cyan

# PowerShell 5.1 会把原生命令的 stderr 包成 ErrorRecord；$ErrorActionPreference=Stop
# 会让脚本在 hvigor 的 WARN 输出时误退出。调用 wsl 期间改为 Continue，按退出码判断。
$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& wsl -d $Distro -- bash -lc $bashCmd
$rc = $LASTEXITCODE
$ErrorActionPreference = $oldEap
exit $rc
