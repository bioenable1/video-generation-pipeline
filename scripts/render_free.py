#!/usr/bin/env python3
"""
Marketing-quality free renderer: stock footage, product images, Ken Burns,
lower-thirds, background music, crossfades. No paid APIs required.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    ROOT,
    ensure_project_dirs,
    is_paid_mode,
    load_production_config,
    load_shot_list,
    project_dir,
    save_json,
    utc_now_iso,
)

W, H = 1920, 1080
FPS = 30
FONT = "C\\\\:/Windows/Fonts/arialbd.ttf"
FONT_REG = "C\\\\:/Windows/Fonts/arial.ttf"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(r.stderr[-2000:] if r.stderr else r.stdout, file=sys.stderr)
        raise RuntimeError("ffmpeg failed")
    return r


def probe_duration(path: Path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(r.stdout.strip())


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\\\\\''").replace("%", "\\%")[:100]


async def tts(text: str, voice: str, out: Path, rate: str = "+8%") -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def generate_vo(slug: str, voice: str, force: bool) -> None:
    vo_dir = project_dir(slug) / "assets" / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)
    for scene in load_shot_list(slug)["scenes"]:
        sid = scene["id"]
        out = vo_dir / f"{sid}.mp3"
        if force and out.exists():
            out.unlink()
        if out.exists() and out.stat().st_size > 500:
            continue
        print(f"  VO {sid}")
        asyncio.run(tts(scene["narration"], voice, out))


def stock_path(slug: str, sid: str) -> Path | None:
    p = project_dir(slug) / "assets" / "stock" / f"{sid}.mp4"
    return p if p.exists() and p.stat().st_size > 50000 else None


def ken_burns_stock(stock: Path, duration: float, out: Path, headline: str, bullets: list[str], dramatic: bool = False) -> None:
    """Stock clip with slow zoom + branded lower-third."""
    frames = int(duration * FPS) + 10
    h = esc(headline)
    dim = "eq=brightness=-0.22:saturation=0.85," if dramatic else ""
    lower = (
        f"{dim}"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill,"
        f"drawbox=x=0:y=h-210:w=iw:h=210:color=black@0.6:t=fill,"
        f"drawbox=x=0:y=h-210:w=iw:h=6:color=0x3b82f6:t=fill,"
        f"drawtext=fontfile={FONT}:text='{h}':fontsize=48:fontcolor=white:"
        f"x=80:y=h-165:enable='gte(t,0.3)'"
    )
    for i, b in enumerate(bullets[:3]):
        bt = esc(b)
        lower += (
            f",drawtext=fontfile={FONT_REG}:text='{chr(0x25C6)}  {bt}':fontsize=30:fontcolor=0x93c5fd:"
            f"x=100:y={H - 120 + i * 38}:enable='gte(t,0.5)'"
        )
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},{lower},"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, duration - 0.5)}:d=0.5[v]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
        "-filter_complex", vf, "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
    ])


def product_composite(stock: Path, product_img: Path, duration: float, out: Path, headline: str) -> None:
    """Stock background + product image card + headline."""
    if not product_img.exists():
        ken_burns_stock(stock, duration, out, headline, [])
        return
    h = esc(headline)
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"eq=brightness=-0.12:saturation=0.95,boxblur=1[bg];"
        f"[1:v]scale=920:-1,format=rgba[prod];"
        f"[bg][prod]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2-30[composed];"
        f"[composed]drawbox=x=0:y=0:w=iw:h=110:color=black@0.55:t=fill,"
        f"drawtext=fontfile={FONT}:text='{h}':fontsize=42:fontcolor=white:x=70:y=38,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, duration - 0.5)}:d=0.5[v]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
        "-loop", "1", "-i", str(product_img),
        "-filter_complex", fc, "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
    ])


def logo_outro(stock: Path, logo: Path, duration: float, out: Path, headline: str, bullets: list[str]) -> None:
    h = esc(headline)
    bullet_fc = ""
    for i, b in enumerate(bullets[:2]):
        bt = esc(b)
        bullet_fc += (
            f",drawtext=fontfile={FONT_REG}:text='{bt}':fontsize=30:fontcolor=0x93c5fd:"
            f"x=(w-text_w)/2:y={680 + i * 40}"
        )
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.25[bg];"
        f"[1:v]format=rgba,scale=520:-1[lg];"
        f"[bg][lg]overlay=(W-w)/2:200[tmp];"
        f"[tmp]drawtext=fontfile={FONT}:text='{h}':fontsize=52:fontcolor=white:x=(w-text_w)/2:y=580"
        f"{bullet_fc},"
        f"drawtext=fontfile={FONT_REG}:text='Identify - Automate - Track':fontsize=28:fontcolor=0x8b9cb3:"
        f"x=(w-text_w)/2:y=780[v]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
        "-loop", "1", "-i", str(logo),
        "-filter_complex", fc, "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
    ])


def mux_av(video: Path, audio: Path, out: Path) -> None:
    run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def render_scene(slug: str, scene: dict, logo: Path, seg_dir: Path) -> Path:
    sid = scene["id"]
    vo = project_dir(slug) / "assets" / "vo" / f"{sid}.mp3"
    dur = probe_duration(vo) + 0.4
    stock = stock_path(slug, sid)
    if not stock:
        raise FileNotFoundError(f"No stock for {sid} — run fetch_free_stock.py first")

    silent = seg_dir / f"{sid}_v.mp4"
    vtype = scene.get("visual", {}).get("type", "stock_video")
    headline = scene.get("on_screen_text", "")
    bullets = scene.get("bullets", [])

    if vtype == "logo_slate":
        logo_outro(stock, logo, dur, silent, headline, bullets)
    elif vtype == "product_image":
        prod = project_dir(slug) / scene["visual"].get("source_path", "")
        product_composite(stock, prod, dur, silent, headline)
    else:
        dramatic = sid in ("s01", "s02")
        ken_burns_stock(stock, dur, silent, headline, bullets, dramatic=dramatic)

    out = seg_dir / f"{sid}.mp4"
    mux_av(silent, vo, out)
    silent.unlink(missing_ok=True)
    return out


def concat_with_music(segments: list[Path], music: Path | None, out: Path) -> None:
    lst = out.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{s.resolve().as_posix()}'" for s in segments) + "\n")
    draft = out.with_name("draft_muxed.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(draft)])
    lst.unlink(missing_ok=True)

    if music and music.exists():
        run([
            "ffmpeg", "-y", "-i", str(draft), "-i", str(music),
            "-filter_complex",
            "[0:a]volume=1.0[vo];[1:a]volume=0.12,aloop=loop=-1:size=2e+09[bg];"
            "[vo][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(out),
        ])
        draft.unlink(missing_ok=True)
    else:
        draft.rename(out)


def render_free(slug: str, force: bool = False) -> Path:
    if is_paid_mode(slug):
        print("Paid mode — use voiceover + veed scripts")
        sys.exit(1)

    cfg = load_production_config(slug)
    voice = cfg.get("free", {}).get("voice", "en-US-ChristopherNeural")
    base = ensure_project_dirs(slug)
    logo = base / "assets" / "brand" / "logo-dark-bg.png"
    if not logo.exists():
        logo = base / "assets" / "brand" / "logo-transparent.png"

    # Prerequisite steps
    print("=== Marketing render (free) ===")
    print("1. Extract assets + stock + research")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "extract_assets.py"), "--project", slug], check=False)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_free_stock.py"), "--project", slug], check=False)
    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "research.py"), "--project", slug,
        "--urls", "https://www.youtube.com/watch?v=d58Kduairis",
        "https://www.youtube.com/watch?v=e_04ZrNroTo",
    ], check=False)

    print("2. Voiceover")
    generate_vo(slug, voice, force=force)

    seg_dir = base / "renders" / "segments"
    if force and seg_dir.exists():
        import shutil
        shutil.rmtree(seg_dir)
    seg_dir.mkdir(parents=True, exist_ok=True)

    print("3. Scene composites")
    segments = []
    for scene in load_shot_list(slug)["scenes"]:
        print(f"  {scene['id']}")
        segments.append(render_scene(slug, scene, logo, seg_dir))

    music = base / "assets" / "music" / "background.mp3"
    final = base / "renders" / "final.mp4"
    print("4. Concat + music")
    concat_with_music(segments, music, final)

    save_json(base / "assets" / "manifest.json", {
        "updated_at": utc_now_iso(),
        "production_mode": "free",
        "renderer": "render_free.py (marketing)",
        "stock": True,
        "music": music.exists(),
    })
    print(f"\nDone: {final} ({probe_duration(final):.0f}s)")
    return final


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--force", action="store_true", help="Regenerate VO and segments")
    args = p.parse_args()
    render_free(args.project, force=args.force)


if __name__ == "__main__":
    main()
