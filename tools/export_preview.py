"""Inietta il profilo del modello nell'anteprima web (docs/preview.html).

Il visualizzatore rivoluziona questi stessi punti (LatheGeometry), quindi la
forma è quella di watch_body.half_profile().

Uso:  python tools/export_preview.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import watch_body as wb

PAGE = ROOT / "docs" / "preview.html"


def sampled_profile():
    """Punti del profilo in ordine, dal centro del vetro al centro del fondello
    (l'asse, che chiude il profilo, è escluso)."""
    def key(v):
        return (round(v.x, 6), round(v.z, 6))

    edges = [e for e in wb.half_profile().wire().val().Edges()
             if not (abs(e.startPoint().x) < 1e-9 and abs(e.endPoint().x) < 1e-9)]
    current = (0.0, round(wb.PROFILE["top_z"], 6))
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


if __name__ == "__main__":
    pts = sampled_profile()
    p = wb.PROFILE
    data = {
        "profile": pts,
        "diameter": round(2 * max(x for x, _ in pts), 3),
        "height": round(max(z for _, z in pts) - min(z for _, z in pts), 3),
    }
    html = PAGE.read_text()
    html = re.sub(r"/\*PROFILE\*/.*?/\*END\*/", "/*PROFILE*/" + json.dumps(data) + "/*END*/", html, flags=re.S)
    PAGE.write_text(html)
    print(f"{len(pts)} punti, Ø {data['diameter']} mm, h {data['height']} mm")
