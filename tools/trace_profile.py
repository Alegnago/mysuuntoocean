"""Ricava la mezza sezione della cassa direttamente dal disegno tecnico.

Ogni tratto del disegno è largo ~4.4 px: lo spigolo reale è la mezzeria del
tratto, quindi qui si misurano sempre i centri dei tratti (media pesata
sull'intensità), mai i bordi. La vista laterale viene letta su entrambi i lati
e mediata (il disegno è simmetrico entro 0.1 px).

Scrive data/profile_mm.json con i punti in mm:
r = distanza dall'asse, z = altezza dal punto più basso del fondello.

Uso:  python tools/trace_profile.py [reference/suunto_ocean_drawing.png]
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.interpolate import splev, splprep

ROOT = Path(__file__).resolve().parents[1]
DRAWING = ROOT / "reference" / "suunto_ocean_drawing.png"
OUT = ROOT / "data" / "profile_mm.json"

DIAMETER_MM = 49.9          # quota della barra sopra la vista laterale
STROKE_HALF = 2.2           # mezza larghezza del tratto [px] (misurata sul bordo superiore)

# Righe/colonne dell'immagine (px) dove leggere ogni tratto.
BAR_ROW = 235               # barra di quota
TOP_COLS = range(300, 701, 50)
CORNER_COLS = range(805, 811)        # raccordo superiore, letto per colonne
SIDE_ROWS = [*range(312, 352), *range(360, 388), *range(394, 401)]  # 352-359 e 388-393: linee di giunzione
FLANK_ROWS = range(400, 413)         # tratto rettilineo visibile sotto le anse
BACK_LINE_COL = 450                  # dove leggere le due linee orizzontali del fondo
DOME_ROWS = range(476, 491)          # fondello, parte ripida (per righe)
DOME_MAX_R_COLS = 135                # fondello, parte piatta (per colonne) fino a questo raggio [px]
SENSOR_R_PX = 21                     # gradino del sensore (vedi bordo inferiore a r≈20 px)


def load(path):
    return 255.0 - np.asarray(Image.open(path).convert("L"), dtype=float)


def centroid(v, lo, hi):
    w = v[lo:hi + 1]
    return lo + (w * np.arange(len(w))).sum() / w.sum()


def stroke_runs(v, thr=60):
    idx = np.where(v > thr)[0]
    if len(idx) == 0:
        return []
    splits = np.where(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[splits + 1]]
    ends = np.r_[idx[splits], idx[-1]]
    return list(zip(starts, ends))


def bar_scale(ink):
    row = ink[BAR_ROW]
    (a0, b0), *_, (a1, b1) = stroke_runs(row)
    left, right = centroid(row, a0 - 2, b0 + 2), centroid(row, a1 - 2, b1 + 2)
    return (right - left) / DIAMETER_MM


def outer_centers(ink, y):
    """Centri del tratto più esterno a sinistra e a destra sulla riga y."""
    row = ink[y]
    runs = stroke_runs(row)
    (a0, b0), (a1, b1) = runs[0], runs[-1]
    return centroid(row, a0 - 1, b0 + 1), centroid(row, a1 - 1, b1 + 1)


def lower_edge(ink, x, lo, hi):
    """Bordo inferiore (sub-pixel, soglia 50%) del tratto più basso in colonna x."""
    c = ink[lo:hi, x]
    i = np.where(c > 127.5)[0][-1]
    a, b = c[i], c[i + 1]
    return lo + i + (a - 127.5) / (a - b)


def two_lines(ink, x, lo=460, hi=478):
    """Le due linee orizzontali ravvicinate del fondo: separa al minimo d'intensità."""
    c = ink[lo:hi, x]
    peaks = np.argsort(c)[::-1]
    p0 = peaks[0]
    p1 = next(p for p in peaks if abs(p - p0) > 3)
    p0, p1 = sorted((p0, p1))
    split = p0 + int(np.argmin(c[p0:p1 + 1]))
    return centroid(c, max(p0 - 3, 0), split) + lo, centroid(c, split, min(p1 + 3, len(c) - 1)) + lo


def smooth(points, sigma_px=0.25, n=40, w=None):
    pts = np.asarray(points, dtype=float)
    tck, _ = splprep(pts.T, w=w, s=len(pts) * sigma_px**2)
    return np.array(splev(np.linspace(0, 1, n), tck)).T


