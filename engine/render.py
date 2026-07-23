"""Engine layer — top-down render using the Urizen Onebit v2.0 tileset.

Tile atlas: /home/command/Downloads/urizen_onebit_tileset__v2d0.png
  167 cols x 40 rows of 16x16 tiles
  5 sections separated by 12px magenta dividers at tile-col boundaries
  20-21, 41-42, 63-64, 84-85:

  Section A (cols 0-20,  21 cols): walls, terrain, animals, items, doors, furniture
  Section B (cols 21-41, 21 cols): floors/wood, arrows/weapons, baskets/fences,
                                   gates/signs, mailboxes/fountains, scrolls/papers
  Section C (cols 42-63, 22 cols): gray walls, COLORED HOUSES (red/blue/green/
                                   purple/yellow/teal), UI icons, papers, potions
  Section D (cols 64-84, 21 cols): UI icons (guns, hearts, gems), standing green/
                                   cyan/white figures, SKELETONS/ZOMBIES/DEMONS
                                   (rows 14-20)
  Section E (cols 85-166, 82 cols): NPC ANIMATION STRIP (rows 0-24, full width
                                    = 25 * 82 = 2050 character frames), small
                                    colored characters (rows 25-31), pixel fonts
                                    (rows 32-39).

Verified row-by-row map (all coords confirmed by visual inspection):

  Section A (cols 0-20):
    r0: brown wood floor + arches + door arch + insets (interior)
    r1: brown wood wall (with windows/arches)
    r2: gray stone wall
    r3: red brick wall
    r4: brown plank wall
    r5: cobblestone path
    r6: mountain range (brown peaks)
    r7: forest (green pine/deciduous mix)
    r8: shrubs/saplings
    r9: red mushrooms / small plants
    r10: brown terrain (rocks/ground)
    r11: water (blue rivers/ponds)
    r12: brown trees (sparse forest)
    r13: wildlife (rabbits, pigs, dragons)
    r14: butterflies/insects
    r15: horses/camels/cows
    r16-17: food (bread, meat, fish, fruit)
    r18-26: clothes/tools/weapons/armor/gems
    r27: doors + windows
    r28-29: furniture (chairs, tables, workbench, anvil, bed, fireplace, etc.)
    r30-31: banners/cream items
    r32-39: UI / signs / empty

  Section C (cols 42-63) — colored houses:
    r5: row of colored house exteriors (red, white, gray, blue, yellow, cyan)
    r6: more colored houses (red cart, blue, green, purple, gray, trees)
    r7: building doors — brown wood doors (cols 42-46), gray stone walls (47-49),
        red brick walls (50-62), and small windows
    r8-12: UI icons, colored papers/documents, signs
    r13-22: potions, gems, food, weapons, armor

  Section D (cols 64-84) — characters & monsters:
    r0-5: UI icons (weapons, ammo, hearts, music, arrows)
    r6-9: green standing figures (rangers?), blue, red, gray
    r10-13: cyan figures, white figures (villagers)
    r14: skeletons
    r15-16: skeletons/zombies
    r17-19: demons (knight, dragon, lord)
    r20-26: demon fiends, eyes, skulls

  Section E (cols 85-166) — NPC animation strip:
    r0-24: 25 rows × 82 cols = full-width NPC character animation
           (each col = a different character, each row = different pose)

We sample colors from family-name hash to pick a unique tile per NPC.
"""
from __future__ import annotations

import hashlib
import os
import random as _random
from pathlib import Path
from typing import Optional, Tuple, List

from PIL import Image, ImageDraw, ImageFont

from core.world import World
from core.building import Building, BuildingType
from core.npc import NPC, LifecycleState


TILE_SIZE = 16
URIZEN_ONEBIT = "/home/command/Downloads/urizen_onebit_tileset__v2d0.png"


# ============================================================
# Tile coordinate constants — all verified by visual inspection.
# Format: (col, row) within the full 167x40 grid.
# ============================================================

# --- Terrain tiles (Section A rows 5-12) ---
# Used as ground tiles based on world tile terrain type.
# Coords are (col, row). All values verified by tile census.
GRASS_TILES: List[Tuple[int, int]] = [(c, 7) for c in range(20)]
DIRT_TILES: List[Tuple[int, int]] = [(c, 10) for c in range(20)]
COBBLE_PATH_TILES: List[Tuple[int, int]] = [(c, 5) for c in range(20)]
WATER_TILES: List[Tuple[int, int]] = [(c, 11) for c in range(20)]
FOREST_TILES: List[Tuple[int, int]] = [(c, 7) for c in range(20)] + [(c, 12) for c in range(20)]
MOUNTAIN_TILES: List[Tuple[int, int]] = [(c, 6) for c in range(20)]
SHRUB_TILES: List[Tuple[int, int]] = [(c, 8) for c in range(20)]
FLOWER_TILES: List[Tuple[int, int]] = [(c, 9) for c in range(20)]

