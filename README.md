# playground

[![CI](https://github.com/samurai0x/playground/actions/workflows/ci.yml/badge.svg)](https://github.com/samurai0x/playground/actions/workflows/ci.yml)

一些日常在 Windows 上折腾时攒下来的小工具：环境、GitHub、Office 转换。

都是自用的，但尽量写成拿来就能跑的样子。

## 脚本

| 文件 | 作用 |
|---|---|
| [`pwsh/Refresh-Path.ps1`](pwsh/Refresh-Path.ps1) | 不动重启，把机器 + 用户环境变量里的 PATH 合并回当前会话 |
| [`pwsh/New-GithubKey.ps1`](pwsh/New-GithubKey.ps1) | 生成无口令 ed25519 SSH key，可一键上传到 GitHub |
| [`pwsh/New-GitHubRepo.ps1`](pwsh/New-GitHubRepo.ps1) | 目录里补 README/.gitignore/LICENSE，初始化并建仓推送 |
| [`python/office_convert.py`](python/office_convert.py) | 调 LibreOffice 无头模式批量转换 docx/xlsx/pptx → pdf 等 |
| [`python/env_report.py`](python/env_report.py) | 打印本机工具链版本表，缺什么一眼看到 |
| [`python/ocr.py`](python/ocr.py) | 图片 / PDF 中文 OCR（RapidOCR，PP-OCRv6） |

## 用法

### 刷新 PATH

winget 装完东西，已经开着的终端（尤其是被 GUI 程序拉起来的）里还是看不到新命令。
点源执行才会改当前会话：

```powershell
. .\pwsh\Refresh-Path.ps1
```

直接 `.\Refresh-Path.ps1` 只改子进程，命令跑完就恢复原样。

### 生成 SSH key

```powershell
.\pwsh\New-GithubKey.ps1 -Comment "1078512620@qq.com" -Upload -Title "workstation"
```

为什么绕一层 `.bat`：PowerShell 传 `-N ""` 时会把空字符串参数丢掉，ssh-keygen 收到的是
残缺参数，结果是钥匙带上了莫名其妙的口令（甚至口令就是两个引号字符），之后 `ssh -T`
一直 `Permission denied (publickey)`。交给 `cmd` 执行就没有这个问题。

脚本最后会用 `ssh-keygen -y -P ''` 验证一遍，确认真的无口令。

### 建仓库

```powershell
.\pwsh\New-GitHubRepo.ps1 -Name my-project -Description "一句话介绍" -Directory D:\Work\my-project
.\pwsh\New-GitHubRepo.ps1 -Name notes -Private          # 私有仓库
.\pwsh\New-GitHubRepo.ps1 -Name demo -WhatIf            # 只看会做什么
```

需要 `gh auth login` 已完成。

### Office 批量转 PDF

```powershell
python .\python\office_convert.py .\docs --to pdf --out .\dist
python .\python\office_convert.py report.docx deck.pptx --to pdf
```

找不到 soffice 时设置 `SOFFICE_BIN` 环境变量指向可执行文件。

### OCR

```powershell
python .\python\ocr.py scan.png
python .\python\ocr.py .\contracts --out out.txt     # 目录递归
python .\python\ocr.py report.pdf --json             # 带置信度，便于过滤
```

PDF 用 pypdfium2 渲染成位图再识别，不依赖 poppler。糊图可以用 `--min-score 0.85`
把明显不可信的行丢掉——实测 640px + JPEG q28 + 噪点的页面，PP-OCRv4 会把
「浏览器」认成「浏宽器」，PP-OCRv6 全对。

### 环境体检

```powershell
python .\python\env_report.py
python .\python\env_report.py --json
```

## 环境

- Windows 11 / PowerShell 5.1 与 7 都能跑（脚本按 5.1 语法写）
- Python 3.10+，只用了标准库
- LibreOffice（仅 `office_convert.py` 需要）、GitHub CLI（仅建仓/传 key 需要）
- `ocr.py` 额外要 `pip install rapidocr pypdfium2 pillow numpy`，其余脚本不需要

## License

MIT
