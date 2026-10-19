#!/usr/bin/env python3
"""用 LibreOffice 无头模式批量转换 Office 文档（docx/xlsx/pptx/odt/... -> pdf/...）。

用法:
    python office_convert.py report.docx deck.pptx --to pdf
    python office_convert.py . --to pdf --out dist        # 目录递归
    python office_convert.py book.xlsx --to csv

依赖: 安装 LibreOffice 后自带 soffice（Windows 默认在
C:/Program Files/LibreOffice/program/soffice.exe）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

OFFICE_EXTS = {
    ".doc", ".docx", ".odt", ".rtf", ".txt", ".html",
    ".xls", ".xlsx", ".ods", ".csv",
    ".ppt", ".pptx", ".odp",
}

SOFFICE_CANDIDATES = [
    os.environ.get("SOFFICE_BIN", ""),
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice() -> str:
    for cand in SOFFICE_CANDIDATES:
        if cand and Path(cand).is_file():
            return cand
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    sys.exit("找不到 soffice：安装 LibreOffice，或设置环境变量 SOFFICE_BIN 指向可执行文件")


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in OFFICE_EXTS:
                    files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            print(f"[跳过] 不存在: {p}", file=sys.stderr)
    return files


def convert(soffice: str, src: Path, fmt: str, out_dir: Path) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        soffice, "--headless", "--norestore", "--convert-to", fmt,
        "--outdir", str(out_dir), str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    expected = out_dir / f"{src.stem}.{fmt.split(':')[0]}"
    ok = proc.returncode == 0 and expected.is_file()
    status = "OK  " if ok else "FAIL"
    print(f"[{status}] {src.name} -> {expected.name}")
    if not ok and (proc.stderr or proc.stdout):
        print((proc.stderr or proc.stdout).strip(), file=sys.stderr)
    return ok


def main() -> int:
    try:  # Windows 控制台默认 GBK，中文输出会乱码
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    ap = argparse.ArgumentParser(description="LibreOffice 无头批量转换")
    ap.add_argument("inputs", nargs="+", help="文件或目录（目录会递归）")
    ap.add_argument("--to", default="pdf", help="目标格式，默认 pdf；也可 csv / txt / docx ...")
    ap.add_argument("--out", default=None, help="输出目录，默认与源文件同目录")
    args = ap.parse_args()

    soffice = find_soffice()
    files = collect(args.inputs)
    if not files:
        print("没有可转换的文件", file=sys.stderr)
        return 1

    failures = 0
    for src in files:
        out_dir = Path(args.out) if args.out else src.parent
        if not convert(soffice, src, args.to, out_dir):
            failures += 1

    print(f"\n完成: {len(files) - failures}/{len(files)} 成功")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
