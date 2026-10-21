"""Suunto Ocean - corpo cassa (fase 1: profilo + revolve, niente bottoni/anse).

Il profilo NON è disegnato a mano: è la mezza sezione ricalcata sul disegno
tecnico (reference/suunto_ocean_drawing.png) da tools/trace_profile.py, che
scrive data/profile_mm.json. Qui la si chiude e la si rivoluziona di 360°.

Convenzione: r = distanza dall'asse [mm], z = altezza [mm], z = 0 sul punto più
basso del fondello (sensore), z = top sulla faccia superiore della lunetta.

Profilo, dall'alto:
  faccia superiore piana -> raccordo -> fianco lunetta/cassa (curva ricalcata)
  -> fianco rettilineo (pendenza letta sotto le anse, prolungata fino al fondo)
  -> fondo cassa piano -> fondello bombato (curva ricalcata) -> sensore.

Uso:  python watch_body.py   ->  export/suunto_ocean_body.step / .stl
"""

import json
import math
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).parent
PROFILE = json.loads((ROOT / "data" / "profile_mm.json").read_text())


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def _direction(a, b):
    return _unit((b[0] - a[0], b[1] - a[1]))


def half_profile() -> cq.Workplane:
    """Mezza sezione chiusa sul piano XZ (X = raggio, Z = altezza)."""
    p = PROFILE
    top = p["top_z"]
    upper = [tuple(pt) for pt in p["upper"]]
    upper[0] = (p["corner_start_r"], top)
    flank_bottom = tuple(p["flank_bottom"])
    dome = [tuple(pt) for pt in p["dome"]]
    z_case = flank_bottom[1]
    k = p["flank_slope_dr_dz"]

    return (
        cq.Workplane("XZ")
        .moveTo(0, top)
        # faccia superiore piana
        .lineTo(*upper[0])
        # raccordo + fianco lunetta + fianco cassa (ricalcati); in fondo è
        # tangente al fianco rettilineo
        .spline(upper[1:], tangents=[(1, 0), _unit((-k, -1))], includeCurrent=True, scale=False)
        # fianco rettilineo fino al fondo cassa
        .lineTo(*flank_bottom)
        # fondo cassa piano fino all'attacco del fondello (dome[0] è sulla linea di fondo)
        .lineTo(dome[0][0], z_case)
        # fondello: scende quasi in verticale e si appiattisce verso il centro
        .spline(dome[1:], tangents=[_direction(dome[0], dome[1]), _direction(dome[-2], dome[-1])],
                includeCurrent=True, scale=False)
        # gradino del sensore
        .lineTo(p["sensor_r"], 0)
        .lineTo(0, 0)
        .close()
    )


def build_body() -> cq.Workplane:
    return half_profile().revolve(360, (0, 0, 0), (0, 1, 0))


if __name__ == "__main__":
    body = build_body()
    out = ROOT / "export"
    out.mkdir(exist_ok=True)
    cq.exporters.export(body, str(out / "suunto_ocean_body.step"))
    cq.exporters.export(body, str(out / "suunto_ocean_body.stl"), tolerance=0.02, angularTolerance=0.1)

    # ingombro letto sul profilo (BoundingBox esatto su queste spline è lentissimo)
    pts = [e.positionAt(i / 400) for e in half_profile().wire().val().Edges() for i in range(401)]
    print(f"Ø {2 * max(p.x for p in pts):.3f} mm, spessore {max(p.z for p in pts) - min(p.z for p in pts):.3f} mm")
    print(f"volume: {body.val().Volume():.0f} mm^3")
