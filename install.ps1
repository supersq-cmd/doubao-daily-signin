# 把 doubao-daily-signin 安装到豆包的技能目录。
# 用法：powershell -ExecutionPolicy Bypass -File .\install.ps1
# 可选参数：-SkillsRoot "自定义技能目录"

param(
    [string]$SkillsRoot = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here "doubao-daily-signin"
if (-not (Test-Path $src)) { $src = $here }   # 已经在技能文件夹内执行

if (-not (Test-Path (Join-Path $src "SKILL.md"))) {
    Write-Host "没有找到 SKILL.md，请在解压后的 doubao-daily-signin 目录（或其上一级）执行本脚本。" -ForegroundColor Red
    exit 1
}

if (-not $SkillsRoot) {
    $base = Join-Path $env:LOCALAPPDATA "Doubao\User Data\Default\.doubao\agent_mode\workspace"
    $SkillsRoot = Join-Path $base ".user_skills"
}

if (-not (Test-Path $SkillsRoot)) {
    New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null
}

$dst = Join-Path $SkillsRoot "doubao-daily-signin"
if (Test-Path $dst) {
    $bak = "$dst.bak-" + (Get-Date -Format "yyyyMMddHHmmss")
    Move-Item -LiteralPath $dst -Destination $bak
    Write-Host "已存在的旧版本已备份到：$bak"
}
Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force

Write-Host ""
Write-Host "已安装到：$dst" -ForegroundColor Green
Write-Host "下一步："
Write-Host "  1. 完全退出并重新打开豆包客户端"
Write-Host "  2. 在对话里说「豆包签到」"
Write-Host "  3. 想定时签到就说「每天 7:20 签到」"
