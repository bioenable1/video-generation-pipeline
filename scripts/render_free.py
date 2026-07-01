#!/usr/bin/env python3
"""
Universal free renderer: stock footage, product images, Ken Burns,
lower-thirds, background music. Works for any video type and brand.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    ROOT,
    aspect_dimensions,
    ensure_project_dirs,
    is_paid_mode,
    load_brand,
    load_production_config,
    load_shot_list,
    parse_brief_urls,
    project_dir,
    resolve_logo_path,
    save_json,
    utc_now_iso,
)

FPS = 30


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


def font_path(brand: dict, style: str = "heading") -> str:
    """FFmpeg drawtext font path (Windows drive colon must be C\\:/...)."""
    path = brand.get("font", {}).get(style, "C:/Windows/Fonts/arialbd.ttf")
    path = path.replace("\\", "/")
    if len(path) > 1 and path[1] == ":":
        return path[0] + "\\\\:" + path[2:]
    return path


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


def ken_burns_stock(
    stock: Path, duration: float, out: Path, headline: str, bullets: list[str],
    brand: dict, w: int, h: int, dramatic: bool = False,
) -> None:
    frames = int(duration * FPS) + 10
    h_esc = esc(headline)
    primary = brand["colors"]["primary"]
    accent = brand["colors"]["accent"]
    dim = "eq=brightness=-0.22:saturation=0.85," if dramatic else ""
    lower = (
        f"{dim}"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill,"
        f"drawbox=x=0:y=0:w=iw:h=210:color=black@0.6:t=fill,"
        f"drawbox=x=0:y=0:w=iw:h=6:color={primary}:t=fill,"
        f"drawtext=fontfile={font_path(brand)}:text='{h_esc}':fontsize=48:fontcolor=white:"
        f"x=80:y=45:enable='gte(t,0.3)'"
    )
    bar_h = 210 if h > w else 210
    if h > w:
        lower = (
            f"{dim}"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill,"
            f"drawbox=x=0:y=h-{bar_h}:w=iw:h={bar_h}:color=black@0.6:t=fill,"
            f"drawbox=x=0:y=h-{bar_h}:w=iw:h=6:color={primary}:t=fill,"
            f"drawtext=fontfile={font_path(brand)}:text='{h_esc}':fontsize=42:fontcolor=white:"
            f"x=60:y=h-{bar_h - 45}:enable='gte(t,0.3)'"
        )
    for i, b in enumerate(bullets[:3]):
        bt = esc(b)
        y_pos = (h - 120 + i * 38) if h <= w else (h - bar_h + 80 + i * 38)
        lower += (
            f",drawtext=fontfile={font_path(brand, 'body')}:text='{chr(0x25C6)}  {bt}':fontsize=30:fontcolor={accent}:"
            f"x=100:y={y_pos}:enable='gte(t,0.5)'"
        )
    vf = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={w}x{h}:fps={FPS},{lower},"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, duration - 0.5)}:d=0.5[v]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
        "-filter_complex", vf, "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
    ])


def product_composite(
    stock: Path, product_img: Path, duration: float, out: Path,
    headline: str, brand: dict, w: int, h: int,
) -> None:
    if not product_img.exists():
        ken_burns_stock(stock, duration, out, headline, [], brand, w, h)
        return
    h_esc = esc(headline)
    card_w = min(920, w - 80)
    fc = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"eq=brightness=-0.12:saturation=0.95,boxblur=1[bg];"
        f"[1:v]scale={card_w}:-1,format=rgba[prod];"
        f"[bg][prod]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2-30[composed];"
        f"[composed]drawbox=x=0:y=0:w=iw:h=110:color=black@0.55:t=fill,"
        f"drawtext=fontfile={font_path(brand)}:text='{h_esc}':fontsize=42:fontcolor=white:x=70:y=38,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, duration - 0.5)}:d=0.5[v]"
    )
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
        "-loop", "1", "-i", str(product_img),
        "-filter_complex", fc, "-map", "[v]", "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
    ])


def text_card(stock: Path, duration: float, out: Path, headline: str, bullets: list[str],
              brand: dict, w: int, h: int) -> None:
    ken_burns_stock(stock, duration, out, headline, bullets, brand, w, h, dramatic=True)


def logo_outro(
    stock: Path, logo: Path, duration: float, out: Path,
    headline: str, bullets: list[str], brand: dict, w: int, h: int,
) -> None:
    h_esc = esc(headline)
    accent = brand["colors"]["accent"]
    muted = brand["colors"]["text_muted"]
    tagline = esc(brand.get("tagline", ""))
    bullet_fc = ""
    for i, b in enumerate(bullets[:3]):
        bt = esc(b)
        bullet_fc += (
            f",drawtext=fontfile={font_path(brand, 'body')}:text='{bt}':fontsize=30:fontcolor={accent}:"
            f"x=(w-text_w)/2:y={int(h * 0.63) + i * 40}"
        )
    tagline_fc = ""
    if tagline:
        tagline_fc = (
            f",drawtext=fontfile={font_path(brand, 'body')}:text='{tagline}':fontsize=28:fontcolor={muted}:"
            f"x=(w-text_w)/2:y={int(h * 0.78)}"
        )
    logo_scale = 420 if h > w else 520
    if logo.exists():
        fc = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},eq=brightness=-0.25[bg];"
            f"[1:v]format=rgba,scale={logo_scale}:-1[lg];"
            f"[bg][lg]overlay=(W-w)/2:{int(h * 0.18)}[tmp];"
            f"[tmp]drawtext=fontfile={font_path(brand)}:text='{h_esc}':fontsize=52:fontcolor=white:"
            f"x=(w-text_w)/2:y={int(h * 0.54)}{bullet_fc}{tagline_fc}[v]"
        )
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(stock),
            "-loop", "1", "-i", str(logo),
            "-filter_complex", fc, "-map", "[v]", "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out),
        ])
    else:
        ken_burns_stock(stock, duration, out, headline, bullets, brand, w, h)


def mux_av(video: Path, audio: Path, out: Path) -> None:
    run(["ffmpeg", "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])


def resolve_product_image(slug: str, scene: dict) -> Path:
    base = project_dir(slug)
    src = scene.get("visual", {}).get("source_path", "")
    if src:
        p = base / src
        if p.exists():
            return p
    sid = scene["id"]
    for candidate in (
        base / "assets" / "images" / f"{sid}.png",
        base / "assets" / "images" / "hero.png",
    ):
        if candidate.exists():
            return candidate
    return base / "assets" / "images" / "hero.png"


def render_scene(slug: str, scene: dict, logo: Path, seg_dir: Path,
                 brand: dict, w: int, h: int) -> Path:
    sid = scene["id"]
    vo = project_dir(slug) / "assets" / "vo" / f"{sid}.mp3"
    dur = probe_duration(vo) + 0.4
    stock = stock_path(slug, sid)
    if not stock:
        raise FileNotFoundError(f"No stock for {sid} — run: python run.py generate-assets --project {slug}")

    silent = seg_dir / f"{sid}_v.mp4"
    vtype = scene.get("visual", {}).get("type", "stock_video")
    headline = scene.get("on_screen_text", "")
    bullets = scene.get("bullets", [])
    dramatic = scene.get("dramatic", sid in ("s01", "s02"))

    if vtype == "logo_slate":
        logo_outro(stock, logo, dur, silent, headline, bullets, brand, w, h)
    elif vtype in ("product_image", "ai_image"):
        prod = resolve_product_image(slug, scene)
        product_composite(stock, prod, dur, silent, headline, brand, w, h)
    elif vtype == "text_card":
        text_card(stock, dur, silent, headline, bullets, brand, w, h)
    elif vtype == "screen_recording":
        clip = project_dir(slug) / scene.get("visual", {}).get("source_path", "")
        if clip.exists() and clip.suffix == ".mp4":
            run([
                "ffmpeg", "-y", "-i", str(clip),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
                "-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(silent),
            ])
        else:
            product_composite(stock, resolve_product_image(slug, scene), dur, silent, headline, brand, w, h)
    else:
        ken_burns_stock(stock, dur, silent, headline, bullets, brand, w, h, dramatic=dramatic)

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


def optional_research(slug: str) -> None:
    """Run transcript research only when brief has YouTube reference URLs."""
    shot_list = load_shot_list(slug)
    urls = []
    ref = shot_list.get("style_reference", "")
    if ref and "youtube" in ref:
        urls.append(ref)
    urls.extend(u for u in parse_brief_urls(project_dir(slug) / "brief.md") if "youtube" in u.lower())
    urls = list(dict.fromkeys(urls))
    if not urls:
        return
    print("  Research (YouTube refs from brief)")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "research.py"), "--project", slug, "--urls", *urls],
        check=False,
    )


def render_free(slug: str, force: bool = False, skip_assets: bool = False) -> Path:
    if is_paid_mode(slug):
        print("Paid mode — use voiceover + veed scripts")
        sys.exit(1)

    cfg = load_production_config(slug)
    voice = cfg.get("free", {}).get("voice", "en-US-ChristopherNeural")
    shot_list = load_shot_list(slug)
    brand = load_brand(slug)
    w, h = aspect_dimensions(shot_list.get("aspect_ratio", "16:9"))
    base = ensure_project_dirs(slug)
    logo = resolve_logo_path(slug, brand)

    print(f"=== Render (free) — {shot_list.get('video_type', 'custom')} {w}x{h} ===")

    if not skip_assets:
        print("1. Assets")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_assets.py"), "--project", slug],
            check=False,
        )
        optional_research(slug)

    print("2. Voiceover")
    generate_vo(slug, voice, force=force)

    seg_dir = base / "renders" / "segments"
    if force and seg_dir.exists():
        import shutil
        shutil.rmtree(seg_dir)
    seg_dir.mkdir(parents=True, exist_ok=True)

    print("3. Scene composites")
    segments = []
    for scene in shot_list["scenes"]:
        print(f"  {scene['id']}")
        segments.append(render_scene(slug, scene, logo, seg_dir, brand, w, h))

    music = base / "assets" / "music" / "background.mp3"
    final = base / "renders" / "final.mp4"
    print("4. Concat + music")
    concat_with_music(segments, music, final)

    save_json(base / "assets" / "manifest.json", {
        "updated_at": utc_now_iso(),
        "production_mode": "free",
        "renderer": "render_free.py",
        "video_type": shot_list.get("video_type"),
        "aspect_ratio": shot_list.get("aspect_ratio"),
        "brand": brand.get("name"),
        "stock": True,
        "music": music.exists(),
    })
    print(f"\nDone: {final} ({probe_duration(final):.0f}s)")
    return final


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--force", action="store_true", help="Regenerate VO and segments")
    p.add_argument("--skip-assets", action="store_true", help="Skip generate-assets step")
    args = p.parse_args()
    render_free(args.project, force=args.force, skip_assets=args.skip_assets)


if __name__ == "__main__":
    main()
