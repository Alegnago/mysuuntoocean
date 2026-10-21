"""Sovrappone il profilo del modello al disegno tecnico e misura lo scarto.

Lo scarto è la distanza (in px del disegno) tra i centri dei tratti misurati da
trace_profile.py e il profilo effettivo del modello.

Uso:  python tools/overlay.py [out.png] [zoom.png]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import watch_body as wb

P = wb.PROFILE
S, CX = P["px_per_mm"], P["axis_px"]
Y0 = None  # riga del disegno che corrisponde a z = 0


def to_px(r, z, sign=1):
    return CX + sign * r * S, Y0 - z * S


def profile_edges(n=200):
    wire = wb.half_profile().wire().val()
    return [np.array([(e.positionAt(i / n).x, e.positionAt(i / n).z) for i in range(n + 1)]) for e in wire.Edges()]


def deviation(edges):
    model = np.vstack(edges)
    raw = np.vstack([P["raw"][k] for k in ("upper", "flank", "dome")])
    d = np.sqrt(((raw[:, None, :] - model[None, :, :]) ** 2).sum(-1)).min(1)
    return d * S


def draw(ax, im, edges, xlim, ylim, lw):
    ax.imshow(im)
    for pts in edges:
        for sign in (1, -1):
            xs, ys = to_px(pts[:, 0], pts[:, 1], sign)
            ax.plot(xs, ys, color="lime", lw=lw)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")


def main(out, zoom_out):
    global Y0
    im = Image.open(ROOT / "reference" / P["source"])
    Y0 = 0
    # z = 0 sta height_mm sotto il centro del tratto superiore
    y_top = None
    g = 255 - np.asarray(im.convert("L"), dtype=float)
    col = g[300:315, 600]
    y_top = 300 + (col * np.arange(len(col))).sum() / col.sum()
    Y0 = y_top + P["top_z"] * S

    edges = profile_edges()
    d = deviation(edges)
    print(f"scarto modello-disegno: medio {d.mean():.2f} px, max {d.max():.2f} px ({d.max() / S:.3f} mm)")

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
    draw(ax, im, edges, (150, 880), (530, 280), 0.8)
    fig.savefig(out, bbox_inches="tight")

    fig, axs = plt.subplots(1, 2, figsize=(12, 7), dpi=150)
    draw(axs[0], im, edges, (690, 850), (510, 295), 0.8)
    axs[0].set_title("fianco destro")
    draw(axs[1], im, edges, (330, 530), (510, 455), 0.8)
    axs[1].set_title("fondello")
    fig.savefig(zoom_out, bbox_inches="tight")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "overlay.png",
         sys.argv[2] if len(sys.argv) > 2 else ROOT / "docs" / "overlay_zoom.png")
