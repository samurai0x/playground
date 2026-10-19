#!/usr/bin/env python3
"""用 RapidOCR（PP-OCRv6，纯 onnxruntime）识别图片和 PDF 里的文字。

为什么用它：Windows 自带的 OCR 只有系统语言包那几种排版模型，扫描件、截图、
糊掉的会议照片经常整行漏字；RapidOCR 的识别模型对中文混排明显更稳，而且
不需要装 PaddlePaddle，pip 一个包就能跑。

    python ocr.py scan.png                 # 单图
    python ocr.py contracts/*.pdf           # 多文件，PDF 逐页渲染
    python ocr.py report.pdf --json         # 带坐标和置信度
    python ocr.py shots/ --out out.txt      # 目录递归，结果另存

PDF 用 pypdfium2 渲染成位图再识别，不依赖 poppler。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


def _configure_stdout() -> None:
    # Windows 控制台默认 GBK，中文和框线字符会炸。
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def make_engine():
    try:
        from rapidocr import RapidOCR
    except ImportError:
        sys.exit(
            "缺少依赖：pip install rapidocr\n"
            "（旧版包名 rapidocr-onnxruntime 也能用，但准确率低一档）"
        )
    return RapidOCR()


def collect_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in targets:
        path = Path(raw).expanduser()
        if path.is_dir():
            files.extend(
                p for p in sorted(path.rglob("*"))
                if p.suffix.lower() in IMAGE_SUFFIXES or p.suffix.lower() == ".pdf"
            )
        elif path.exists():
            files.append(path)
        else:
            print(f"[跳过] 不存在：{path}", file=sys.stderr)
    return files


def image_to_pages(path: Path) -> list[tuple[str, object]]:
    """返回 [(页标签, PIL.Image)]；单图就是一页。"""
    from PIL import Image

    if path.suffix.lower() != ".pdf":
        return [("", Image.open(path).convert("RGB"))]

    import pypdfium2 as pdfium

    pages = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        for index in range(len(pdf)):
            bitmap = pdf[index].render(scale=2.0)
            pages.append((f"第 {index + 1} 页", bitmap.to_pil().convert("RGB")))
    finally:
        pdf.close()
    return pages


def run(engine, image) -> list[dict]:
    import numpy as np

    result = engine(np.array(image))
    texts = getattr(result, "txts", None)
    if texts is None:  # 兼容 rapidocr-onnxruntime 的 (list, elapse) 返回
        boxes, texts, scores = [], [], []
        for item in (result[0] or []):
            boxes.append(item[0]); texts.append(item[1]); scores.append(item[2])
        return [{"text": t, "score": round(float(s), 4)} for t, s in zip(texts, scores)]

    scores = getattr(result, "scores", None) or [0.0] * len(texts)
    return [{"text": t, "score": round(float(s), 4)} for t, s in zip(texts, scores)]


def main() -> int:
    parser = argparse.ArgumentParser(description="RapidOCR 识别图片 / PDF 文字")
    parser.add_argument("targets", nargs="+", help="图片、PDF 或目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON（含每行置信度）")
    parser.add_argument("--min-score", type=float, default=0.0, help="低于该置信度的行丢弃，默认 0")
    parser.add_argument("--out", help="把纯文本结果写到这个文件")
    args = parser.parse_args()

    _configure_stdout()
    files = collect_files(args.targets)
    if not files:
        print("没有可识别的文件", file=sys.stderr)
        return 1

    engine = make_engine()
    report: list[dict] = []
    text_chunks: list[str] = []

    for path in files:
        for label, image in image_to_pages(path):
            lines = [ln for ln in run(engine, image) if ln["score"] >= args.min_score]
            name = path.name if not label else f"{path.name} {label}"
            if args.json:
                report.append({"file": str(path), "page": label or None, "lines": lines})
            else:
                print(f"=== {name} ({len(lines)} 行) ===")
                for line in lines:
                    print(line["text"])
                print()
            text_chunks.append("\n".join(ln["text"] for ln in lines))

    if args.json:
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        print(payload)
    if args.out:
        Path(args.out).write_text("\n\n".join(text_chunks), encoding="utf-8")
        print(f"已写入 {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
