"""Sovrappone il profilo del modello al disegno tecnico (controllo visivo)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import watch_body as wb

PX_PER_MM = 625 / 49.9      # barra di quota del disegno: x 201..826
CX, TOP_Y = 513.5, 307      # asse e faccia superiore nel disegno


def profile_edges(n=60):
    wire = wb.half_profile().wire().val()
    return [[(e.positionAt(i / n).x, e.positionAt(i / n).z) for i in range(n + 1)] for e in wire.Edges()]


def main(drawing, out):
    im = Image.open(drawing)
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
    ax.imshow(im)
    for pts in profile_edges():
        for sign in (1, -1):
            xs = [CX + sign * r * PX_PER_MM for r, z in pts]
            ys = [TOP_Y + (wb.TOTAL_HEIGHT - z) / wb._K * PX_PER_MM for r, z in pts]
            ax.plot(xs, ys, color="lime", lw=1)
    ax.set_xlim(150, 880)
    ax.set_ylim(530, 280)
    ax.axis("off")
    fig.savefig(out, bbox_inches="tight")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
