"""Save/load. JSON, human-readable, one file per town."""
from __future__ import annotations
import json
import os
from pathlib import Path

from .world import World


def save_world(world: World, path: str) -> None:
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(world.to_dict(), f, indent=2)


def load_world(path: str) -> World:
    with open(path) as f:
        return World.from_dict(json.load(f))
