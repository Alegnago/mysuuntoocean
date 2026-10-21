"""Suunto Ocean - fase 3: anse (layer separato, non toccato dal resto).

Ogni ansa è l'intersezione tra la forma in pianta (estrusa in verticale) e la
sagoma della vista frontale (estrusa in profondità): sezione circa rettangolare
che si stringe verso l'esterno e una gamba che scende piegandosi verso fuori.
Si ricalca l'ansa in basso a sinistra della pianta; le altre tre sono speculari.

Nella pianta l'ansa finisce sul cerchio della cassa: per attaccarla al corpo i
due lati dritti vengono prolungati verso l'interno (la faccia verso il cinturino
resta piana), fino a dove la sagoma frontale la taglia.

Forme: data/lugs_mm.json (tools/trace_lugs.py). Sistema come watch_buttons.py.

Uso:  python watch_lugs.py   ->  export/suunto_ocean_lugs.step / .stl
"""

import json
import math
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "data" / "lugs_mm.json").read_text())

ARC_R = 25.4          # punti della pianta sotto questo raggio stanno sul cerchio della cassa
EXTEND_TO_X = -13.0   # i lati dritti proseguono fino a qui (oltre il taglio della sagoma frontale)


def _attached_plan():
    """Contorno in pianta dell'ansa in basso a sinistra, con i lati prolungati nella cassa."""
    pts = [tuple(p) for p in DATA["plan"]]
    n = len(pts)
    on_arc = [math.hypot(*p) < ARC_R for p in pts]
    # tratto contiguo (ciclico) sul cerchio
    start = next(i for i in range(n) if on_arc[i] and not on_arc[i - 1])
    end = start
    while on_arc[(end + 1) % n]:
        end += 1
    before = [pts[(start - k) % n] for k in (1, 3)]      # lato che arriva al cerchio
    after = [pts[(end + k) % n] for k in (1, 3)]         # lato che riparte dal cerchio

    def extend(p, q):
        """Prolunga la retta q->p oltre p fino a X = EXTEND_TO_X."""
        dx, dy = p[0] - q[0], p[1] - q[1]
        t = (EXTEND_TO_X - p[0]) / dx
        return (EXTEND_TO_X, p[1] + t * dy)

    # dal primo punto dopo il cerchio, attorno all'ansa, fino all'ultimo prima del cerchio;
    # poi si chiude passando per i due prolungamenti
    keep = [pts[(end + 1 + k) % n] for k in range(n - (end - start + 1))]
    return keep + [extend(before[0], before[1]), extend(after[0], after[1])]


def _plan_prism(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _front_prism(pts, y0, y1):
    return cq.Workplane("XZ").workplane(offset=-y1).polyline(pts).close().extrude(y1 - y0)


def lug(mirror_x=False, mirror_y=False):
    sx, sy = (-1 if mirror_x else 1), (-1 if mirror_y else 1)
    plan = [(sx * x, sy * y) for x, y in _attached_plan()]
    front = [(sx * x, z) for x, z in DATA["front"]]
    if mirror_x != mirror_y:                         # una sola specchiatura inverte il verso
        plan.reverse()
    if mirror_x:
        front.reverse()
    return _plan_prism(plan, -2, 12).intersect(_front_prism(front, -40, 40))


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
