#!/usr/bin/env python3
"""Extract product images from brochure PDF and BioEnable website."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import project_dir


def pdf_to_images(pdf: Path, out_dir: Path) -> list[Path]:
    import fitz

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    doc = fitz.open(pdf)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        p = out_dir / f"brochure-page{i + 1}.png"
        pix.save(str(p))
        paths.append(p)
    doc.close()
    return paths


def scrape_website_images(url: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    # Google Sites / embedded images
    patterns = [
        r'https://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',
        r'https://lh3\.googleusercontent\.com/[^\s"\'<>]+',
    ]
    urls: set[str] = set()
    for pat in patterns:
        urls.update(re.findall(pat, html, re.I))

    saved = []
    for i, img_url in enumerate(sorted(urls)[:15]):
        try:
            r = requests.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            ext = ".jpg" if "jpeg" in img_url or "jpg" in img_url else ".png"
            p = out_dir / f"web-{i + 1:02d}{ext}"
            p.write_bytes(r.content)
            if p.stat().st_size > 5000:
                saved.append(p)
        except Exception:
            continue
    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    base = project_dir(args.project)
    img_dir = base / "assets" / "images"

    brochure = base / "assets" / "brochure.pdf"
    if brochure.exists():
        pages = pdf_to_images(brochure, img_dir / "brochure")
        print(f"Brochure: {len(pages)} pages -> {img_dir / 'brochure'}")

    web = scrape_website_images(
        "https://www.bioenabletech.com/iriuniverse-two-dual-iris-scanner",
        img_dir / "website",
    )
    print(f"Website: {len(web)} images -> {img_dir / 'website'}")


if __name__ == "__main__":
    main()
