"""
Image optimization utilities.

Every raster image that ends up in the served `static/{package}/{tag}/` tree is
re-encoded to WebP at build time so the documentation site stays fast and
snappy. Vector formats (SVG) are passed through untouched — they are already
compact and scale crisply at any DPI.

This module is the single choke point for that policy. The notebook figure
collector, the notebook executor and the docstring figure collector all route
their image writes through `optimize_image` / `encode_bytes`, so the WebP rule
is enforced in exactly one place.
"""

from __future__ import annotations

import shutil
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:  # pragma: no cover - Pillow is a hard build dependency
    HAS_PIL = False

from .config import (
    RASTER_EXTENSIONS,
    VECTOR_EXTENSIONS,
    WEBP_LOSSLESS_EXTENSIONS,
    WEBP_METHOD,
    WEBP_QUALITY,
)


def is_vector(path: Path | str) -> bool:
    """Whether a path is a vector image we pass through verbatim."""
    return Path(path).suffix.lower() in VECTOR_EXTENSIONS


def is_raster(path: Path | str) -> bool:
    """Whether a path is a raster image we re-encode to WebP."""
    return Path(path).suffix.lower() in RASTER_EXTENSIONS


def _encode_params(source_suffix: str) -> dict:
    """WebP save parameters for a given source extension."""
    suffix = source_suffix.lower()
    if suffix in WEBP_LOSSLESS_EXTENSIONS:
        # Flat-color diagrams / screenshots: lossless avoids text fringing and
        # is usually smaller than a lossy encode of sharp edges anyway.
        return {"lossless": True, "method": WEBP_METHOD}
    return {"quality": WEBP_QUALITY, "method": WEBP_METHOD}


def optimize_image(src: Path, dest_dir: Path, name: str | None = None) -> str:
    """
    Place `src` into `dest_dir`, re-encoding raster images to WebP.

    Args:
        src: Source image file.
        dest_dir: Target directory (created if missing).
        name: Optional output stem (without extension). Defaults to src stem.

    Returns the final filename as written into dest_dir (caller rewrites refs to
    point at it). Raster -> "<stem>.webp"; vector/other -> original extension.
    """
    src = Path(src)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    stem = name if name is not None else src.stem
    suffix = src.suffix.lower()

    # Vector or unknown: copy verbatim.
    if is_vector(src) or not is_raster(src):
        out_name = f"{stem}{src.suffix}"
        dest = dest_dir / out_name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return out_name

    # Raster: re-encode to WebP.
    out_name = f"{stem}.webp"
    dest = dest_dir / out_name
    try:
        _encode_file_to_webp(src, dest, suffix)
        return out_name
    except Exception as e:
        # Never let an image hiccup break the whole build — fall back to a
        # verbatim copy of the original so the figure still shows.
        print(f"      Warning: WebP encode failed for {src.name} ({e}); copying original")
        fallback = f"{stem}{src.suffix}"
        shutil.copy2(src, dest_dir / fallback)
        return fallback


def _encode_file_to_webp(src: Path, dest: Path, source_suffix: str) -> None:
    """Encode a raster file on disk to WebP at `dest`."""
    if not HAS_PIL:
        raise RuntimeError("Pillow not installed")

    with Image.open(src) as img:
        _save_webp(img, dest, source_suffix)


def encode_bytes(data: bytes, dest_dir: Path, stem: str, source_ext: str) -> str:
    """
    Re-encode raw image bytes (e.g. a base64-decoded notebook output) to WebP.

    Args:
        data: Raw image bytes.
        dest_dir: Target directory.
        stem: Output filename stem.
        source_ext: Original extension incl. dot (".png", ".jpg", ...), used to
            pick lossless vs lossy.

    Returns the written filename. Falls back to writing the original bytes with
    the source extension if encoding fails.
    """
    import io

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{stem}.webp"
    dest = dest_dir / out_name
    try:
        if not HAS_PIL:
            raise RuntimeError("Pillow not installed")
        with Image.open(io.BytesIO(data)) as img:
            _save_webp(img, dest, source_ext)
        return out_name
    except Exception as e:
        print(f"      Warning: WebP encode failed for {stem}{source_ext} ({e}); writing original")
        fallback = f"{stem}{source_ext}"
        (dest_dir / fallback).write_bytes(data)
        return fallback


def _save_webp(img: "Image.Image", dest: Path, source_suffix: str) -> None:
    """Save a PIL image to WebP, preserving alpha and GIF animation."""
    params = _encode_params(source_suffix)

    # Animated GIF -> animated WebP.
    if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
        img.save(dest, format="WEBP", save_all=True, **params)
        return

    # Preserve alpha; flatten exotic modes (P, CMYK) into something WebP takes.
    if img.mode in ("RGBA", "LA"):
        out = img.convert("RGBA")
    elif img.mode == "P" and "transparency" in img.info:
        out = img.convert("RGBA")
    elif img.mode in ("RGB", "L"):
        out = img
    else:
        out = img.convert("RGB")

    out.save(dest, format="WEBP", **params)
