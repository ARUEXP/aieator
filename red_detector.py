import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    from PIL import Image
except ImportError:
    print("PIL missing"); sys.exit(1)

def red_clusters(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    hits = []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if r > 170 and g < 130 and b < 130:
                hits.append((x, y))
    print(f"{os.path.basename(path)}: {w}x{h}, red pixels(sampled): {len(hits)}")
    for (x, y) in hits[:20]:
        print(f"   red at ({x},{y})")
    return len(hits)

total = 0
for f in os.listdir("screenshots"):
    total += red_clusters(os.path.join("screenshots", f))
print("TOTAL red hits:", total)
