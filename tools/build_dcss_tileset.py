#!/usr/bin/env python3
import os
from PIL import Image

dcss_root = "/home/command/Documents/Dungeon Crawl Stone Soup Full"

# Tile Map Grid: 8 columns x 4 rows, each cell 32x32 pixels = 256x128 image
TILE_SIZE = 32
GRID_W = 8
GRID_H = 4

atlas = Image.new("RGBA", (GRID_W * TILE_SIZE, GRID_H * TILE_SIZE), (0, 0, 0, 0))

def find_first(candidates):
    for rel_path in candidates:
        full_p = os.path.join(dcss_root, rel_path)
        if os.path.exists(full_p):
            return full_p
    return None

mapping = {
    # Terrains (Row 0)
    (0, 0): find_first(["dungeon/floor/grass/grass_0_new.png", "dungeon/floor/grass/grass1.png"]),
    (1, 0): find_first(["dungeon/floor/dirt_0_new.png", "dungeon/floor/dirt_1_new.png"]),
    (2, 0): find_first(["dungeon/floor/rect_gray_0_new.png", "dungeon/floor/mosaic_0.png"]),
    (3, 0): find_first(["dungeon/water/deep_water.png", "dungeon/water/shoals_shallow_water_0.png"]),
    (4, 0): find_first(["dungeon/floor/pebble_brown_0_new.png", "dungeon/floor/moss_0.png"]),

    # Buildings (Row 1)
    (0, 1): find_first(["dungeon/wall/brick_brown_7.png", "dungeon/wall/brick_brown_3.png"]),
    (1, 1): find_first(["dungeon/wall/stone_brick_5.png", "dungeon/wall/catacombs_11.png"]),
    (2, 1): find_first(["dungeon/shops/shop_food.png"]),
    (3, 1): find_first(["dungeon/shops/shop_weapon.png"]),
    (4, 1): find_first(["dungeon/shops/enter_shop.png"]),
    (5, 1): find_first(["dungeon/shops/shop_general.png"]),
    (6, 1): find_first(["dungeon/wall/sandstone_wall_5.png"]),

    # Actors & Selection (Row 2)
    (0, 2): find_first(["player/base/human_m.png", "player/base/human_f.png", "monster/human_monk_ghost.png"]),
    (1, 2): find_first(["misc/cursor.png"]),
}

for (gx, gy), path in mapping.items():
    if path and os.path.exists(path):
        img = Image.open(path).convert("RGBA")
        if img.size != (TILE_SIZE, TILE_SIZE):
            img = img.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.LANCZOS)
        atlas.paste(img, (gx * TILE_SIZE, gy * TILE_SIZE))
        print(f"Placed ({gx}, {gy}): {os.path.basename(path)}")
    else:
        print(f"WARNING: Missing tile for ({gx}, {gy})")

output_path = "/home/command/borough/assets/dcss_borough_tileset.png"
atlas.save(output_path)
print(f"DCSS 32x32 Tileset Atlas successfully saved to {output_path}")
