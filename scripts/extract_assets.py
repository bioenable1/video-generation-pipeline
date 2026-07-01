#!/usr/bin/env python3
"""Extract images from project source materials (PDF, website URLs in brief)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import parse_brief_urls, project_dir


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
    parser.add_argument("--url", action="append", help="Website URL to scrape (overrides brief)")
    args = parser.parse_args()

    base = project_dir(args.project)
    img_dir = base / "assets" / "images"
    source_dir = base / "assets" / "source"

    for pdf in list(base.glob("assets/**/*.pdf")) + list(source_dir.glob("*.pdf")):
        rel = pdf.relative_to(base)
        out_name = "brochure" if "brochure" in pdf.name.lower() else pdf.stem
        pages = pdf_to_images(pdf, img_dir / out_name)
        print(f"PDF {rel}: {len(pages)} pages -> {img_dir / out_name}")

    urls = args.url or []
    if not urls:
        urls = [u for u in parse_brief_urls(base / "brief.md") if "youtube" not in u.lower()]

    for i, url in enumerate(urls):
        sub = img_dir / f"website-{i + 1}" if len(urls) > 1 else img_dir / "website"
        web = scrape_website_images(url, sub)
        print(f"Website {url}: {len(web)} images -> {sub}")

    if not urls and not list(base.glob("assets/**/*.pdf")):
        print("No source PDFs or website URLs found — add to brief.md or assets/source/")


if __name__ == "__main__":
    main()
