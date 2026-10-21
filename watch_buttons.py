"""Suunto Ocean - fase 2: piattaforma dei tasti + tasti (layer separati).

Il corpo di watch_body.py non viene toccato.

Piattaforma: anello rivoluzionato (quote verticali lette sulla vista frontale)
intersecato con il prisma del lobo ricalcato in pianta, uno per lato.

Tasti: per ognuno, intersezione tra la forma in pianta estrusa in verticale e la
sagoma della vista frontale estrusa in profondità: le due viste del modello
coincidono con quelle del disegno.

Forme e quote: data/buttons_mm.json (tools/trace_buttons.py).
Sistema: X a destra, Y verso ore 12 (ore 6 = -Y), Z in alto, z = 0 sul fondo.

Uso:  python watch_buttons.py   ->  export/*.step / *.stl
"""

import json
import math
from pathlib import Path

import cadquery as cq

import watch_body

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "data" / "buttons_mm.json").read_text())

RING_R_IN = 22.0        # l'anello parte dentro il corpo (a z >= 5.84 il corpo ha r >= 23.2)
RING_R_OUT = 29.0       # oltre il lobo: il contorno esterno lo dà la pianta
SEAT_R = 23.0           # il tasto centrale entra nella cassa fino a questo raggio
INNER_EDGE_R = 25.3     # punti della pianta sotto questo raggio stanno sul cerchio della cassa
SIDE_SEAT_R = 24.0      # il tasto laterale prosegue, nascosto, fino a questo raggio
CASE_EDGE_R = 25.2      # fascia sotto il bordo della cassa (r < 24.95 è coperto dall'alto)


def _mirror(pts):
    return [(-x, y) for x, y in reversed(pts)]


def _push_inner(pts, r_new):
    """Porta verso l'interno i punti che stanno sul cerchio della cassa, così il pezzo
    si attacca al corpo invece di toccarlo solo lungo una linea."""
    out = []
    for x, y in pts:
        r = math.hypot(x, y)
        out.append((x * r_new / r, y * r_new / r) if r < INNER_EDGE_R else (x, y))
    return out


def _plan_prism(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _front_prism(pts, y0, y1):
    """Sagoma della vista frontale (x, z) estrusa lungo Y da y0 a y1."""
    # il piano XZ di CadQuery ha la normale verso -Y
    return cq.Workplane("XZ").workplane(offset=-y1).polyline(pts).close().extrude(y1 - y0)


def platform() -> cq.Workplane:
    z0, z1 = DATA["platform_bottom_z"], DATA["platform_top_z"]
    ring = (
        cq.Workplane("XZ")
        .moveTo(RING_R_IN, z0).lineTo(RING_R_OUT, z0).lineTo(RING_R_OUT, z1).lineTo(RING_R_IN, z1).close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    left = _push_inner(DATA["plan"]["platform"], RING_R_IN - 0.5)
    lobes = _plan_prism(left, z0 - 1, z1 + 1).union(_plan_prism(_mirror(left), z0 - 1, z1 + 1))
    return ring.intersect(lobes)


def _button(plan, front_pts):
    """plan: un Workplane o una lista di punti della pianta."""
    if not isinstance(plan, cq.Workplane):
        plan = _plan_prism(plan, 0, 16)
    return plan.intersect(_front_prism(front_pts, -40, 40))


def _side_button_plan(mirror=False):
    """In pianta del tasto laterale si vede solo la parte esterna: verso il centro è
    coperto dalla piattaforma (più alta) e dal bordo della cassa. La zona utilizzabile
    è quindi parte visibile + lobo + fascia sotto il bordo cassa (solo lato ore 6);
    la sagoma frontale decide fin dove arriva davvero."""
    f = _mirror if mirror else (lambda p: p)
    # +0.05 mm: parte visibile e lobo condividono il bordo, devono sovrapporsi per fondersi
    visible = cq.Workplane("XY").polyline(f(DATA["plan"]["side_button"])).close().offset2D(0.05).extrude(16)
    lobe = _plan_prism(f(_push_inner(DATA["plan"]["platform"], SIDE_SEAT_R)), 0, 16)
    band = (cq.Workplane("XY").circle(CASE_EDGE_R).circle(SIDE_SEAT_R).extrude(16)
            .intersect(cq.Workplane("XY").box(60, 30, 16, centered=(True, False, False)).translate((0, -30, 0))))
    return visible.union(lobe).union(band)


def buttons() -> cq.Workplane:
    side_front = DATA["front"]["side_button"]
    left = _button(_side_button_plan(), side_front)
    right = _button(_side_button_plan(mirror=True), _mirror(side_front))
    center = _button(_push_inner(DATA["plan"]["center_button"], SEAT_R), DATA["front"]["center_button"])
    return left.union(right).union(center)


if __name__ == "__main__":
    out = ROOT / "export"
    out.mkdir(exist_ok=True)
    body = watch_body.build_body()
    plat = platform()
    btns = buttons()
    case = body.union(plat)
    for name, part in [("platform", plat), ("buttons", btns), ("case", case)]:
        cq.exporters.export(part, str(out / f"suunto_ocean_{name}.step"))
        cq.exporters.export(part, str(out / f"suunto_ocean_{name}.stl"), tolerance=0.02, angularTolerance=0.1)
        print(f"{name}: volume {part.val().Volume():.1f} mm^3, solidi {len(part.solids().vals())}")
