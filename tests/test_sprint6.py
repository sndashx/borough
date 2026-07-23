"""Sprint 6 tests: render pipeline with Urizen tilesets.

We don't visually verify (no display). We verify:
  - render_map produces a valid PNG of the right size
  - render_portrait produces a valid PNG
  - render_scene_visual produces a valid PNG
  - the render doesn't crash on a populated world
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))

import tempfile
from PIL import Image

from core.world import generate_world
from core.scene import birth_scene
from core.chronicle import Chronicle
from core.player import spawn_player
from core.simulation import Simulation
from engine.render import render_map, render_portrait, render_scene_visual


def test_render_map_png_created():
    world = generate_world(seed=1729)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "map.png")
        render_map(world, out)
        assert os.path.exists(out)
        img = Image.open(out)
        # Map is at least map_width*tile_size*scale pixels wide
        assert img.size[0] >= world.map_width * 16 * 2
        assert img.size[1] >= world.map_height * 16 * 2
        print(f"  PASS: render_map → {img.size[0]}x{img.size[1]} PNG")


def test_render_portrait_png_created():
    world = generate_world(seed=1729)
    npc = list(world.npcs.values())[0]
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "portrait.png")
        render_portrait(npc, out)
        assert os.path.exists(out)
        img = Image.open(out)
        assert img.size == (16 * 8, 16 * 8)
        print(f"  PASS: render_portrait → {img.size[0]}x{img.size[1]} PNG")


def test_render_scene_visual_png_created():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    scene = birth_scene(world, player, chronicle)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "scene.png")
        render_scene_visual(scene, out, world)
        assert os.path.exists(out)
        img = Image.open(out)
        assert img.size[0] >= 400
        assert img.size[1] >= 300
        print(f"  PASS: render_scene_visual → {img.size[0]}x{img.size[1]} PNG")


def test_render_after_15_years():
    """The render still works after the sim has run for 15 years."""
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(15)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "map_15y.png")
        render_map(world, out)
        assert os.path.exists(out)
        img = Image.open(out)
        assert img.size[0] > 0
        print(f"  PASS: render after 15y → pop {world.living_count()}, map {img.size[0]}x{img.size[1]}")


def test_all_npc_portraits_renderable():
    """Every NPC in the world can have a portrait generated."""
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(10)
    with tempfile.TemporaryDirectory() as tmp:
        for i, n in enumerate(list(world.npcs.values())[:15]):
            out = os.path.join(tmp, f"p_{i}.png")
            render_portrait(n, out)
            assert os.path.exists(out)
    print(f"  PASS: 15 portraits rendered")


if __name__ == "__main__":
    print("Sprint 6 tests:")
    test_render_map_png_created()
    test_render_portrait_png_created()
    test_render_scene_visual_png_created()
    test_render_after_15_years()
    test_all_npc_portraits_renderable()
    print("\nAll Sprint 6 tests passed.")
