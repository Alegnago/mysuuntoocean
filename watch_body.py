"""Suunto Ocean - corpo cassa base (fase 1: profilo + revolve, niente bottoni/anse).

Il profilo è la mezza sezione dell'orologio (dall'asse centrale verso il bordo),
ricavata dal disegno tecnico ufficiale (Ø 49.9 mm) e rivoluzionata di 360° attorno
all'asse verticale.

Convenzione: r = distanza dall'asse [mm], z = altezza [mm], z = 0 sul fondo
(punto più basso del sensore), z = TOTAL_HEIGHT sulla faccia superiore della lunetta.

Uso:  python watch_body.py   ->  export/suunto_ocean_body.step / .stl
"""

from pathlib import Path

import math

import cadquery as cq

# --- Dimensioni globali ------------------------------------------------------
DIAMETER = 49.9            # Ø massimo (spec. ufficiale)
TOTAL_HEIGHT = 15.1        # spessore totale (spec. ufficiale)

# Le quote verticali sotto sono misurate sul disegno (12.525 px/mm), dove lo
# spessore risulta 15.57 mm: le scalo per tornare ai 15.1 ufficiali.
_DRAWING_HEIGHT = 15.57
_K = TOTAL_HEIGHT / _DRAWING_HEIGHT

R_MAX = DIAMETER / 2

# --- Lunetta (bezel) ---------------------------------------------------------
BEZEL_TOP_R = 23.5          # raggio della faccia piana superiore
BEZEL_TOP_FILLET = 0.4      # raccordo spigolo superiore
BEZEL_DEPTH = 3.83 * _K     # dal top alla linea lunetta/cassa (lato conico)

# --- Vetro / display ---------------------------------------------------------
GLASS_R = 18.4              # Ø 36.8 dal disegno in pianta
GLASS_RECESS = 0.4          # quanto il vetro sta sotto la lunetta (ipotesi)

# --- Fianco cassa -------------------------------------------------------------
SIDE_STRAIGHT_DEPTH = 6.7 * _K   # fin dove il fianco resta verticale a R_MAX
CASE_BOTTOM_DEPTH = 12.6 * _K    # fondo della cassa (linea verde orizzontale)
CASE_BOTTOM_R = 20.4             # raggio del fondo cassa dopo la rastremazione

# --- Fondello (caseback) -----------------------------------------------------
CASEBACK_TOP_R = 13.0       # dove il fondello si stacca dal fondo cassa
CASEBACK_FLAT_R = 8.0       # inizio della parte piana del fondello
SENSOR_R = 1.8              # bombatura del sensore ottico al centro
SENSOR_HEIGHT = 0.25 * _K


def _quarter_ellipse(r0, z0, r1, z1, n=12):
    """Punti di un quarto di ellisse da (r0, z0) a (r1, z1), centro in (r1, z0)."""
    a, b = r0 - r1, z0 - z1
    return [(r1 + a * math.cos(t), z0 - b * math.sin(t))
            for t in (i * math.pi / 2 / n for i in range(1, n + 1))]


def _dome_z(r):
    """Quota della calotta del sensore (sfera tangente al fondo sull'asse)."""
    radius = (SENSOR_R**2 + SENSOR_HEIGHT**2) / (2 * SENSOR_HEIGHT)
    return radius - math.sqrt(radius**2 - r**2)


def half_profile() -> cq.Workplane:
    """Mezza sezione chiusa sul piano XZ (X = raggio, Z = altezza)."""
    top = TOTAL_HEIGHT
    z_bezel = top - BEZEL_DEPTH
    z_side = top - SIDE_STRAIGHT_DEPTH
    z_case = top - CASE_BOTTOM_DEPTH
    z_back = SENSOR_HEIGHT
    f = BEZEL_TOP_FILLET

    return (
        cq.Workplane("XZ")
        .moveTo(0, top - GLASS_RECESS)
        # vetro (incassato) e gradino verso la lunetta
        .lineTo(GLASS_R, top - GLASS_RECESS)
        .lineTo(GLASS_R, top)
        # faccia superiore lunetta + raccordo
        .lineTo(BEZEL_TOP_R - f, top)
        .threePointArc((BEZEL_TOP_R - f * 0.3, top - f * 0.3), (BEZEL_TOP_R + f * 0.15, top - f))
        # lato conico della lunetta fino al Ø massimo
        .lineTo(R_MAX, z_bezel)
        # fianco verticale
        .lineTo(R_MAX, z_side)
        # rastremazione verso il fondo cassa: quarto di ellisse, tangente
        # verticale in alto e orizzontale in basso (curva verde della foto)
        .spline(_quarter_ellipse(R_MAX, z_side, CASE_BOTTOM_R, z_case), includeCurrent=True)
        # fondo cassa piano
        .lineTo(CASEBACK_TOP_R, z_case)
        # fondello bombato
        .spline(
            [(CASEBACK_FLAT_R, z_back)],
            tangents=[(-0.35, -1), (-1, 0)],
            includeCurrent=True,
        )
        .lineTo(SENSOR_R, z_back)
        # bombatura sensore: calotta sferica con centro sull'asse
        .threePointArc((SENSOR_R / 2, _dome_z(SENSOR_R / 2)), (0, 0))
        .close()
    )


def build_body() -> cq.Workplane:
    return half_profile().revolve(360, (0, 0, 0), (0, 1, 0))


if __name__ == "__main__":
    body = build_body()
    out = Path(__file__).parent / "export"
    out.mkdir(exist_ok=True)
    cq.exporters.export(body, str(out / "suunto_ocean_body.step"))
    cq.exporters.export(body, str(out / "suunto_ocean_body.stl"), tolerance=0.02, angularTolerance=0.1)

    bb = body.val().BoundingBox()
    print(f"bounding box: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm")
    print(f"volume: {body.val().Volume():.0f} mm^3")
