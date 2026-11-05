"""Procedurally generated MJCF assets.

The mobile robot and the moving obstacle are *planar-jointed rigid bodies*: two slide joints (world x, y) plus,
for the robot, a yaw hinge. They are driven by Genesis joint velocity servos (``control_dofs_velocity``) with a
finite force limit, so motion is integrated by the rigid solver and contacts with walls / obstacles are resolved
by the constraint solver. Nothing is ever teleported during an episode; ``set_dofs_position`` is used only at
episode reset.

This is a deliberate abstraction of a differential-drive base: there is no wheel/ground friction model. The
non-holonomic constraint and the robot's dynamics (limits, lag, delay) are imposed by the actuator model in
``gnav.sim.dynamics``; the servo then tracks the resulting body velocity through physics.
"""

from __future__ import annotations

import os
import tempfile

ROBOT_RADIUS = 0.20
ROBOT_HALF_HEIGHT = 0.10
ROBOT_Z = 0.15  # body centre height; bottom at 0.05 m so the hull never touches the ground

MOVER_RADIUS = 0.25
MOVER_HALF_HEIGHT = 0.50
MOVER_Z = 0.52


def robot_mjcf(mass: float) -> str:
    # Joints on one body compose in declaration order: slides are world-aligned, the hinge then rotates the body.
    # The heading marker is visual only (contype=conaffinity=0) so it is invisible to the raycaster and collisions.
    return f"""<mujoco model="planar_robot">
  <compiler angle="radian"/>
  <worldbody>
    <body name="base" pos="0 0 {ROBOT_Z}">
      <joint name="x" type="slide" axis="1 0 0" damping="0"/>
      <joint name="y" type="slide" axis="0 1 0" damping="0"/>
      <joint name="yaw" type="hinge" axis="0 0 1" damping="0"/>
      <inertial pos="0 0 0" mass="{mass}" diaginertia="{0.5 * mass * ROBOT_RADIUS**2:.5f} {0.5 * mass * ROBOT_RADIUS**2:.5f} {0.5 * mass * ROBOT_RADIUS**2:.5f}"/>
      <geom name="hull" type="cylinder" size="{ROBOT_RADIUS} {ROBOT_HALF_HEIGHT}" rgba="0.165 0.47 0.84 1" friction="0.3 0.005 0.0001"/>
      <geom name="nose" type="box" size="0.08 0.03 0.02" pos="{ROBOT_RADIUS} 0 {ROBOT_HALF_HEIGHT}" rgba="1 0.85 0.1 1" contype="0" conaffinity="0"/>
    </body>
  </worldbody>
</mujoco>
"""


def mover_mjcf(mass: float) -> str:
    return f"""<mujoco model="moving_obstacle">
  <compiler angle="radian"/>
  <worldbody>
    <body name="mover" pos="0 0 {MOVER_Z}">
      <joint name="mx" type="slide" axis="1 0 0" damping="0"/>
      <joint name="my" type="slide" axis="0 1 0" damping="0"/>
      <inertial pos="0 0 0" mass="{mass}" diaginertia="1 1 1"/>
      <geom name="body" type="cylinder" size="{MOVER_RADIUS} {MOVER_HALF_HEIGHT}" rgba="0.92 0.41 0.20 1" friction="0.3 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>
"""


def write_asset(text: str, name: str) -> str:
    d = os.path.join(tempfile.gettempdir(), f"gnav_assets_{os.getuid()}")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    # Write atomically so concurrent processes never read a partial file.
    tmp = path + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)
    return path


def tall_mover_mjcf(mass: float, radius: float = 0.25, height: float = 1.8, z_bottom: float = 0.02) -> str:
    """Level B pedestrian: a cylinder taller than the 1.2 m hedges (so a 1.5 m mast lidar sees it over them).

    Slide joints x, y only (driven by a velocity servo); the bottom is lifted ``z_bottom`` above the ground plane so
    the body never touches it. Genesis tessellates the collision/ray-cast cylinder as a 32-gon (trimesh default)."""
    return f"""<mujoco model="tall_mover">
  <compiler angle="radian"/>
  <worldbody>
    <body name="mover" pos="0 0 {z_bottom + height / 2:.5f}">
      <joint name="mx" type="slide" axis="1 0 0" damping="0"/>
      <joint name="my" type="slide" axis="0 1 0" damping="0"/>
      <inertial pos="0 0 0" mass="{mass}" diaginertia="1 1 1"/>
      <geom name="body" type="cylinder" size="{radius} {height / 2:.5f}" rgba="0.92 0.41 0.20 1" friction="0.3 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>
"""
