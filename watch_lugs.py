"""Suunto Ocean - fase 3: anse (layer separato, non toccato dal resto).

Ogni ansa è un tronco di piramide deformato: l'involucro convesso (facce piane) di
pochi punti presi dal disegno.

- in alto, nascosto sotto la lunetta: il rettangolo alla quota della giunzione
  lunetta/cassa, largo in X quanto la gamba lì (tra bordo esterno e bordo interno
  della vista frontale) e in Y dal lato cinturino al bordo esterno della pianta;
- il piede (piatto): l'estremità dell'ansa in pianta, tra il bordo della punta, il
  lato cinturino e la linea tratteggiata (spigolo di sotto), da dove nella vista
  frontale comincia la punta fino al fondo;
- l'attacco in basso alla cassa: dove la linea di fondo della vista frontale
  incontra la cassa.

In pianta ne escono il contorno dell'ansa e la tratteggiata come spigolo di sotto;
nella vista frontale la sagoma della gamba, con il bordo interno come spigolo tra
due facce. Si costruisce l'ansa in basso a sinistra; le altre tre sono speculari.

Forme: data/lugs_mm.json (tools/trace_lugs.py). Sistema come watch_buttons.py.

Uso:  python watch_lugs.py   ->  export/suunto_ocean_lugs.step / .stl
"""

import json
from pathlib import Path

import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "data" / "lugs_mm.json").read_text())
PROFILE = json.loads((ROOT / "data" / "profile_mm.json").read_text())
S, Z0_PX = PROFILE["px_per_mm"], PROFILE["zero_px"]

SEAM_Y_PX = 355.98      # giunzione lunetta/cassa nella vista frontale
TIP_Y_PX = 473          # dove il bordo esterno della gamba gira nella punta
ROOT_PX = (345, 465)    # la linea di fondo incontra la cassa (vista frontale, ansa sinistra)
FOOT_Z = 0.0            # fondo del piede (piatto)


def _z(y_px):
    return (Z0_PX - y_px) / S


def _front_x(line, z):
    """X [mm] della retta della vista frontale (x_px = a*y_px + b) alla quota z."""
    a, b = line
    return (a * (Z0_PX - z * S) + b - PROFILE["axis_px"]) / S


def _fit(points):
    """Retta y = m*x + q ai minimi quadrati."""
    p = np.asarray(points)
    return np.polyfit(p[:, 0], p[:, 1], 1)


def lug_points():
    """Punti 3D dell'ansa in basso a sinistra (X < 0, Y < 0)."""
    plan = np.asarray(DATA["plan"])
    r = np.hypot(plan[:, 0], plan[:, 1])
    strap_y = float(np.median(plan[(plan[:, 1] > -11.2) & (r > 25.4), 1]))
    outer = _fit(plan[(plan[:, 1] < -16.0) & (r > 25.6) & (r < 28.0)])
    # punta (arco a r ≈ 28.3, freccia 0.13 mm: si usa la corda) come x = a*y + c,
    # perché in pianta è quasi verticale
    a, c = np.polyfit(plan[r > 28.2][:, 1], plan[r > 28.2][:, 0], 1)
    b = (a * strap_y + c, strap_y)                                # punta / lato cinturino
    # incrocio punta-esterno: x = a*y + c  e  y = m*x + q
    m, q = outer
    yc = (m * c + q) / (1 - m * a)
    c_pt = (a * yc + c, yc)                                       # punta / bordo esterno

    inner, outer_edge = DATA["inner_edge_px"], DATA["outer_edge_px"]
    z_seam, z_tip, z_root = _z(SEAM_Y_PX), _z(TIP_Y_PX), _z(ROOT_PX[1])
    x_out_top, x_in_top = _front_x(outer_edge, z_seam), _front_x(inner, z_seam)
    x_in_foot = _front_x(inner, z_tip)                            # la tratteggiata parte da qui sul lato cinturino
    x_root = (ROOT_PX[0] - PROFILE["axis_px"]) / S

    def y_outer(x):
        return m * x + q

    pts = [
        # rettangolo in alto, sotto la lunetta
        (x_out_top, strap_y, z_seam), (x_in_top, strap_y, z_seam),
        (x_in_top, y_outer(x_in_top), z_seam), (x_out_top, y_outer(x_out_top), z_seam),
        # attacco in basso alla cassa
        (x_root, strap_y, z_root), (x_root, y_outer(x_root), z_root),
    ]
    foot = [(b[0], b[1]), (x_in_foot, strap_y), c_pt]
    for z in (z_tip, FOOT_Z):
        pts += [(x, y, z) for x, y in foot]
    return pts


def _hull_solid(points):
    """Solido dall'involucro convesso: i triangoli complanari diventano una faccia."""
    p = np.asarray(points, dtype=float)
    hull = ConvexHull(p)
    faces = {}
    for simplex, eq in zip(hull.simplices, hull.equations):
        key = tuple(np.round(eq, 6))
        faces.setdefault(key, set()).update(simplex)
    occ = []
    for eq, idx in faces.items():
        n = np.array(eq[:3])
        v = p[list(idx)]
        ctr = v.mean(axis=0)
        u = np.cross(n, [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0])
        u /= np.linalg.norm(u)
        w = np.cross(n, u)
        ang = np.arctan2((v - ctr) @ w, (v - ctr) @ u)
        ring = [cq.Vector(*v[i]) for i in np.argsort(ang)]
        occ.append(cq.Face.makeFromWires(cq.Wire.makePolygon(ring, close=True)))
    return cq.Solid.makeSolid(cq.Shell.makeShell(occ)).fix()


def lug(mirror_x=False, mirror_y=False):
    sx, sy = (-1 if mirror_x else 1), (-1 if mirror_y else 1)
    pts = [(sx * x, sy * y, z) for x, y, z in lug_points()]
    return cq.Workplane("XY").add(_hull_solid(pts))


def lugs() -> cq.Workplane:
    out = lug()
    for mx, my in ((True, False), (False, True), (True, True)):
        out = out.union(lug(mx, my))
    return out


if __name__ == "__main__":
    out = ROOT / "export"
    out.mkdir(exist_ok=True)
    part = lugs()
    cq.exporters.export(part, str(out / "suunto_ocean_lugs.step"))
    cq.exporters.export(part, str(out / "suunto_ocean_lugs.stl"), tolerance=0.02, angularTolerance=0.1)
    for s in part.solids().vals():
        bb = s.BoundingBox()
        print(f"ansa: X {bb.xmin:.2f}..{bb.xmax:.2f}  Y {bb.ymin:.2f}..{bb.ymax:.2f}  "
              f"Z {bb.zmin:.2f}..{bb.zmax:.2f}  volume {s.Volume():.1f} mm^3  valida {s.isValid()}")
