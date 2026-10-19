#!/usr/bin/env python3
"""体检当前机器的开发工具链，打印一张版本表。

用法:
    python env_report.py
    python env_report.py --json

新机器 / 重装系统后第一步跑它：缺什么、版本对不对，一眼看完。
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = [
    ("git", ["git", "--version"]),
    ("node", ["node", "--version"]),
    ("npm", ["npm", "--version"]),
    ("pnpm", ["pnpm", "--version"]),
    ("python", ["python", "--version"]),
    ("pip", ["pip", "--version"]),
    ("uv", ["uv", "--version"]),
    ("rg", ["rg", "--version"]),
    ("gh", ["gh", "--version"]),
    ("pwsh", ["pwsh", "--version"]),
    ("docker", ["docker", "--version"]),
    ("dotnet", ["dotnet", "--version"]),
]

SOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def run_version(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    argv = [exe] + cmd[1:]
    try:
        # .cmd/.bat（npm、pnpm）不能直接 CreateProcess，要交给 cmd.exe
        shell = exe.lower().endswith((".cmd", ".bat"))
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30, shell=shell)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    return text[0].strip() if text else None


def soffice_version() -> str | None:
    for path in SOFFICE:
        exe = path if Path(path).is_file() else shutil.which(path)
        if not exe:
            continue
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
            if out.stdout.strip():
                return out.stdout.strip().splitlines()[0]
        except (OSError, subprocess.TimeoutExpired):
            pass
        # GUI 版 soffice 不挂控制台，--version 常常什么都不打印，只能确认存在
        return f"已安装 ({exe})"
    return None


def main() -> int:
    # Windows 控制台默认 GBK，中文和符号会炸；统一按 UTF-8 输出
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    report = {}
    for name, cmd in TOOLS:
        report[name] = run_version(cmd)
    report["libreoffice"] = soffice_version()
    report["_os"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    report["_python"] = sys.version.split()[0]

    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"OS: {report['_os']}")
    print(f"Python runtime: {report['_python']}\n")
    width = max(len(k) for k in report if not k.startswith("_"))
    missing = []
    for name in [n for n, _ in TOOLS] + ["libreoffice"]:
        ver = report[name]
        if ver is None:
            missing.append(name)
            print(f"{name:<{width}}  [--] 未安装 / 不在 PATH")
        else:
            print(f"{name:<{width}}  {ver}")
    print()
    if missing:
        print("缺失: " + ", ".join(missing))
    else:
        print("工具链齐全")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
