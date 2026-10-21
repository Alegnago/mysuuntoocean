"""Genera i dati dell'anteprima web (docs/preview.html).

- profilo: gli stessi punti di watch_body.half_profile(), rivoluzionati nel
  visualizzatore con LatheGeometry
- riferimenti: le due viste del disegno (laterale e pianta) ritagliate come PNG a
  linee bianche su fondo trasparente, con dimensioni e posizione in mm, da
  mettere in scena come piani
- quote principali

Uso:  python tools/export_preview.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import watch_body as wb

DOCS = ROOT / "docs"
PAGE = DOCS / "preview.html"
P = wb.PROFILE
S = P["px_per_mm"]

# ritagli del disegno (px): x0, y0, x1, y1
SIDE_CROP = (150, 285, 880, 515)
TOP_CROP = (170, 600, 860, 1280)


def sampled_profile():
    """Punti del profilo in ordine, dal centro del vetro al centro del fondello
    (l'asse, che chiude il profilo, è escluso)."""
    def key(v):
        return (round(v.x, 6), round(v.z, 6))

    edges = [e for e in wb.half_profile().wire().val().Edges()
             if not (abs(e.startPoint().x) < 1e-9 and abs(e.endPoint().x) < 1e-9)]
    current = (0.0, round(P["top_z"], 6))
    pts = []
    while edges:
        e = next(e for e in edges if current in (key(e.startPoint()), key(e.endPoint())))
        edges.remove(e)
        forward = key(e.startPoint()) == current
        n = 2 if e.geomType() == "LINE" else 80
        for i in range(n):
            t = i / (n - 1)
            p = e.positionAt(t if forward else 1 - t)
            pt = [round(p.x, 4), round(p.z, 4)]
            if not pts or pt != pts[-1]:
                pts.append(pt)
        current = key(e.endPoint() if forward else e.startPoint())
    return pts


def line_png(ink, crop, out):
    """Ritaglio come linee bianche con alpha = intensità del tratto."""
    x0, y0, x1, y1 = crop
    a = ink[y0:y1, x0:x1].astype(np.uint8)
    rgba = np.dstack([np.full_like(a, 255)] * 3 + [a])
    Image.fromarray(rgba, "RGBA").save(out, optimize=True)


def stroke_center(v, lo, hi):
    w = v[lo:hi + 1]
    return lo + (w * np.arange(len(w))).sum() / w.sum()


def plan_center(ink):
    """Centro della pianta: mezzeria del cerchio del vetro (orizzontale e verticale)."""
    row, col = ink[940], ink[:, 513]
    cx = (stroke_center(row, 279, 287) + stroke_center(row, 739, 747)) / 2
    cy = (stroke_center(col, 704, 712) + stroke_center(col, 1163, 1171)) / 2
    return cx, cy


def references():
    ink = 255 - np.asarray(Image.open(ROOT / "reference" / P["source"]).convert("L"))
    line_png(ink, SIDE_CROP, DOCS / "ref_side.png")
    line_png(ink, TOP_CROP, DOCS / "ref_top.png")

    # vista laterale: piano verticale per l'asse (x = raggio, y = altezza)
    x0, y0, x1, y1 = SIDE_CROP
    side = {
        "src": "ref_side.png",
        "w": (x1 - x0) / S, "h": (y1 - y0) / S,
        "x": ((x0 + x1) / 2 - P["axis_px"]) / S,
        "z": (P["zero_px"] - (y0 + y1) / 2) / S,       # altezza del centro del ritaglio
    }
    # pianta: piano orizzontale sulla faccia superiore; in basso nell'immagine = verso chi guarda la laterale
    cx, cy = plan_center(ink)
    x0, y0, x1, y1 = TOP_CROP
    top = {
        "src": "ref_top.png",
        "w": (x1 - x0) / S, "h": (y1 - y0) / S,
        "x": ((x0 + x1) / 2 - cx) / S,
        "d": ((y0 + y1) / 2 - cy) / S,                  # verso +z (lato bottoni)
    }
    return {"side": side, "top": top}


def dimensions(pts):
    """Quote nel piano della vista laterale: a, b = punti misurati (r, z) in mm,
    axis = "x" (quota orizzontale, linea alla quota z = at) o "y" (verticale, linea a r = at)."""
    r_max = max(x for x, _ in pts)
    top = P["top_z"]
    r_top = P["corner_start_r"]
    r_case, z_case = P["flank_bottom"]
    side = r_max + 5.0
    return [
        {"axis": "x", "a": [-r_max, top - 5.0], "b": [r_max, top - 5.0], "at": top + 7.0, "label": f"Ø {2 * r_max:.2f}"},
        {"axis": "x", "a": [-r_top, top], "b": [r_top, top], "at": top + 3.0, "label": f"Ø {2 * r_top:.2f}"},
        {"axis": "x", "a": [-r_case, z_case], "b": [r_case, z_case], "at": -3.5, "label": f"Ø {2 * r_case:.2f}"},
        {"axis": "y", "a": [0.0, 0.0], "b": [r_top, top], "at": side, "label": f"{top:.2f}"},
        {"axis": "y", "a": [0.0, 0.0], "b": [-r_case, z_case], "at": -side, "label": f"{z_case:.2f}"},
    ]


def mesh(part, tol=0.01):
    """Triangoli del pezzo, già nel sistema del visualizzatore: (X, Z - H/2, -Y)."""
    verts, tris = part.val().tessellate(tol, 0.15)
    h = P["top_z"] / 2
    v = [c for p in verts for c in (round(p.x, 3), round(p.z - h, 3), round(-p.y, 3))]
    return {"v": v, "i": [i for t in tris for i in t]}


def layers():
    import watch_buttons
    return {"platform": mesh(watch_buttons.platform()), "buttons": mesh(watch_buttons.buttons())}


def stats():
    import overlay
    edges = overlay.profile_edges()
    d = overlay.deviation(edges)
    k = P["flank_slope_dr_dz"]
    return {
        "top_flat_d": 2 * P["corner_start_r"],
        "case_bottom_d": 2 * P["flank_bottom"][0],
        "case_bottom_z": P["flank_bottom"][1],
        "slope": k,
        "slope_deg": float(np.degrees(np.arctan(k))),
        "dev_max_mm": float(d.max() / S),
        "dev_mean_px": float(d.mean()),
    }


if __name__ == "__main__":
    pts = sampled_profile()
    data = {
        "profile": pts,
        "diameter": round(2 * max(x for x, _ in pts), 3),
        "height": round(max(z for _, z in pts) - min(z for _, z in pts), 3),
        "refs": references(),
        "dims": dimensions(pts),
        "stats": stats(),
        "layers": layers(),
    }
    html = PAGE.read_text()
    html = re.sub(r"/\*PROFILE\*/.*?/\*END\*/", lambda _: "/*PROFILE*/" + json.dumps(data) + "/*END*/", html, flags=re.S)
    PAGE.write_text(html)
    print(f"{len(pts)} punti, Ø {data['diameter']} mm, h {data['height']} mm")
    print(json.dumps(data["refs"], indent=1))
