from __future__ import annotations

import sys
from pathlib import Path

import pyte
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def parse_screen(transcript_path: Path) -> list[str]:
    data = transcript_path.read_text(encoding="utf-8", errors="ignore")
    screen = pyte.Screen(140, 50)
    stream = pyte.Stream(screen)
    last_nonempty: list[str] = []
    for chunk in data.splitlines(keepends=True):
        stream.feed(chunk)
        rows = [row.rstrip() for row in screen.display]
        while rows and not rows[-1]:
            rows.pop()
        if rows:
            last_nonempty = rows
    return last_nonempty


def render(rows: list[str], output_path: Path) -> None:
    if not rows:
        rows = ["<blank screen>"]
    font = load_font(20)
    sample = max(rows, key=len)
    left_pad = 24
    top_pad = 24
    line_gap = 8
    bg = "#111318"
    fg = "#e8edf3"
    accent = "#7dd3fc"

    dummy = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), sample or " ", font=font)
    line_height = bbox[3] - bbox[1] + line_gap
    width = max(draw.textbbox((0, 0), line or " ", font=font)[2] for line in rows)
    image = Image.new(
        "RGB",
        (width + left_pad * 2, top_pad * 2 + line_height * len(rows) + 16),
        bg,
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (8, 8, image.width - 8, image.height - 8), 16, outline=accent
    )
    y = top_pad
    for line in rows:
        draw.text((left_pad, y), line or " ", font=font, fill=fg)
        y += line_height
    image.save(output_path)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: render_terminal_snapshot.py INPUT.typescript OUTPUT.png"
        )
    transcript_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    rows = parse_screen(transcript_path)
    render(rows, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
