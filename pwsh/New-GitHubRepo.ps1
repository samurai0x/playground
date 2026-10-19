<#
.SYNOPSIS
  在当前目录初始化并推送一个新的 GitHub 仓库。

.DESCRIPTION
  依赖已登录的 gh（`gh auth status`）。流程：
    1. 在目标目录写 README.md / .gitignore / LICENSE（缺什么补什么）
    2. git init + 首次提交
    3. gh repo create --source . --push 一步建仓并推送

.EXAMPLE
  .\pwsh\New-GitHubRepo.ps1 -Name playground -Description "小工具与脚本" -Directory D:\Work\playground

.EXAMPLE
  .\pwsh\New-GitHubRepo.ps1 -Name secret-notes -Private

.EXAMPLE
  .\pwsh\New-GitHubRepo.ps1 -Name demo -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    [string]$Description = '',

    [string]$Directory = (Get-Location).Path,

    [switch]$Private,

    [string]$DefaultBranch = 'main'
)

$ErrorActionPreference = 'Stop'

function Write-Utf8 {
    param([string]$Path, [string]$Text)
    $enc = New-Object System.Text.UTF8Encoding($false)   # 不带 BOM，跨平台友好
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw '未找到 gh，请先安装 GitHub CLI 并 gh auth login'
}

$owner = gh api user --jq '.login' 2>$null
if ($LASTEXITCODE -ne 0 -or -not $owner) { throw 'gh 未登录，先执行 gh auth login' }
$repoFull = "$owner/$Name"

if (-not (Test-Path $Directory)) { New-Item -ItemType Directory -Force -Path $Directory | Out-Null }
Push-Location $Directory
try {
    if ($PSCmdlet.ShouldProcess($Directory, '写 README / .gitignore / LICENSE')) {
        if (-not (Test-Path 'README.md')) {
            Write-Utf8 'README.md' ("# {0}`n`n{1}`n" -f $Name, $Description)
        }
        if (-not (Test-Path '.gitignore')) {
            Write-Utf8 '.gitignore' (@(
                'node_modules/', '__pycache__/', '.venv/', '*.pyc',
                'dist/', 'build/', '.DS_Store', 'Thumbs.db'
            ) -join "`n")
        }
        if (-not (Test-Path 'LICENSE')) {
            $year = Get-Date -Format yyyy
            Write-Utf8 'LICENSE' (@(
                'MIT License',
                '',
                "Copyright (c) $year $owner",
                '',
                'Permission is hereby granted, free of charge, to any person obtaining a copy',
                'of this software and associated documentation files (the "Software"), to deal',
                'in the Software without restriction, including without limitation the rights',
                'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell',
                'copies of the Software, and to permit persons to whom the Software is',
                'furnished to do so, subject to the following conditions:',
                '',
                'The above copyright notice and this permission notice shall be included in all',
                'copies or substantial portions of the Software.',
                '',
                'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR',
                'IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,',
                'FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE',
                'AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER',
                'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,',
                'OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE',
                'SOFTWARE.'
            ) -join "`n")
        }
    }

    if (-not (Test-Path (Join-Path $Directory '.git'))) {
        if ($PSCmdlet.ShouldProcess($Directory, 'git init')) {
            git init -b $DefaultBranch 2>&1 | Out-Null
        }
    }

    if (Test-Path (Join-Path $Directory '.git')) {
        git add -A 2>&1 | Out-Null
        $staged = git diff --cached --name-only
        if ($staged) {
            if ($PSCmdlet.ShouldProcess($repoFull, 'git commit -m "Initial commit"')) {
                git commit -m 'Initial commit' 2>&1 | Out-Null
            }
        }
    }
    elseif (-not $WhatIfPreference) {
        throw 'git init 没有成功，目录里没有 .git'
    }

    $visibility = '--public'
    if ($Private) { $visibility = '--private' }

    if ($PSCmdlet.ShouldProcess($repoFull, "gh repo create $visibility --source . --push")) {
        $ghArgs = @('repo', 'create', $repoFull, $visibility, '--source', '.', '--remote', 'origin', '--push')
        if ($Description) { $ghArgs += @('--description', $Description) }
        & gh @ghArgs
        if ($LASTEXITCODE -ne 0) { throw "gh repo create 失败，退出码 $LASTEXITCODE" }
    }
}
finally {
    Pop-Location
}
