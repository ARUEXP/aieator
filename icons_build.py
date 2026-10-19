"""Build-time icon pipeline: Iconoir SVGs in icons/ -> white RGBA baked into gen.py.

Why build-time: the exe stays a single file with zero runtime deps (no SVG
parser, no sidecar PNGs) — matters on the i3-4005U/4GB floor. icons/ is the
source of truth; rerun this script after swapping any icon, then rebuild.

Usage: python icons_build.py && python gen.py && <compile>
"""
import math
import os
import re
import subprocess
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# App icon enum -> Iconoir file (regular = stroke style, solid = filled style)
MAP = [
    ("ICON_PLAY", "icons/solid/play.svg"),
    ("ICON_PAUSE", "icons/solid/pause.svg"),
    ("ICON_REWIND", "icons/regular/rewind.svg"),
    ("ICON_FORWARD", "icons/regular/forward.svg"),
    ("ICON_SKIP_PREV", "icons/regular/skip-prev.svg"),
    ("ICON_SKIP_NEXT", "icons/regular/skip-next.svg"),
    ("ICON_UNDO", "icons/regular/undo.svg"),
    ("ICON_REDO", "icons/regular/redo.svg"),
    ("ICON_CUT", "icons/regular/cut.svg"),
    ("ICON_BIN", "icons/regular/trash.svg"),
    ("ICON_GRID", "icons/regular/view-grid.svg"),
    ("ICON_MAGNET", "icons/regular/magnet.svg"),
    ("ICON_EXPAND", "icons/regular/expand.svg"),
    ("ICON_COLLAPSE", "icons/regular/collapse.svg"),
    ("ICON_KEYFRAME", "icons/regular/keyframe.svg"),
    ("ICON_TEXT", "icons/regular/text.svg"),
    ("ICON_MEDIA", "icons/regular/media-image.svg"),
    ("ICON_COLOR", "icons/regular/color-filter.svg"),
    ("ICON_FX", "icons/regular/magic-wand.svg"),
    ("ICON_EASE", "icons/regular/ease-curve-control-points.svg"),
    ("ICON_FOLDER", "icons/regular/folder.svg"),
    ("ICON_PLUS", "icons/regular/plus.svg"),
    ("ICON_XMARK", "icons/regular/x.svg"),
    ("ICON_CHEVRON_DOWN", "icons/regular/nav-arrow-down.svg"),
    ("ICON_CHECK", "icons/regular/check.svg"),
    ("ICON_KEYFRAME_FILL", "icons/solid/keyframe.svg"),
]

CELL = 128   # grid cell in the raster page
RENDER = 112  # icon px (downscaled 4x to 28 for AA)
OUT = 28
COLS = 5

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def load_svg(path):
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    # Iconoir paints with currentColor (stroke and/or fill) -> force white
    svg = svg.replace("currentColor", "#ffffff")
    # fixed render size; viewBox preserved for aspect
    svg = re.sub(r'width="[^"]*"', f'width="{RENDER}"', svg, count=1)
    svg = re.sub(r'height="[^"]*"', f'height="{RENDER}"', svg, count=1)
    return svg


def main():
    from PIL import Image

    for _, path in MAP:
        if not os.path.exists(path):
            sys.exit(f"missing icon file: {path}")
    if not os.path.exists(CHROME):
        sys.exit(f"chrome not found: {CHROME}")

    rows = math.ceil(len(MAP) / COLS)
    cells = []
    for _, path in MAP:
        cells.append(f'<div class="c">{load_svg(path)}</div>')
    html = (
        "<html><head><style>"
        "html,body{margin:0;padding:0;background:transparent;}"
        f".g{{display:grid;grid-template-columns:repeat({COLS},{CELL}px);width:{COLS * CELL}px;}}"
        f".c{{width:{CELL}px;height:{CELL}px;display:flex;align-items:center;justify-content:center;}}"
        "</style></head><body><div class=\"g\">"
        + "".join(cells)
        + "</div></body></html>"
    )
    page = os.path.abspath("_icons_page.html")
    shot = os.path.abspath("_icons_shot.png")
    with open(page, "w", encoding="utf-8") as f:
        f.write(html)

    W, H = COLS * CELL, rows * CELL
    cmd = [
        CHROME, "--headless=new", "--disable-gpu",
        f"--screenshot={shot}", f"--window-size={W},{H}",
        "--default-background-color=00000000", "--hide-scrollbars",
        "file:///" + page.replace("\\", "/"),
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)
    if not os.path.exists(shot):
        sys.exit("chrome screenshot failed")
    sheet = Image.open(shot).convert("RGBA")

    arrays = {}
    for idx, (name, _) in enumerate(MAP):
        cx, cy = (idx % COLS) * CELL, (idx // COLS) * CELL
        pad = (CELL - RENDER) // 2
        icon = sheet.crop((cx + pad, cy + pad, cx + pad + RENDER, cy + pad + RENDER))
        icon = icon.resize((OUT, OUT), Image.LANCZOS)
        # force white RGB (source is white), keep raster alpha for tinting
        r, g, b, a = icon.split()
        white = Image.new("L", icon.size, 255)
        icon = Image.merge("RGBA", (white, white, white, a))
        raw = icon.tobytes()  # RGBA, 28*28*4 = 3136
        assert len(raw) == OUT * OUT * 4, name
        if a.getextrema() == (0, 0):
            print(f"warning: {name} rasterized empty")
        arrays[name] = ", ".join(f"0x{b:02x}" for b in raw)

    with open("gen.py", encoding="utf-8") as f:
        gen = f.read()
    patched = 0
    for name, body in arrays.items():
        new_line = f"static const unsigned char raw_{name}[{OUT * OUT * 4}] = {{{body}}};"
        gen, n = re.subn(
            r"static const unsigned char raw_" + name + r"\[\d+\] = \{[^}]*\};",
            lambda m: new_line, gen, count=1)
        patched += n
    if patched != len(MAP):
        sys.exit(f"patched {patched}/{len(MAP)} icons, aborting")
    with open("gen.py", "w", encoding="utf-8") as f:
        f.write(gen)

    for tmp in (page, shot):
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(f"baked {patched} icons from icons/ into gen.py")


if __name__ == "__main__":
    main()
