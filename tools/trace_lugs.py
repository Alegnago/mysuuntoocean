"""Ricava dal disegno la forma delle anse.

Pianta: l'ansa è la zona chiusa tra il suo contorno e il cerchio della cassa
(riempita da un punto interno, allargata di mezzo tratto). Si ricalca l'ansa in
basso a sinistra; le altre tre sono speculari (il disegno lo è entro 1 px).

Vista frontale (lato tasti): la sagoma dell'ansa è l'unione delle zone chiuse
della gamba (faccia della gamba, triangolo in alto, parte sotto la gamba). La
parte sotto la gamba non è separata dal fianco della cassa da nessuna linea:
si taglia a FRONT_CUT_X, che sta già dentro la cassa.

Coordinate in mm come in trace_buttons.py: X a destra, Y verso l'alto della pianta
(il lato tasti è -Y), Z in alto, z = 0 sul fondo.

Scrive data/lugs_mm.json.

Uso:  python tools/trace_lugs.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from trace_buttons import STROKE_HALF, outline, plan_center, simplify

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "data" / "profile_mm.json").read_text())
S = P["px_per_mm"]
OUT = ROOT / "data" / "lugs_mm.json"

PLAN_SEED = (1110, 215)                         # (riga, colonna) dentro l'ansa in basso a sinistra
PLAN_SEED_CHECK = (1110, 811)                   # la sua speculare a destra, per il controllo
FRONT_SEEDS = [(450, 230), (400, 216), (470, 275)]   # gamba, triangolo in alto, parte sotto
FRONT_CUT_X = 330                               # px: oltre, la zona sotto la gamba è fianco cassa
FRONT_TOP_Y = 389                               # px: sopra la linea y≈391 c'è la cassa


def load():
    return 255.0 - np.asarray(Image.open(ROOT / "reference" / P["source"]).convert("L"), dtype=float)


def main():
    g = load()
    ink = g > 128
    labels, _ = ndi.label(~ink)
    cx, cy = plan_center(g)

    # pianta
    m = labels == labels[PLAN_SEED]
    assert m.sum() < 20000, "il riempimento dell'ansa è uscito dal contorno"
    line = simplify(outline(m, STROKE_HALF), 0.15)
    plan = [[round((x - cx) / S, 4), round(-(y - cy) / S, 4)] for x, y in line]
    check = labels == labels[PLAN_SEED_CHECK]
    left_area, right_area = m.sum(), check.sum()

    # vista frontale: unione delle zone, chiusura dei tratti interni
    m = np.zeros_like(ink)
    for seed in FRONT_SEEDS:
        m |= labels == labels[seed]
    m[:, FRONT_CUT_X:] = False
    m[:FRONT_TOP_Y, :] = False
    m = ndi.binary_closing(m, iterations=4)              # assorbe i tratti tra le zone
    m = ndi.binary_fill_holes(m)
    lab, _ = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, lab.max() + 1))
    m = lab == (1 + int(np.argmax(sizes)))
    line = simplify(outline(m, STROKE_HALF), 0.15)
    front = [[round((x - P["axis_px"]) / S, 4), round((P["zero_px"] - y) / S, 4)] for x, y in line]

    data = {"plan": plan, "front": front}
    OUT.write_text(json.dumps(data, indent=1))
    xs, ys = [p[0] for p in plan], [p[1] for p in plan]
    print(f"pianta: {len(plan)} punti, X {min(xs):.2f}..{max(xs):.2f}, Y {min(ys):.2f}..{max(ys):.2f}"
          f" (area sx {left_area} px, dx {right_area} px)")
    xs, zs = [p[0] for p in front], [p[1] for p in front]
    print(f"frontale: {len(front)} punti, X {min(xs):.2f}..{max(xs):.2f}, Z {min(zs):.2f}..{max(zs):.2f}")


if __name__ == "__main__":
    main()
