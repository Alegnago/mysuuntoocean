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

RING_R_IN = 22.0        # le sezioni della piattaforma partono dentro il corpo
SEAM_ROW_PX = 355.98    # riga della giunzione lunetta/cassa nella vista frontale del disegno
RING_R_OUT = 29.0       # limite esterno della zona utile dei tasti
SEAT_R = 23.0           # il tasto centrale entra nella cassa fino a questo raggio
INNER_EDGE_R = 25.3     # punti della pianta sotto questo raggio stanno sul cerchio della cassa
SIDE_SEAT_R = 24.0      # il tasto laterale prosegue, nascosto, fino a questo raggio
CASE_EDGE_R = 25.2      # fascia sotto il bordo della cassa (r < 24.95 è coperto dall'alto)

# raccordi del lobo: il bordo in comune con il tasto prosegue e entra tangente nel
# cerchio della cassa a questi angoli (gradi dalle ore 6, lato sinistro)
CASE_R = max(p[0] for p in watch_body.PROFILE["upper"])   # Ø massimo della cassa / 2
BLEND_END_DEG = (-15.5, -46.0)     # (verso il tasto centrale, verso l'ansa)
SHARED_EDGE_TOL = 0.3              # mm: punti del lobo così vicini al tasto sono il bordo in comune
NEAR_TRIM = 4                      # punti del bordo saltati verso il tasto centrale (spigolo arrotondato del tasto)


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


