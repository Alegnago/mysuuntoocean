"""Ricava dal disegno le forme della piattaforma dei tasti e dei tasti.

Pianta (vista dall'alto): ogni zona chiusa del disegno (lobo della piattaforma,
tasto laterale, tasto centrale) viene riempita a partire da un punto interno; il
riempimento allargato di mezzo tratto dà il contorno alla mezzeria della linea.
Le dentellature dei tasti restano come tacche nel contorno.

Vista frontale (laterale del disegno, lato ore 6): la sagoma chiusa di ogni
tasto viene riempita e ristretta di mezzo tratto.

Coordinate in mm, sistema del modello: X a destra, Y verso ore 12 (le ore 6 sono
-Y, il lato che guarda la vista frontale), Z in alto con z = 0 sul fondo.

Scrive data/buttons_mm.json.

Uso:  python tools/trace_buttons.py
"""
import json
from pathlib import Path

import contourpy
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "data" / "profile_mm.json").read_text())
S = P["px_per_mm"]
OUT = ROOT / "data" / "buttons_mm.json"

STROKE_HALF = 2.2                     # px, come in trace_profile
PLAN_CENTER_ROW, PLAN_CENTER_COL = 940, 513

# punti interni (r [mm], angolo dalle ore 6 [gradi], negativo = verso sinistra)
PLAN_SEEDS = {
    "platform": (25.8, -31.0),
    "side_button": (27.1, -30.0),
    "center_button": (25.65, 0.0),
}
# finestre della vista frontale che contengono solo la sagoma del tasto (x0, y0, x1, y1)
FRONT_BOXES = {
    "side_button": (302, 368, 428, 419),
    "center_button": (450, 368, 578, 419),
}
PLATFORM_COL = 350                    # colonna della vista frontale dove leggere le quote della piattaforma


def load():
    return 255.0 - np.asarray(Image.open(ROOT / "reference" / P["source"]).convert("L"), dtype=float)


def stroke_center(v, lo, hi):
    w = v[lo:hi + 1]
    return lo + (w * np.arange(len(w))).sum() / w.sum()


def plan_center(ink):
    row, col = ink[PLAN_CENTER_ROW], ink[:, PLAN_CENTER_COL]
    cx = (stroke_center(row, 279, 287) + stroke_center(row, 739, 747)) / 2
    cy = (stroke_center(col, 704, 712) + stroke_center(col, 1163, 1171)) / 2
    return cx, cy


def outline(mask, grow_px):
    """Contorno sub-pixel della maschera allargata (grow > 0) o ristretta (grow < 0)."""
    inside = ndi.distance_transform_edt(mask) if grow_px < 0 else None
    if grow_px >= 0:
        field = ndi.distance_transform_edt(~mask)          # distanza dall'esterno
        level_mask = field <= grow_px
    else:
        level_mask = inside > -grow_px
    smooth = ndi.gaussian_filter(level_mask.astype(float), 0.8)
    lines = contourpy.contour_generator(z=smooth).lines(0.5)
    line = max(lines, key=len)                             # contorno esterno
    return line                                            # colonne (x), righe (y)


def simplify(pts, tol):
    """Douglas-Peucker su un poligono chiuso."""
    pts = np.asarray(pts)

    def dp(a):
        if len(a) < 3:
            return a
        s, e = a[0], a[-1]
        v, w = e - s, a - s
        d = np.abs(v[0] * w[:, 1] - v[1] * w[:, 0]) / (np.linalg.norm(v) + 1e-12)
        i = int(np.argmax(d))
        if d[i] > tol:
            return np.vstack([dp(a[:i + 1])[:-1], dp(a[i:])])
        return np.array([s, e])

    far = int(np.argmax(np.linalg.norm(pts - pts[0], axis=1)))
    out = np.vstack([dp(pts[:far + 1])[:-1], dp(np.vstack([pts[far:], pts[:1]]))[:-1]])
    return out


def region(ink_mask, labels, seed):
    return labels == labels[seed]


def main():
    g = load()
    ink = g > 128
    labels, _ = ndi.label(~ink)
    cx, cy = plan_center(g)

    plan = {}
    for name, (r_mm, ang) in PLAN_SEEDS.items():
        a = np.radians(ang)
        seed = (int(round(cy + r_mm * S * np.cos(a))), int(round(cx + r_mm * S * np.sin(a))))
        m = region(ink, labels, seed)
        line = outline(m, STROKE_HALF)
        line = simplify(line, 0.15)
        plan[name] = [[round((x - cx) / S, 4), round(-(y - cy) / S, 4)] for x, y in line]

    front = {}
    for name, (x0, y0, x1, y1) in FRONT_BOXES.items():
        crop = ink[y0:y1, x0:x1]
        filled = ndi.binary_fill_holes(crop)
        lab, _ = ndi.label(filled)
        sizes = ndi.sum(filled, lab, range(1, lab.max() + 1))
        m = lab == (1 + int(np.argmax(sizes)))
        line = outline(m, -STROKE_HALF)
        line = simplify(line, 0.15)
        front[name] = [[round((x0 + x - P["axis_px"]) / S, 4), round((P["zero_px"] - (y0 + y)) / S, 4)]
                       for x, y in line]

    # piattaforma in vista frontale: faccia superiore (linea sotto la giunzione
    # lunetta/cassa) e fondo
    col = g[:, PLATFORM_COL]
    top_y = stroke_center(col, 359, 367)
    bottom_y = stroke_center(col, 423, 432)
    seam_y = stroke_center(col, 352, 359)

    data = {
        "plan_center_px": [cx, cy],
        "plan": plan,
        "front": front,
        "platform_top_z": (P["zero_px"] - top_y) / S,
        "platform_bottom_z": (P["zero_px"] - bottom_y) / S,
        "seam_z": (P["zero_px"] - seam_y) / S,
    }
    OUT.write_text(json.dumps(data, indent=1))
    for k, v in plan.items():
        print(f"pianta {k}: {len(v)} punti")
    for k, v in front.items():
        zs = [p[1] for p in v]
        print(f"frontale {k}: {len(v)} punti, z {min(zs):.2f}..{max(zs):.2f}")
    print(f"piattaforma: z {data['platform_bottom_z']:.3f}..{data['platform_top_z']:.3f}, giunzione {data['seam_z']:.3f}")


if __name__ == "__main__":
    main()