# --- Interior floor (Section A row 0) ---
INTERIOR_FLOOR_TILES: List[Tuple[int, int]] = [(c, 0) for c in range(20)]

# --- Walls (Section A rows 1-4) ---
# Verified by tile census: brown_wood=r1, gray_stone=r2, red_brick=r3,
# brown_plank=r4. There is no separate wood_dark row; alias it to brown_wood.
WALL_TILES = {
    "brown_wood":   [(c, 1) for c in range(20)],
    "gray_stone":   [(c, 2) for c in range(20)],
    "red_brick":    [(c, 3) for c in range(20)],
    "brown_plank":  [(c, 4) for c in range(20)],
    "wood_dark":    [(c, 1) for c in range(10, 20)],
}

# --- Colored HOUSE EXTERIORS (Section C rows 5-7) — for building tops ---
# Verified by tile census. Section C col 42-63 split into colored house types.
HOUSE_EXTERIOR_TILES = {
    # Row 5 — colored houses (red, blue, yellow, white, gray, cyan)
    "house_red":      [(42, 5), (44, 5), (48, 5), (49, 5), (53, 5), (54, 5)],
    "house_blue":     [(47, 5), (52, 5)],
    "house_yellow":   [(51, 5)],
    "house_white":    [(43, 5), (45, 5), (50, 5)],
    "house_gray":     [(55, 5), (60, 5)],
    "house_cyan":     [(56, 5), (57, 5), (58, 5), (59, 5), (61, 5), (62, 5), (63, 5)],
    # Row 6 — secondary house exteriors (purple, green, red_cart, blue, wood, gray)
    "house_purple":   [(47, 6), (48, 6), (49, 6), (51, 6)],
    "house_green":    [(46, 6), (50, 6)],
    "house_red_cart": [(44, 6)],
    "house_blue_2":   [(45, 6)],
    "house_wood_2":   [(42, 6), (43, 6)],
    "house_gray_2":   [(52, 6), (53, 6)],
    # Row 7 — material walls (brown wood 42-46, gray stone 47-49, red brick 50-63)
    "red_brick":      [(c, 7) for c in range(50, 64)],
    "gray_stone":     [(c, 7) for c in range(47, 50)],
    "wood_brown":     [(c, 7) for c in range(42, 47)],
    # Window/sign decorations
    "window_sign":    [(49, 7), (50, 7)],
}

HOUSE_DOOR_TILES = {
    "wood_closed":    [(42, 7), (43, 7)],
    "wood":           [(44, 7), (45, 7)],
}

# --- Doors & windows (Section A row 27) ---
DOOR_TILES = {
    "open":   (1, 27),
    "closed": (0, 27),
}
WINDOW_TILE = (2, 27)

# --- Furniture (Section A rows 28-29) ---
FURNITURE_TILES = {
    "chair":       (0, 28),
    "stool":       (1, 28),
    "table_round": (2, 28),
    "table_square":(3, 28),
    "workbench":   (4, 28),
    "anvil":       (5, 28),
    "stove":       (6, 28),
    "oven":        (7, 28),
    "bed":         (8, 28),
    "dresser":     (9, 28),
    "fireplace":   (10, 28),
    "column":      (11, 28),
    "shelf":       (12, 28),
    "wardrobe":    (0, 29),
    "altar":       (1, 29),
    "statue":      (3, 29),
    "throne":      (4, 29),
    "sign":        (7, 29),
    "fence":       (14, 28),
    "basket":      (15, 28),
}

# --- Items (Section A rows 14-26) ---
ITEM_TILES = {
    "food_bread":  (0, 16),
    "food_meat":   (1, 16),
    "food_fish":   (2, 16),
    "food_egg":    (3, 16),
    "food_apple":  (4, 15),
    "food_grapes": (1, 15),
    "food_carrot": (1, 14),
    "food_pumpkin":(0, 14),
    "grain":       (0, 16),
    "tool":        (0, 25),
    "axe":         (3, 25),
    "hammer":      (4, 25),
    "sword":       (5, 25),
    "bow":         (0, 25),
    "shield":      (1, 26),
    "armor":       (0, 22),
    "cloth":       (0, 22),
    "potion":      (4, 17),
    "gem":         (8, 15),
    "key":         (3, 19),
    "coin":        (0, 24),
    "book":        (0, 26),
}

# --- Animals (Section A rows 10-15) ---
ANIMAL_TILES = {
    "cat":       (0, 13),
    "rat":       (1, 13),
    "rabbit":    (3, 13),
    "pig":       (0, 13),
    "chicken":   (13, 13),
    "horse":     (0, 15),
    "cow":       (3, 15),
    "sheep":     (4, 15),
    "dragon":    (5, 15),
    "wolf":      (6, 13),
    "bear":      (7, 13),
}

