#!/usr/bin/env python3
# backend/tools/map_tool.py
"""
Visual world-map validator CLI.

Renders the game world as per-z-level ASCII grids and reports layout problems
(non-reciprocal exits, direction/coordinate contradictions, collisions,
dangling exits, disconnected rooms). It never fixes anything — some one-way
exits are intentional puzzle gates and are classified as such.

Usage (from anywhere):
    python3 backend/tools/map_tool.py [--z N] [--static-only] [--strict]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from typing import Any, Callable, Dict, List, Optional

from tools.map_render import render_ascii
from tools.map_validation import validate_world


def load_world() -> Dict[str, Any]:
    from managers.world import generate_world

    return generate_world(None)


def main(
    argv: Optional[List[str]] = None,
    world_loader: Callable[[], Dict[str, Any]] = load_world,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--z", type=int, default=None, help="render only this z level")
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="ignore latent (interaction-added) exits when validating",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any errors are found",
    )
    parser.add_argument(
        "--spawn",
        default="square",
        help="room id to anchor the layout (default: square)",
    )
    args = parser.parse_args(argv)

    rooms = world_loader()
    report = validate_world(
        rooms, spawn=args.spawn, include_latent=not args.static_only
    )
    print(render_ascii(report, rooms, only_z=args.z))
    if args.strict and report.has_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