def trace(path=DRAWING):
    ink = load(path)
    s = bar_scale(ink)

    lr = np.array([outer_centers(ink, y) for y in range(366, 377)])
    cx = lr.mean()                                        # asse di simmetria

    y_top = np.mean([centroid(ink[:, x], 300, 315) for x in TOP_COLS])

    def hw(y):
        left, right = outer_centers(ink, y)
        return (right - left) / 2

    # raccordo superiore (colonne) + fianco lunetta/cassa (righe), in px (r, y)
    upper = []
    for x in CORNER_COLS:
        upper.append((x - cx, centroid(ink[:, x], 300, 330)))
    upper += [(hw(y), float(y)) for y in SIDE_ROWS]
    corner_start_r = next(r for r, y in upper if y - y_top > 0.1)

    # fianco rettilineo sotto le anse: pendenza dr/dy dal tratto visibile,
    # prolungata (coperta dalle anse) fino alla linea di fondo
    m, _ = np.polyfit(list(FLANK_ROWS), [hw(y) for y in FLANK_ROWS], 1)

    line_a, line_b = two_lines(ink, BACK_LINE_COL)

    # fondello: righe per la parte ripida, colonne (bordo inferiore - mezzo tratto) per quella piatta
    dome = []
    for y in DOME_ROWS:
        row = ink[y, int(cx) - 170:int(cx) - 100]
        a, b = stroke_runs(row)[-1]
        x_l = int(cx) - 170 + centroid(row, a - 1, b + 1)
        row_r = ink[y, int(cx) + 100:int(cx) + 170]
        a, b = stroke_runs(row_r)[0]
        x_r = int(cx) + 100 + centroid(row_r, a - 1, b + 1)
        dome.append(((x_r - x_l) / 2, float(y)))
    for r in range(DOME_MAX_R_COLS, SENSOR_R_PX, -1):
        ys = [lower_edge(ink, int(round(cx + sgn * r)), 470, 510) for sgn in (-1, 1)]
        dome.append((float(r), np.mean(ys) - STROKE_HALF))
    # il fondello esce dalla linea di fondo: punto d'attacco estrapolato (parabola
    # x(y) sulle prime righe) e tenuto fermo nello smoothing con peso alto
    rows = np.array(dome[:6])
    anchor = (float(np.polyval(np.polyfit(rows[:, 1], rows[:, 0], 2), line_b)), float(line_b))
    dome.insert(0, anchor)
    sensor_y = np.mean([lower_edge(ink, int(round(cx + d)), 470, 510) for d in range(-15, 16)]) - STROKE_HALF

    y0 = sensor_y                                          # z = 0

    def mm(r, y):
        return [round(float(r) / s, 4), round(float(y0 - y) / s, 4)]

    upper_s = smooth(upper)
    dome_s = smooth(dome, w=[20.0] + [1.0] * (len(dome) - 1))
    r_end, y_end = upper_s[-1]

    def flank_r(y):
        return r_end + m * (y - y_end)

    data = {
        "source": str(Path(path).name),
        "px_per_mm": s,
        "top_px": y_top,
        "zero_px": y0,
        "axis_px": cx,
        "height_mm": (y0 - y_top) / s,
        "top_z": (y0 - y_top) / s,
        "corner_start_r": corner_start_r / s,
        "upper": [mm(r, y) for r, y in upper_s],
        "flank_slope_dr_dz": float(-m),
        "flank_bottom": mm(flank_r(line_b), line_b),
        "seam_line_a": mm(flank_r(line_a), line_a),
        "dome": [mm(r, y) for r, y in dome_s],
        "sensor_r": SENSOR_R_PX / s,
        "raw": {
            "upper": [mm(r, y) for r, y in upper],
            "flank": [mm(hw(y), y) for y in FLANK_ROWS],
            "dome": [mm(r, y) for r, y in dome],
        },
    }
    return data


if __name__ == "__main__":
    data = trace(sys.argv[1] if len(sys.argv) > 1 else DRAWING)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"scala {data['px_per_mm']:.4f} px/mm, asse x={data['axis_px']:.2f}, altezza {data['height_mm']:.3f} mm")
    print(f"fianco: pendenza {data['flank_slope_dr_dz']:.3f}, fondo cassa {data['flank_bottom']}")
