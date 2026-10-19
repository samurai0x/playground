<#
.SYNOPSIS
  刷新当前 PowerShell 会话的 PATH。

.DESCRIPTION
  用 winget / 安装器新装的工具通常会写进机器或用户环境变量，但已经跑着的
  shell（尤其是被 GUI 宿主派生的 shell）继承的还是启动时的旧 PATH。

  必须「点源」执行，环境变量才会留在当前会话：

      . .\pwsh\Refresh-Path.ps1

  直接 .\Refresh-Path.ps1 执行只会改子进程，命令跑完就没了。

.EXAMPLE
  . .\Refresh-Path.ps1
  Get-Command node, python, gh -ErrorAction SilentlyContinue
#>
[CmdletBinding()]
param()

$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')

$merged = @($machinePath, $userPath) | Where-Object { $_ } | ForEach-Object { $_ -split ';' }
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
$clean = @()
foreach ($p in $merged) {
    $p = $p.Trim()
    if ($p -and $seen.Add($p)) { $clean += $p }
}

$env:Path = $clean -join ';'
Write-Verbose ("PATH entries: {0}" -f $clean.Count)