# --- NPC color rows in Section E (cols 85-166, rows 0-24) ---
# Each col-offset within section E corresponds to a colored character.
# We pick color via family-name hash → stable per NPC.
# Row 0 in section E is the "main" character pose row; rows 1-24 are animation frames.
NPC_COLOR_BANDS = {
    # band_name -> (section_E_col_start, base_row)
    # Each col in section E is a different colored character; we pick cols 85-166.
    # Row 0 is the standing/neutral pose, rows 1-24 are walking/attacking/dying.
    "white":       (85, 0),
    "gray":        (90, 1),
    "brown":       (95, 2),
    "tan":         (100, 3),
    "red":         (105, 4),
    "green":       (110, 5),
    "blue":        (115, 6),
    "purple":      (120, 7),
    "yellow":      (125, 8),
    "orange":      (130, 9),
    "olive":       (135, 10),
    "navy":        (140, 11),
    "teal":        (145, 12),
    "scarlet":     (150, 13),
    "crimson":     (155, 14),
    "dark_green":  (160, 15),
}

NPC_COLORS = list(NPC_COLOR_BANDS.keys())


# --- Demographic NPC variants (Section D rows 9-20) ---
# Used for special NPCs: rangers, soldiers, villagers, undead, demons.
# Each role has a range of cols (64-69) for pose variation.
DEMOGRAPHIC_TILES = {
    "ranger_green":     [(c, 9)  for c in range(64, 70)],
    "soldier_cyan":     [(c, 10) for c in range(64, 70)],
    "villager_white":   [(c, 11) for c in range(64, 70)],
    "skeleton":         [(c, 14) for c in range(64, 70)],
    "skeleton_warrior": [(c, 15) for c in range(64, 70)],
    "zombie":           [(c, 16) for c in range(64, 70)],
    "demon_knight":     [(c, 17) for c in range(64, 70)],
    "demon_dragon":     [(c, 18) for c in range(64, 70)],
    "demon_lord":       [(c, 19) for c in range(64, 70)],
    "demon_fiend":      [(c, 20) for c in range(64, 70)],
}


# ============================================================
# Helper functions
# ============================================================

def _load_onebit() -> Image.Image:
    return Image.open(URIZEN_ONEBIT).convert("RGBA")


def _crop_tile(src: Image.Image, col: int, row: int, size: int = TILE_SIZE) -> Image.Image:
    return src.crop((col * size, row * size, (col + 1) * size, (row + 1) * size))


def _hash_to_int(s: str, mod: int = 1000) -> int:
    """Stable hash for tile variation (deterministic per NPC)."""
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % mod


def _npc_key(npc: NPC) -> str:
    """Stable identifier string for an NPC (used in hashing for tile variation)."""
    if hasattr(npc, "lineage") and getattr(npc.lineage, "family_name", ""):
        return npc.lineage.family_name
    return f"{npc.first_name}_{npc.family_name}"


def _pick_npc_color(npc: NPC) -> str:
    """Stable color band per NPC based on family name."""
    idx = _hash_to_int(_npc_key(npc), len(NPC_COLORS))
    return NPC_COLORS[idx]


def _pick_npc_pose(npc: NPC) -> int:
    """Pick a column offset within section E for pose variation.
    Section E is cols 85-166 (82 cols). Cap pose offset to keep
    (base_col + pose) <= 166.
    """
    base_col, _ = NPC_COLOR_BANDS[_pick_npc_color(npc)]
    max_offset = 166 - base_col
    if max_offset < 1:
        max_offset = 1
    return _hash_to_int(_npc_key(npc) + "_pose", max_offset + 1)


def _pick_npc_animation_frame(npc: NPC) -> int:
    """Pick an animation frame (row 0-19) for the NPC.
    Rows 20-32 of section E are mostly black/empty/UI text —
    use 0-19 to stay in the character animation strip."""
    return _hash_to_int(_npc_key(npc) + "_frame", 20)


def _pick_npc_tile(npc: NPC):
    """Return (col, row) for an NPC's character sprite from section E.
    Each NPC gets a stable color band + col offset + animation frame.
    """
    color = _pick_npc_color(npc)
    base_col, base_row = NPC_COLOR_BANDS[color]
    pose_col = _pick_npc_pose(npc)
    anim_row = _pick_npc_animation_frame(npc)
    return (base_col + pose_col, base_row + anim_row)


