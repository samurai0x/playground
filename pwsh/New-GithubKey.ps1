<#
.SYNOPSIS
  生成一把无口令的 ed25519 SSH key，并可选地上传到 GitHub。

.DESCRIPTION
  坑：PowerShell 传空字符串参数时会把参数丢掉，`ssh-keygen -N ""` 实际会变成
  `ssh-keygen -N`，于是 ssh-keygen 把口令设成「用户输入」或干脆把后面的 -f 吃掉，
  常见结果是拿到一把带奇怪口令的钥匙（例如口令正好是两个引号字符），
  之后 ssh 连接一直 Permission denied (publickey)。

  这里用 .bat 包一层交给 cmd 执行，让 `-N ""` 原样传进去。

.EXAMPLE
  .\pwsh\New-GithubKey.ps1 -Comment "me@example.com"

.EXAMPLE
  .\pwsh\New-GithubKey.ps1 -Comment "me@example.com" -Upload -Title "workstation"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Comment,

    [string]$KeyPath = (Join-Path $env:USERPROFILE '.ssh\id_ed25519'),

    [switch]$Upload,

    [string]$Title = ("{0} {1}" -f $env:COMPUTERNAME, (Get-Date -Format 'yyyy-MM-dd')),

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if ((Test-Path $KeyPath) -and -not $Force) {
    Write-Error "已存在: $KeyPath（要覆盖请加 -Force）"
    return
}
if ($Force) {
    Remove-Item -LiteralPath $KeyPath, "$KeyPath.pub" -Force -ErrorAction SilentlyContinue
}

$dir = Split-Path -Parent $KeyPath
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

$bat = Join-Path $env:TEMP ("sshkey-{0}.bat" -f [guid]::NewGuid().ToString('N'))
$lines = @(
    '@echo off',
    ('ssh-keygen -t ed25519 -C "{0}" -f "{1}" -N "" -q' -f $Comment, $KeyPath),
    'if errorlevel 1 exit /b 1',
    # 同一层验证：不带口令也能导出公钥 -> 真的无口令；有口令时 ssh-keygen -y 会失败
    ('ssh-keygen -y -P "" -f "{0}" >nul 2>&1' -f $KeyPath),
    'if errorlevel 1 exit /b 3',
    'exit /b 0'
)
Set-Content -LiteralPath $bat -Value $lines -Encoding ASCII

$code = 0
try {
    cmd /c "`"$bat`""
    $code = $LASTEXITCODE
}
finally {
    Remove-Item -LiteralPath $bat -Force -ErrorAction SilentlyContinue
}
if ($code -eq 1) { throw 'ssh-keygen 生成密钥失败' }
if ($code -eq 3) { Write-Warning '钥匙似乎带口令：ssh-keygen -y 无法无口令导出' }

$pub = Get-Content -LiteralPath "$KeyPath.pub" -Raw
Write-Host "已生成 $KeyPath"
Write-Host $pub.Trim()

if ($Upload) {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { Write-Warning '未找到 gh，跳过上传（可手动粘贴公钥到 GitHub Settings → SSH keys）'; return }
    gh ssh-key add "$KeyPath.pub" --title $Title
    if ($LASTEXITCODE -eq 0) { Write-Host "已上传到 GitHub，标题: $Title" }
    else { Write-Warning "gh ssh-key add 失败，退出码 $LASTEXITCODE" }
}
