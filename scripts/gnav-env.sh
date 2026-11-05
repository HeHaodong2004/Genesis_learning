#!/usr/bin/env bash
# Run a command inside the genesis-research env, isolated from ROS 2's Python 3.10 PYTHONPATH
# (~/.bashrc sources /opt/ros/humble/setup.bash, which would otherwise leak into Python 3.11).
#   scripts/gnav-env.sh python scripts/smoke_test.py --backend gpu
# GPU 0 drives the display; compute defaults to GPU 1 unless CUDA_VISIBLE_DEVICES is already set.
set -euo pipefail
ENV_PREFIX="${GNAV_ENV_PREFIX:-$HOME/miniforge3/envs/genesis-research}"
unset PYTHONPATH AMENT_PREFIX_PATH
export PYTHONNOUSERSITE=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES-1}"
export PATH="$ENV_PREFIX/bin:$PATH"
exec "$@"