def _pick_terrain_tile(terrain: str, x: int, y: int) -> Tuple[int, int]:
    """Pick a terrain tile based on terrain type and position."""
    idx = (x * 7 + y * 13)
    if terrain == "grass":
        pool = GRASS_TILES
    elif terrain == "dirt":
        pool = DIRT_TILES
    elif terrain == "water":
        pool = WATER_TILES
    elif terrain == "forest":
        pool = FOREST_TILES
    elif terrain == "mountain":
        pool = MOUNTAIN_TILES
    elif terrain == "path" or terrain == "cobble":
        pool = COBBLE_PATH_TILES
    elif terrain == "farmland":
        pool = DIRT_TILES  # ploughed dirt looks like dark dirt
    elif terrain == "stone":
        pool = WALL_TILES["gray_stone"]
    elif terrain == "void":
        return None  # signal to skip
    else:
        pool = DIRT_TILES  # default
    return pool[idx % len(pool)]


def _pick_wall_tile(building_type: BuildingType, idx: int = 0):
    """Pick a wall tile by building type."""
    type_map = {
        BuildingType.CHURCH: WALL_TILES["gray_stone"],
        BuildingType.TAVERN: WALL_TILES["brown_wood"],
        BuildingType.MILL: WALL_TILES["brown_plank"],
        BuildingType.SMITHY: WALL_TILES["gray_stone"],
        BuildingType.BARN: WALL_TILES["wood_dark"],
        BuildingType.GRANARY: WALL_TILES["brown_plank"],
        BuildingType.MARKET: WALL_TILES["red_brick"],
        BuildingType.HOUSE: WALL_TILES["brown_wood"],
    }
    bank = type_map.get(building_type, WALL_TILES["brown_wood"])
    return bank[idx % len(bank)]


def _pick_house_exterior(building_type: BuildingType, idx: int = 0):
    """Pick a colored house exterior from section C."""
    type_map = {
        BuildingType.CHURCH: HOUSE_EXTERIOR_TILES["gray_stone"],
        BuildingType.TAVERN: HOUSE_EXTERIOR_TILES["red_brick"],
        BuildingType.MILL: HOUSE_EXTERIOR_TILES["wood_brown"],
        BuildingType.SMITHY: HOUSE_EXTERIOR_TILES["gray_stone"],
        BuildingType.BARN: HOUSE_EXTERIOR_TILES["wood_brown"],
        BuildingType.GRANARY: HOUSE_EXTERIOR_TILES["wood_brown"],
        BuildingType.MARKET: HOUSE_EXTERIOR_TILES["red_brick"],
        BuildingType.HOUSE: HOUSE_EXTERIOR_TILES["red_brick"],
    }
    bank = type_map.get(building_type, HOUSE_EXTERIOR_TILES["red_brick"])
    return bank[idx % len(bank)]


def _pick_floor_tile(idx: int = 0):
    return INTERIOR_FLOOR_TILES[idx % len(INTERIOR_FLOOR_TILES)]


def _pick_demographic_tile(npc: NPC):
    """Pick a demographic tile based on NPC's social role/status."""
    role = getattr(npc, "social_role", None) or ""
    role = str(role).lower()
    if "skeleton" in role or "zombie" in role:
        return _pick_from_demographic("skeleton", npc)
    if "demon" in role:
        return _pick_from_demographic("demon_knight", npc)
    if "ranger" in role or "hunter" in role:
        return _pick_from_demographic("ranger_green", npc)
    if "soldier" in role or "guard" in role:
        return _pick_from_demographic("soldier_cyan", npc)
    return None


def _pick_from_demographic(key: str, npc: NPC):
    """Pick a stable pose variant from a DEMOGRAPHIC_TILES list."""
    bank = DEMOGRAPHIC_TILES.get(key)
    if not bank:
        return None
    idx = _hash_to_int(_npc_key(npc) + "_demo_" + key, len(bank))
    return bank[idx]


# ============================================================
# Top-level render functions.
# ============================================================

