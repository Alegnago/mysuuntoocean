"""Render rapido del corpo (intero + sezione) per controllo visivo."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cadquery as cq
import watch_body as wb


def mesh(shape, tol=0.03):
    verts, tris = shape.tessellate(tol, 0.2)
    v = np.array([(p.x, p.y, p.z) for p in verts])
    return v[np.array(tris)]


def draw(ax, faces, elev, azim, title):
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    n = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    ax.add_collection3d(Poly3DCollection(faces, facecolors=plt.cm.Greys(0.25 + 0.6 * shade), linewidths=0))
    ax.set_xlim(-25, 25); ax.set_ylim(-25, 25); ax.set_zlim(0, 15.1)
    ax.set_box_aspect((50, 50, 15.1), zoom=1.4); ax.view_init(elev, azim); ax.axis("off"); ax.set_title(title)


def main(out):
    body = wb.build_body()
    cut = body.cut(cq.Workplane("XY").box(60, 30, 40, centered=(True, False, False)).translate((0, 0, -5)))
    fig = plt.figure(figsize=(15, 4.5), dpi=130)
    draw(fig.add_subplot(131, projection="3d"), mesh(body.val()), 25, -60, "vista 3/4")
    draw(fig.add_subplot(132, projection="3d"), mesh(body.val()), -25, -60, "vista dal fondello")
    draw(fig.add_subplot(133, projection="3d"), mesh(cut.val()), 12, 90, "sezione (profilo del revolve)")
    fig.savefig(out, bbox_inches="tight")


if __name__ == "__main__":
    main(sys.argv[1])