def _dist_to_polygon(p, poly):
    best = math.inf
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / (vx * vx + vy * vy or 1)))
        best = min(best, math.hypot(p[0] - ax - t * vx, p[1] - ay - t * vy))
    return best


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def _blend(e, t_e, ang_deg, n=24):
    """Bézier cubica da e (direzione t_e) al punto del cerchio della cassa ad ang_deg,
    dove arriva tangente al cerchio."""
    a = math.radians(ang_deg)
    t = (CASE_R * math.sin(a), -CASE_R * math.cos(a))          # ore 6 = -Y
    # tangente al cerchio nel verso in cui si allontana dal lobo
    tan = _unit((-t[1], t[0]))
    if (tan[0] * (t[0] - e[0]) + tan[1] * (t[1] - e[1])) < 0:
        tan = (-tan[0], -tan[1])
    k = 0.45 * math.dist(e, t)
    p1 = (e[0] + t_e[0] * k, e[1] + t_e[1] * k)
    p2 = (t[0] - tan[0] * k, t[1] - tan[1] * k)
    pts = []
    for i in range(1, n + 1):
        u = i / n
        b = [(1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3]
        pts.append((b[0] * e[0] + b[1] * p1[0] + b[2] * p2[0] + b[3] * t[0],
                    b[0] * e[1] + b[1] * p1[1] + b[2] * p2[1] + b[3] * t[1]))
    return pts


def platform_outline():
    """Lobo sinistro in pianta: bordo in comune con il tasto (dal disegno) +
    raccordi tangenti al cerchio della cassa alle due estremità + chiusura interna."""
    lobe = [tuple(p) for p in DATA["plan"]["platform"]]
    btn = [tuple(p) for p in DATA["plan"]["side_button"]]
    shared = [_dist_to_polygon(p, btn) < SHARED_EDGE_TOL for p in lobe]
    # tratto contiguo (ciclico) di punti in comune
    n = len(lobe)
    start = next(i for i in range(n) if shared[i] and not shared[i - 1])
    edge = []
    i = start
    while shared[i % n]:
        edge.append(lobe[i % n])
        i += 1
    # orienta il bordo dal lato del tasto centrale (angolo maggiore) verso l'ansa
    ang = lambda p: math.degrees(math.atan2(p[0], -p[1]))
    if ang(edge[0]) < ang(edge[-1]):
        edge.reverse()
    edge = edge[NEAR_TRIM:]
    near, far = BLEND_END_DEG
    head = _blend(edge[0], _unit((edge[0][0] - edge[2][0], edge[0][1] - edge[2][1])), near)
    tail = _blend(edge[-1], _unit((edge[-1][0] - edge[-3][0], edge[-1][1] - edge[-3][1])), far)
    outline = list(reversed(head)) + edge + tail
    # chiusura dentro il corpo
    r_in = RING_R_IN - 0.5
    for a in (far, near):
        ar = math.radians(a)
        outline.append((r_in * math.sin(ar), -r_in * math.cos(ar)))
    return outline


def _plan_prism(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _front_prism(pts, y0, y1):
    """Sagoma della vista frontale (x, z) estrusa lungo Y da y0 a y1."""
    # il piano XZ di CadQuery ha la normale verso -Y
    return cq.Workplane("XZ").workplane(offset=-y1).polyline(pts).close().extrude(y1 - y0)


# --- piattaforma: loft di sezioni radiali ----------------------------------------
# Profilo della sezione (vista dal lato, foto del lato ore 3 + vista frontale del disegno):
# dalla giunzione con la lunetta la superficie prosegue l'inclinazione della lunetta e
# si apre fino a una spalla, scende in verticale al raggio del contorno in pianta, e
# sotto rientra inclinata fino al fianco del corpo.
SHOULDER_DROP = 0.57        # spalla sotto la giunzione (linea a lente della vista frontale)
SHOULDER_RAMP = 0.6         # mm di sporgenza oltre la cassa per avere la spalla piena
BAND_BOTTOM_Z = 5.35        # bordo inferiore della fascia sotto il tasto centrale (linea y≈433)
FLANK_MEET_Z = 4.57         # dove la superficie inferiore incontra il fianco (linea y≈443)
FADE_DEG = 6.0              # gradi verso le anse in cui la fascia si riassorbe nel corpo
SECTION_STEP_DEG = 1.5
# le superfici del loft non devono essere tangenti a quelle del corpo (le booleane di OCC
# falliscono): dove la piattaforma sparisce, la sezione rientra un poco nel corpo
END_INSET = 0.5             # mm di rientro delle sezioni alle estremità (fade = 0)
SEAM_INSET = 0.3            # la spalla parte da dentro la lunetta, sulla giunzione
BAND_INSET = 0.05           # la fascia centrale sta appena dentro il cerchio della cassa


def _body_r():
    """Raggio del corpo in funzione di z (silhouette esterna del revolve)."""
    import numpy as np
    pts = []
    for e in watch_body.half_profile().wire().val().Edges():
        for i in range(201):
            v = e.positionAt(i / 200)
            if v.x > 20:
                pts.append((v.z, v.x))
    pts.sort()
    zs = np.array([p[0] for p in pts]); rs = np.array([p[1] for p in pts])
    # per ogni z il raggio massimo (silhouette)
    import collections
    best = collections.OrderedDict()
    for z, r in zip(zs.round(3), rs):
        best[z] = max(best.get(z, 0), r)
    zz = np.array(list(best.keys())); rr = np.array(list(best.values()))
    return lambda z: float(np.interp(z, zz, rr))


def _ray_radius(poly, theta_deg):
    """Raggio massimo a cui il raggio uscente all'angolo theta incontra il poligono."""
    a = math.radians(theta_deg)
    d = (math.sin(a), -math.cos(a))
    best = None
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        ex, ey = bx - ax, by - ay
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        t = (ax * ey - ay * ex) / den          # distanza lungo il raggio
        u = (ax * d[1] - ay * d[0]) / den      # posizione sul lato
        if t > 0 and 0 <= u <= 1:
            best = t if best is None else max(best, t)
    return best


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _section(theta, R, fade, body_r, seam, lobe_bottom):
    """Sezione chiusa (punti 3D) nel semipiano all'angolo theta."""
    w = _smooth((R - CASE_R) / SHOULDER_RAMP)          # 0 = a filo cassa, 1 = lobo pieno
    inset = (1 - fade) * END_INSET
    R = max(R, CASE_R) - BAND_INSET * (1 - w) - inset
    z_sh = seam - SHOULDER_DROP * w
    z_bulge = 10.24                                     # quota del raggio massimo del corpo
    z_bo = BAND_BOTTOM_Z + (lobe_bottom - BAND_BOTTOM_Z) * w
    z_bo = z_bulge + (z_bo - z_bulge) * fade
    z_f = z_bulge + (FLANK_MEET_Z - z_bulge) * fade
    r_f = min(body_r(z_f) - inset, R - 0.05)
    r_a = body_r(seam) - SEAM_INSET - inset
    r_in = RING_R_IN
    # spalla: Bézier quadratica dalla giunzione (appena dentro la lunetta) alla spalla
    # (il punto di controllo non supera la parete, altrimenti la sezione si ripiega)
    c = (min(body_r(seam) + 0.2, r_a + 0.6 * (R - r_a)), z_sh)
    rz = [(r_in, seam), (r_a, seam)]
    for u in (0.25, 0.5, 0.75):
        rz.append(((1 - u) ** 2 * r_a + 2 * u * (1 - u) * c[0] + u * u * R,
                   (1 - u) ** 2 * seam + 2 * u * (1 - u) * c[1] + u * u * z_sh))
    rz += [(R, z_sh), (R, z_bo), (r_f, z_f), (r_in, z_f)]
    a = math.radians(theta)
    return [cq.Vector(r * math.sin(a), -r * math.cos(a), z) for r, z in rz]


def platform() -> cq.Workplane:
    body_r = _body_r()
    seam = (watch_body.PROFILE["zero_px"] - SEAM_ROW_PX) / watch_body.PROFILE["px_per_mm"]
    lobe_bottom = DATA["platform_bottom_z"]
    left = platform_outline()
    near, far = BLEND_END_DEG
    span = abs(far)
    n = int(round(2 * span / SECTION_STEP_DEG))
    wires = []
    for i in range(n + 1):
        th = -span + i * 2 * span / n
        R = CASE_R if abs(th) <= abs(near) else (_ray_radius(left, -abs(th)) or CASE_R)
        fade = _smooth((span - abs(th)) / FADE_DEG)
        pts = _section(th, R, fade, body_r, seam, lobe_bottom)
        wires.append(cq.Wire.makePolygon(pts, close=True))
    return cq.Workplane("XY").add(cq.Solid.makeLoft(wires, ruled=False))


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
    lobe = _plan_prism(f(platform_outline()), 0, 16)
    band = (cq.Workplane("XY").circle(CASE_EDGE_R).circle(SIDE_SEAT_R).extrude(16)
            .intersect(cq.Workplane("XY").box(60, 30, 16, centered=(True, False, False)).translate((0, -30, 0))))
    keep = cq.Workplane("XY").circle(RING_R_OUT).circle(SIDE_SEAT_R).extrude(16)
    return visible.union(lobe).union(band).intersect(keep)


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