def render_map(world: World, out_path: str, scale: int = 3,
               show_npcs: bool = True, show_items: bool = True) -> str:
    """Render the world map at scale=3 (48px per tile)."""
    src = _load_onebit()
    tile_px = TILE_SIZE * scale
    w_px = world.map_width * tile_px
    h_px = world.map_height * tile_px
    canvas = Image.new("RGBA", (w_px, h_px + 28), (10, 8, 6, 255))
    draw = ImageDraw.Draw(canvas)

    # --- Pass 1: terrain ---
    for y in range(world.map_height):
        for x in range(world.map_width):
            if y < len(world.tiles) and x < len(world.tiles[y]):
                tile = world.tiles[y][x]
            else:
                tile = {"terrain": "void"}
            terrain = tile.get("terrain", "void")
            pos = _pick_terrain_tile(terrain, x, y)
            if pos is None:
                continue
            col, row = pos
            t = _crop_tile(src, col, row)
            t = t.resize((tile_px, tile_px), Image.NEAREST)
            canvas.paste(t, (x * tile_px, y * tile_px + 28), t)

    # --- Pass 2: ambient foliage overlay ---
    from core.world import seed_to_int
    rng = _random.Random(seed_to_int(world.seed))
    for y in range(world.map_height):
        for x in range(world.map_width):
            if y >= len(world.tiles) or x >= len(world.tiles[y]):
                continue
            terrain = world.tiles[y][x].get("terrain", "void")
            if terrain not in ("grass", "forest", "dirt"):
                continue
            r = rng.random()
            if terrain == "grass" and r < 0.10:
                col, row = rng.choice(FLOWER_TILES)
                t = _crop_tile(src, col, row).resize((tile_px, tile_px), Image.NEAREST)
                canvas.paste(t, (x * tile_px, y * tile_px + 28), t)
            elif terrain == "forest" and r < 0.15:
                col, row = rng.choice(SHRUB_TILES)
                t = _crop_tile(src, col, row).resize((tile_px, tile_px), Image.NEAREST)
                canvas.paste(t, (x * tile_px, y * tile_px + 28), t)
            elif terrain == "dirt" and r < 0.05:
                # sparse rocks on dirt
                col, row = rng.choice(MOUNTAIN_TILES)
                t = _crop_tile(src, col, row).resize((tile_px, tile_px), Image.NEAREST)
                canvas.paste(t, (x * tile_px, y * tile_px + 28), t)

    # --- Pass 3: buildings (composite exterior + walls + floor + door) ---
    for b in world.buildings.values():
        fp = b.footprint if b.footprint else [(0, 0)]
        widx = _hash_to_int(b.id + "_wall", 20)
        fidx = _hash_to_int(b.id + "_floor", 20)
        eidx = _hash_to_int(b.id + "_ext", 14)
        ext_tile = _pick_house_exterior(b.type, eidx)
        wall_tile = _pick_wall_tile(b.type, widx)
        floor_tile = _pick_floor_tile(fidx)
        door_pos = DOOR_TILES["open"]

        max_fy = max(p[1] for p in fp) if fp else 0

        for fx, fy in fp:
            cx, cy = b.x + fx, b.y + fy
            # Exterior (top)
            t = _crop_tile(src, *ext_tile).resize((tile_px, tile_px), Image.NEAREST)
            canvas.paste(t, (cx * tile_px, cy * tile_px + 28), t)
            # Wall body
            t = _crop_tile(src, *wall_tile).resize((tile_px, tile_px), Image.NEAREST)
            canvas.paste(t, (cx * tile_px, cy * tile_px + 28), t)
            # Floor (bottom row)
            t = _crop_tile(src, *floor_tile).resize((tile_px, tile_px), Image.NEAREST)
            canvas.paste(t, (cx * tile_px, (cy + 1) * tile_px + 28), t)
            # Door (only on bottom-row tiles)
            if fy == max_fy:
                t = _crop_tile(src, *door_pos).resize((tile_px, tile_px), Image.NEAREST)
                canvas.paste(t, (cx * tile_px, (cy + 1) * tile_px + 28), t)

        # Building label
        try:
            draw.text((b.x * tile_px + 2, b.y * tile_px + 28 - 14),
                      b.name[:14], fill=(220, 200, 160, 255))
        except Exception:
            pass

    # --- Pass 4: NPCs as character sprites ---
    if show_npcs:
        for n in world.npcs.values():
            if not n.is_alive or n.death_year:
                continue
            if not n.status.household_id:
                continue
            house = world.buildings.get(n.status.household_id)
            if not house:
                continue
            # Use demographic tile if NPC has a special role, otherwise section E
            demo = _pick_demographic_tile(n)
            if demo:
                char_pos = demo
            else:
                char_pos = _pick_npc_tile(n)
            t = _crop_tile(src, *char_pos).resize((tile_px, tile_px), Image.NEAREST)
            offset_x = (_hash_to_int(n.id + "_x", 7) - 3) * (tile_px // 8)
            offset_y = (_hash_to_int(n.id + "_y", 5) - 2) * (tile_px // 8)
            cx = house.x * tile_px + offset_x
            cy = house.y * tile_px + 28 + offset_y
            canvas.paste(t, (cx, cy), t)

    # --- Pass 5: items as small icons ---
    if show_items:
        for item in world.items.values():
            if not item.building_id:
                continue
            b = world.buildings.get(item.building_id)
            if not b:
                continue
            # Map item.type.value to a tile coord
            type_name = item.type.value if hasattr(item.type, "value") else str(item.type)
            item_pos = ITEM_TILES.get(type_name, (0, 16))
            t = _crop_tile(src, *item_pos).resize((tile_px // 2, tile_px // 2), Image.NEAREST)
            ox = (_hash_to_int(item.id + "_ox", 9) - 4) * 4
            oy = (_hash_to_int(item.id + "_oy", 7) - 3) * 4
            canvas.paste(t, (b.x * tile_px + ox, b.y * tile_px + 28 + oy), t)

    # --- Title bar ---
    try:
        draw.rectangle([0, 0, w_px, 28], fill=(30, 20, 14, 255))
        draw.text((4, 6),
                  f"{world.name} — Year {world.year} — pop {world.living_count()}",
                  fill=(220, 200, 160, 255))
    except Exception:
        pass

    canvas.save(out_path)
    return out_path


def render_building_interior(world: World, building_id: str, out_path: str,
                              scale: int = 4) -> str:
    """Render the inside of a single building."""
    src = _load_onebit()
    b = world.buildings.get(building_id)
    if not b:
        raise ValueError(f"Building {building_id} not found")
    tile_px = TILE_SIZE * scale
    interior_w, interior_h = 8, 6
    w_px = interior_w * tile_px
    h_px = interior_h * tile_px
    canvas = Image.new("RGBA", (w_px, h_px + 28), (10, 8, 6, 255))
    draw = ImageDraw.Draw(canvas)

    # --- Floor (wood panels) ---
    for y in range(interior_h):
        for x in range(interior_w):
            idx = (x + y * 3) % len(INTERIOR_FLOOR_TILES)
            t = _crop_tile(src, *INTERIOR_FLOOR_TILES[idx]).resize(
                (tile_px, tile_px), Image.NEAREST)
            canvas.paste(t, (x * tile_px, y * tile_px + 28), t)

    # --- Walls around the edge ---
    wall_pos = _pick_wall_tile(b.type, _hash_to_int(b.id + "_w", 20))
    wall_tile = _crop_tile(src, *wall_pos).resize((tile_px, tile_px), Image.NEAREST)
    for x in range(interior_w):
        canvas.paste(wall_tile, (x * tile_px, 28), wall_tile)
    for y in range(1, interior_h):
        canvas.paste(wall_tile, (0, y * tile_px + 28), wall_tile)
        canvas.paste(wall_tile,
                     ((interior_w - 1) * tile_px, y * tile_px + 28), wall_tile)

    # --- Door (bottom center) ---
    door_tile = _crop_tile(src, *DOOR_TILES["open"]).resize(
        (tile_px, tile_px), Image.NEAREST)
    canvas.paste(door_tile,
                 ((interior_w // 2) * tile_px, (interior_h - 1) * tile_px + 28),
                 door_tile)

    # --- Furniture based on building type ---
    furniture_map = {
        BuildingType.TAVERN:   [("table_round", 1, 1), ("table_round", 5, 1),
                                ("stool", 2, 1), ("stool", 4, 1),
                                ("stool", 6, 1), ("fireplace", 1, 3)],
        BuildingType.SMITHY:   [("anvil", 3, 2), ("workbench", 5, 2),
                                ("stove", 1, 1)],
        BuildingType.CHURCH:   [("altar", 3, 1), ("column", 1, 1),
                                ("column", 5, 1), ("stool", 2, 3),
                                ("stool", 4, 3)],
        BuildingType.MILL:     [("workbench", 1, 1), ("table_square", 5, 1)],
        BuildingType.MARKET:   [("table_round", 1, 1), ("table_round", 3, 1),
                                ("table_round", 5, 1), ("basket", 1, 3)],
        BuildingType.GRANARY:  [("basket", 1, 1), ("basket", 2, 1),
                                ("basket", 5, 1)],
        BuildingType.BARN:     [("basket", 1, 1), ("fence", 5, 1)],
        BuildingType.HOUSE:    [("table_square", 1, 1), ("bed", 5, 1),
                                ("stool", 3, 3)],
    }
    for name, gx, gy in furniture_map.get(b.type, []):
        ftile = _crop_tile(src, *FURNITURE_TILES[name]).resize(
            (tile_px, tile_px), Image.NEAREST)
        canvas.paste(ftile, (gx * tile_px, gy * tile_px + 28), ftile)

    # --- Occupants ---
    occupants = [n for n in world.npcs.values()
                 if n.is_alive and not n.death_year
                 and n.status.household_id == building_id]
    for i, n in enumerate(occupants[:8]):
        char_pos = _pick_npc_tile(n)
        t = _crop_tile(src, *char_pos).resize(
            (tile_px, tile_px), Image.NEAREST)
        gx = 1 + (i % 6)
        gy = 2 + (i // 6)
        canvas.paste(t, (gx * tile_px, gy * tile_px + 28), t)

    # --- Items in the building ---
    items_here = [it for it in world.items.values() if it.building_id == building_id][:10]
    for i, item in enumerate(items_here):
        type_name = item.type.value if hasattr(item.type, "value") else str(item.type)
        item_pos = ITEM_TILES.get(type_name, (0, 16))
        t = _crop_tile(src, *item_pos).resize(
            (tile_px // 2, tile_px // 2), Image.NEAREST)
        gx = 1 + (i % 6)
        gy = 4 + (i // 6)
        if gy < interior_h - 1:
            canvas.paste(t, (gx * tile_px + 4, gy * tile_px + 28 + 4), t)

    # --- Title bar ---
    try:
        draw.rectangle([0, 0, w_px, 28], fill=(30, 20, 14, 255))
        draw.text((4, 6), f"{b.name} ({b.type.value})",
                  fill=(220, 200, 160, 255))
    except Exception:
        pass

    canvas.save(out_path)
    return out_path


def render_portrait(npc: NPC, out_path: str) -> str:
    """Render an NPC's portrait — a close-up of their character sprite."""
    src = _load_onebit()
    demo = _pick_demographic_tile(npc)
    if demo:
        char_pos = demo
    else:
        char_pos = _pick_npc_tile(npc)
    t = _crop_tile(src, *char_pos)
    t = t.resize((TILE_SIZE * 8, TILE_SIZE * 8), Image.NEAREST)
    t.save(out_path)
    return out_path


def render_scene_visual(scene, out_path: str, world: World = None) -> str:
    """Render a Scene as a single PNG: title bar, body text, choice list."""
    src = _load_onebit()
    width, height = 640, 400
    canvas = Image.new("RGBA", (width, height), (20, 18, 16, 255))
    draw = ImageDraw.Draw(canvas)

    # Decorative top + bottom border
    border = _crop_tile(src, 0, 0).resize((16, 16), Image.NEAREST)
    for x in range(0, width, 16):
        canvas.paste(border, (x, 0), border)
        canvas.paste(border, (x, height - 16), border)

    # Title bar
    draw.rectangle([0, 16, width, 56], fill=(60, 30, 20, 255))
    draw.text((8, 24), f"Y{scene.year} — {scene.title}", fill=(220, 200, 160, 255))
    draw.text((8, 60), f"@ {scene.location}", fill=(160, 140, 110, 255))

    # Body word wrap
    body = scene.body
    lines = []
    words = body.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > 80:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)

    y = 84
    for ln in lines[:18]:
        draw.text((8, y), ln, fill=(200, 190, 170, 255))
        y += 14

    # Choices
    draw.rectangle([0, height - 100, width, height - 16], fill=(40, 25, 18, 255))
    draw.text((8, height - 96), "Choices:", fill=(200, 170, 100, 255))
    cy = height - 78
    for i, c in enumerate(scene.choices, 1):
        color = (240, 220, 180, 255) if i == 1 else (200, 180, 140, 255)
        draw.text((8, cy), f"[{i}] {c.label[:70]}", fill=color)
        cy += 16

    canvas.save(out_path)
    return out_path


# ============================================================
# Dungeon scene renderer
# ============================================================
DUNGEON_WALL = (2, 2)         # gray_stone walls (sec A r2)
DUNGEON_FLOOR = (0, 10)       # brown terrain / dirt (sec A r10)
DUNGEON_ENEMY_TILES = [
    (64, 14),  # skeleton
    (65, 15),  # skeleton warrior
    (64, 16),  # zombie
    (64, 17),  # demon knight
    (64, 18),  # demon dragon
    (64, 19),  # demon lord
    (64, 20),  # demon fiend
]
DUNGEON_TREASURE = (8, 15)    # gem (sec A r15)


def render_dungeon(out_path: str, width: int = 16, height: int = 12,
                   scale: int = 4, seed: int = 1729) -> str:
    """Render a dungeon scene: stone walls, dirt floor, enemies, treasure."""
    import random as _rand
    src = _load_onebit()
    tile_px = TILE_SIZE * scale
    canvas = Image.new("RGBA", (width * tile_px, height * tile_px + 28), (8, 6, 4, 255))
    draw = ImageDraw.Draw(canvas)

    rng = _rand.Random(seed)
    wall = _crop_tile(src, *DUNGEON_WALL).resize((tile_px, tile_px), Image.NEAREST)
    floor = _crop_tile(src, *DUNGEON_FLOOR).resize((tile_px, tile_px), Image.NEAREST)
    treasure = _crop_tile(src, *DUNGEON_TREASURE).resize(
        (tile_px // 2, tile_px // 2), Image.NEAREST)

    # Fill floor
    for y in range(height):
        for x in range(width):
            canvas.paste(floor, (x * tile_px, y * tile_px + 28), floor)

    # Border walls
    for x in range(width):
        canvas.paste(wall, (x * tile_px, 28), wall)
        canvas.paste(wall, (x * tile_px, (height - 1) * tile_px + 28), wall)
    for y in range(height):
        canvas.paste(wall, (0, y * tile_px + 28), wall)
        canvas.paste(wall, ((width - 1) * tile_px, y * tile_px + 28), wall)

    # Inner walls (random rooms)
    n_walls = max(2, (width * height) // 30)
    for _ in range(n_walls):
        wx = rng.randint(2, width - 3)
        wy = rng.randint(2, height - 3)
        wlen = rng.randint(2, 4)
        for i in range(wlen):
            if 0 < wx + i < width - 1:
                canvas.paste(wall, ((wx + i) * tile_px, wy * tile_px + 28), wall)

    # Enemies
    enemies = []
    for _ in range(max(3, (width * height) // 40)):
        ex = rng.randint(1, width - 2)
        ey = rng.randint(1, height - 2)
        if any(abs(ex - x) < 2 and abs(ey - y) < 2 for x, y in enemies):
            continue
        enemies.append((ex, ey))
        etile = _crop_tile(src, *rng.choice(DUNGEON_ENEMY_TILES)).resize(
            (tile_px, tile_px), Image.NEAREST)
        canvas.paste(etile, (ex * tile_px, ey * tile_px + 28), etile)

    # Treasure in center-ish
    tx = width // 2
    ty = height // 2
    canvas.paste(treasure,
                 (tx * tile_px + tile_px // 4, ty * tile_px + 28 + tile_px // 4),
                 treasure)

    # Title bar
    try:
        draw.rectangle([0, 0, width * tile_px, 28], fill=(20, 10, 8, 255))
        draw.text((4, 6), "Dungeon — Depth 1",
                  fill=(220, 180, 140, 255))
    except Exception:
        pass

    canvas.save(out_path)
    return out_path


# ============================================================
# Graveyard scene renderer
# ============================================================
GRAVE_SKELETON_TILES = [
    (64, 14),  # skeleton
    (65, 15),  # skeleton warrior
    (64, 16),  # zombie
]


def render_graveyard(out_path: str, width: int = 16, height: int = 12,
                     scale: int = 4, seed: int = 4242) -> str:
    """Render a graveyard scene: graves, scattered skeletons, eerie trees."""
    import random as _rand
    src = _load_onebit()
    tile_px = TILE_SIZE * scale
    canvas = Image.new("RGBA", (width * tile_px, height * tile_px + 28),
                       (10, 12, 8, 255))
    draw = ImageDraw.Draw(canvas)

    rng = _rand.Random(seed)

    # Ground: dark dirt
    floor = _crop_tile(src, 0, 10).resize((tile_px, tile_px), Image.NEAREST)
    for y in range(height):
        for x in range(width):
            canvas.paste(floor, (x * tile_px, y * tile_px + 28), floor)

    # Gravestones (use stone wall as base + cross markers)
    stone = _crop_tile(src, 2, 2).resize((tile_px // 2, tile_px // 2), Image.NEAREST)
    cross = _crop_tile(src, 0, 11).resize((tile_px // 2, tile_px // 2), Image.NEAREST)

    graves = []
    for _ in range(max(5, (width * height) // 18)):
        gx = rng.randint(1, width - 2)
        gy = rng.randint(1, height - 2)
        if any(abs(gx - x) < 2 and abs(gy - y) < 2 for x, y in graves):
            continue
        graves.append((gx, gy))
        canvas.paste(stone,
                     (gx * tile_px + tile_px // 4, gy * tile_px + 28 + tile_px // 4),
                     stone)
        canvas.paste(cross,
                     (gx * tile_px + tile_px // 4,
                      (gy - 1) * tile_px + 28 + tile_px // 4),
                     cross)

    # Skeletons (rising from graves)
    for i, (gx, gy) in enumerate(graves[:max(2, len(graves) // 3)]):
        stile = _crop_tile(src, *GRAVE_SKELETON_TILES[i % len(GRAVE_SKELETON_TILES)]
                           ).resize((tile_px, tile_px), Image.NEAREST)
        canvas.paste(stile,
                     ((gx + 1) * tile_px, gy * tile_px + 28),
                     stile)

    # Border: dark stone wall
    border = _crop_tile(src, 3, 3).resize((tile_px, tile_px), Image.NEAREST)
    for x in range(width):
        canvas.paste(border, (x * tile_px, 28), border)
        canvas.paste(border, (x * tile_px, (height - 1) * tile_px + 28), border)
    for y in range(height):
        canvas.paste(border, (0, y * tile_px + 28), border)
        canvas.paste(border, ((width - 1) * tile_px, y * tile_px + 28), border)

    # Title bar
    try:
        draw.rectangle([0, 0, width * tile_px, 28], fill=(14, 14, 14, 255))
        draw.text((4, 6), "Graveyard — Borough Resting Grounds",
                  fill=(200, 180, 160, 255))
    except Exception:
        pass

    canvas.save(out_path)
    return out_path
