"""Top-down diagnostic rendering drawn ONLY from recorded simulator state and recorded sensor returns.

Every element comes from an episode recorded by ``TrajectoryRecorder``: poses, mover state, contact flags and
clearance (privileged ground truth), plus the robot's actual planar ray returns (``obs_rays``)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrow, Rectangle, Wedge  # noqa: E402

# Reference palette (dataviz skill): categorical slots for entities, status colours for events.
C = {
    "surface": "#fcfcfb", "text": "#0b0b0b", "text2": "#52514e", "grid": "#e4e3df",
    "robot": "#2a78d6", "mover": "#eb6834", "goal": "#1baf7a", "obstacle": "#8a8985", "wall": "#52514e",
    "ray": "#2a78d6", "collision": "#d03b3b", "near": "#ec835a", "heavy": "#eb6834", "agile": "#2a78d6",
}


def draw_state(ax, ep, meta, t, show_rays=True, title=None, trail=True):
    A = meta["arena_half"]
    rr, mr = meta["robot_radius"], meta["mover_radius"]
    ax.set_facecolor(C["surface"])
    ax.add_patch(Rectangle((-A, -A), 2 * A, 2 * A, fill=False, lw=3, ec=C["wall"]))
    for (cx, cy), (hx, hy) in zip(ep["obstacle_xy"], ep["obstacle_half"]):
        ax.add_patch(Rectangle((cx - hx, cy - hy), 2 * hx, 2 * hy, fc=C["obstacle"], ec=C["wall"], lw=0.8))
    g = ep["goal_xy"]
    ax.add_patch(Circle(g, meta["goal_radius"], fc=C["goal"], alpha=0.35, ec=C["goal"], lw=1.5))
    ax.plot(*g, marker="*", ms=12, color=C["goal"], mec="white", mew=0.8, zorder=5)
    # mover: patrol segment + current body
    if np.all(np.abs(ep["mover_a"]) < A + 1):
        ax.plot([ep["mover_a"][0], ep["mover_b"][0]], [ep["mover_a"][1], ep["mover_b"][1]], ls=":", lw=1,
                color=C["mover"], alpha=0.7)
        m = ep["mover_xy"][t]
        vis = bool(ep["mover_visible"][t])
        ax.add_patch(Circle(m, mr, fc=C["mover"], ec=C["text"] if vis else "white", lw=2 if vis else 1,
                            alpha=1.0 if vis else 0.55, zorder=4))
    pose = ep["robot_pose"]
    if trail:
        ax.plot(pose[: t + 1, 0], pose[: t + 1, 1], lw=2, color=C["robot"], alpha=0.85, zorder=3)
    x, y, th = pose[t]
    # sensor: actual recorded ray returns, drawn from the sensor origin (robot centre axis)
    if show_rays and "obs_rays" in ep and "ray_angles" in meta:
        ang = np.asarray(meta["ray_angles"])
        R = ep["obs_rays"][t] * meta["max_range"]
        fov = np.degrees(ang.max() - ang.min())
        ax.add_patch(Wedge((x, y), meta["max_range"], np.degrees(th) - fov / 2, np.degrees(th) + fov / 2,
                           fc=C["ray"], alpha=0.06, ec="none"))
        for a, r in zip(ang, R):
            ex, ey = x + r * np.cos(th + a), y + r * np.sin(th + a)
            ax.plot([x, ex], [y, ey], lw=0.5, color=C["ray"], alpha=0.35, zorder=2)
            if r < meta["max_range"] - 1e-3:
                ax.plot(ex, ey, ".", ms=3, color=C["ray"], zorder=2)
    contact = ep["contact"][: t + 1].astype(bool)
    near = (ep["clearance"][: t + 1] < 0.15) & ~contact
    if near.any():
        ax.scatter(pose[: t + 1][near, 0], pose[: t + 1][near, 1], s=14, color=C["near"], zorder=6,
                   label="near-collision (<0.15 m)")
    if contact.any():
        ax.scatter(pose[: t + 1][contact, 0], pose[: t + 1][contact, 1], s=110, marker="X", color=C["collision"],
                   ec="white", lw=0.8, zorder=8, label="collision")
    hit = bool(ep["contact"][t])
    ax.add_patch(Circle((x, y), rr, fc=C["robot"], ec=C["collision"] if hit else "white", lw=3 if hit else 1.2,
                        zorder=7))
    ax.add_patch(FancyArrow(x, y, 0.45 * np.cos(th), 0.45 * np.sin(th), width=0.05, head_width=0.16,
                            head_length=0.12, color="white", ec=C["text"], lw=0.6, zorder=9))
    ax.set_xlim(-A - 0.3, A + 0.3)
    ax.set_ylim(-A - 0.3, A + 0.3)
    ax.set_aspect("equal")
    ax.set_xticks(range(-int(A), int(A) + 1, 2))
    ax.set_yticks(range(-int(A), int(A) + 1, 2))
    ax.tick_params(labelsize=7, colors=C["text2"])
    for s in ax.spines.values():
        s.set_visible(False)
    if title:
        ax.set_title(title, fontsize=10, color=C["text"], loc="left")


def frame_image(ep, meta, t, size_px=480, hud=True) -> np.ndarray:
    dpi = 100
    fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi, facecolor=C["surface"])
    ax = fig.add_axes([0.06, 0.06, 0.9, 0.84])
    draw_state(ax, ep, meta, t)
    if hud:
        dt = meta["control_dt"]
        a = ep["action"][min(t, len(ep["action"]) - 1)] if len(ep["action"]) else (0, 0)
        status = "COLLISION" if ep["contact"][t] else ("near-collision" if ep["clearance"][t] < 0.15 else "")
        fig.text(0.06, 0.955, f"t={t * dt:5.1f}s  cmd=({a[0]:+.2f},{a[1]:+.2f})  clearance={ep['clearance'][t]:.2f} m"
                 f"  mover {'VISIBLE' if ep['mover_visible'][t] else 'hidden'}", fontsize=7.5, color=C["text"],
                 family="monospace")
        if status:
            fig.text(0.06, 0.915, ("✖ " if ep["contact"][t] else "▲ ") + status, fontsize=9, weight="bold",
                     color=C["collision"] if ep["contact"][t] else C["near"])
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return img


def outcome(ep) -> str:
    s = ep["stats"] if "stats" in ep else {}
    if s.get("success", 0) > 0.5:
        return "success"
    if s.get("collided", 0) > 0.5:
        return "collision"
    return "timeout"
