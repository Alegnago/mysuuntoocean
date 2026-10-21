"""Ricava dal disegno la forma delle anse.

Pianta: l'ansa è la zona chiusa tra il suo contorno e il cerchio della cassa
(riempita da un punto interno, allargata di mezzo tratto). Si ricalca l'ansa in
basso a sinistra; le altre tre sono speculari (il disegno lo è entro 1 px).

Vista frontale (lato tasti): la gamba è una barra dritta tra il bordo interno e il
bordo esterno del disegno (rette ricalcate sui tratti), che parte dalla giunzione
con la lunetta e scende verso l'esterno fino al piede. La sagoma è la gamba più la
parte sotto la gamba fino alla linea di fondo; il triangolo in alto e il bordo
esterno sopra la piega sono il fianco della cassa, non l'ansa. La parte sotto la
gamba non è separata dal fianco della cassa da nessuna linea: si taglia a
FRONT_CUT_X, che sta già dentro la cassa.

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
SEAM_Y = 355.98                                 # px: giunzione lunetta/cassa, dove parte la gamba
INNER_EDGE_ROWS = range(415, 466)               # bordo interno della gamba (secondo tratto in [180, 300])
OUTER_EDGE_ROWS = range(428, 466)               # bordo esterno sotto la piega (primo tratto in [180, 300])
TIP_Y = 473                                     # px: sotto, il bordo esterno gira nel piede arrotondato


def load():
    return 255.0 - np.asarray(Image.open(ROOT / "reference" / P["source"]).convert("L"), dtype=float)


def _runs(v, thr=60):
    idx = np.where(v > thr)[0]
    if len(idx) == 0:
        return []
    splits = np.where(np.diff(idx) > 1)[0]
    return list(zip(np.r_[idx[0], idx[splits + 1]], np.r_[idx[splits], idx[-1]]))


def _edge_line(g, rows, pick):
    """Retta x = a*y + b sui centri del tratto scelto (pick: indice del tratto da sinistra) in [180, 300]."""
    ys, xs = [], []
    for y in rows:
        row = g[y, 180:300]
        runs = _runs(row)
        if not runs:
            continue
        a, b = runs[pick]
        w = row[a:b + 1]
        xs.append(180 + a + (w * np.arange(len(w))).sum() / w.sum())
        ys.append(y)
    return np.polyfit(ys, xs, 1)


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
    inner = _edge_line(g, INNER_EDGE_ROWS, 1)
    outer = _edge_line(g, OUTER_EDGE_ROWS, 0)
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    x_out, x_in = np.polyval(outer, yy), np.polyval(inner, yy)
    m &= ~((xx < x_out) & (yy < TIP_Y))                   # fuori dal bordo esterno: fianco cassa
    # gamba fino alla giunzione; le rette sono già alla mezzeria del tratto, il contorno
    # verrà allargato di mezzo tratto: si parte ristretti della stessa quantità
    h = STROKE_HALF
    m |= (xx >= x_out + h) & (xx <= x_in - h) & (yy >= SEAM_Y + h) & (yy <= TIP_Y)
    m = ndi.binary_closing(m, iterations=4)              # assorbe i tratti tra le zone
    m = ndi.binary_fill_holes(m)
    lab, _ = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, lab.max() + 1))
    m = lab == (1 + int(np.argmax(sizes)))
    line = simplify(outline(m, STROKE_HALF), 0.15)
    front = [[round((x - P["axis_px"]) / S, 4), round((P["zero_px"] - y) / S, 4)] for x, y in line]

    data = {"plan": plan, "front": front,
            "inner_edge_px": inner.tolist(), "outer_edge_px": outer.tolist()}
    OUT.write_text(json.dumps(data, indent=1))
    xs, ys = [p[0] for p in plan], [p[1] for p in plan]
    print(f"pianta: {len(plan)} punti, X {min(xs):.2f}..{max(xs):.2f}, Y {min(ys):.2f}..{max(ys):.2f}"
          f" (area sx {left_area} px, dx {right_area} px)")
    xs, zs = [p[0] for p in front], [p[1] for p in front]
    print(f"frontale: {len(front)} punti, X {min(xs):.2f}..{max(xs):.2f}, Z {min(zs):.2f}..{max(zs):.2f}")


if __name__ == "__main__":
    main()
