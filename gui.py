"""Borough — Pygame Graphical Tileset Application.

Uses Urizen Onebit v2.0 tileset (/home/command/Downloads/urizen_onebit_tileset__v2d0.png)
to render the live 64x64 world map, buildings, items, livestock, and character sprites.
"""
from __future__ import annotations

import os
import sys
import textwrap
import argparse
import random

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), "engine"))

from core.world import generate_world, World
from core.simulation import Simulation, DAYS_PER_YEAR
from core.chronicle import Chronicle
from core.scene import pick_scene_for_year
from core.player import spawn_player, on_player_death
from core.spectator import town_statistics
from core.persistence import save_world, load_world
from engine.render import (
    _pick_terrain_tile, _pick_wall_tile, _pick_house_exterior,
    _pick_floor_tile, _pick_npc_tile, TILE_SIZE, URIZEN_ONEBIT
)

TILE_SCALE = 2  # 32x32 pixels on screen per tile
TILE_DISPLAY_SIZE = TILE_SIZE * TILE_SCALE


class TileCache:
    def __init__(self):
        self.sheet = pygame.image.load(URIZEN_ONEBIT).convert_alpha()
        self.cache = {}

    def get_tile(self, col: int, row: int, scale: int = TILE_SCALE) -> pygame.Surface:
        key = (col, row, scale)
        if key in self.cache:
            return self.cache[key]

        x = col * TILE_SIZE
        y = row * TILE_SIZE
        # Clamp to sheet bounds
        x = min(x, self.sheet.get_width() - TILE_SIZE)
        y = min(y, self.sheet.get_height() - TILE_SIZE)

        sub = self.sheet.subsurface(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
        if scale != 1:
            sub = pygame.transform.scale(sub, (TILE_SIZE * scale, TILE_SIZE * scale))
        self.cache[key] = sub
        return sub


class BoroughGUI:
    def __init__(self, seed: str | None = None, save_path: str = "saves/quicksave.json"):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Borough — A Town That Does Not Need You")

        self.save_path = save_path
        if os.path.exists(save_path):
            try:
                self.world = load_world(save_path)
            except Exception:
                self.world = generate_world(seed=seed)
        else:
            self.world = generate_world(seed=seed)

        self.chronicle = Chronicle(self.world)
        self.sim = Simulation(self.world, seed=self.world.seed)

        if self.world.player_id and self.world.player_id in self.world.npcs:
            self.player = self.world.npcs[self.world.player_id]
        else:
            self.player = spawn_player(self.world)
            self.world.player_id = self.player.id

        # Display setup
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.tile_cache = TileCache()

        # Fonts
        self.font_title = pygame.font.SysFont("Helvetica", 22, bold=True)
        self.font_main = pygame.font.SysFont("Helvetica", 16)
        self.font_small = pygame.font.SysFont("Helvetica", 13)

        # Camera & State
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.current_scene = None
        self.active_overlay = "status"  # status, npcs, chronicle, scene
        self.selected_npc = None
        self.message_log = [
            f"Welcome to Borough ({self.world.name})!",
            f"You were born as {self.player.first_name} {self.player.family_name} in Year {self.player.birth_year}.",
        ]

    def log(self, msg: str):
        self.message_log.append(msg)
        if len(self.message_log) > 100:
            self.message_log.pop(0)

    def step_day(self):
        if self.player.death_year:
            self.log("You have died! Press [R] to reincarnate into a new life.")
            return

        self.sim.tick_day()

        if self.player.death_year:
            on_player_death(self.world, self.chronicle)
            age = self.player.death_year - self.player.birth_year
            self.log(f"*** YOU HAVE DIED at age {age} in Year {self.player.death_year}! ***")
            self.log("Press [R] to reincarnate in this village.")
            return

        if self.sim.day_in_year == 0:
            sc = pick_scene_for_year(self.world, self.player, self.chronicle)
            if sc:
                self.current_scene = sc
                self.active_overlay = "scene"
                self.log(f"Year {self.world.year}: {sc.title}")

    def step_year(self):
        if self.player.death_year:
            self.log("You have died! Press [R] to reincarnate into a new life.")
            return

        start_year = self.world.year
        for _ in range(DAYS_PER_YEAR):
            self.step_day()
            if self.player.death_year or self.current_scene:
                break

        if not self.current_scene and not self.player.death_year:
            self.log(f"Advanced from Year {start_year} to Year {self.world.year}.")

    def spawn_new_life(self):
        if not self.player.death_year:
            self.log("You are still alive! Reincarnation is only available upon death.")
            return
        self.player = spawn_player(self.world)
        self.world.player_id = self.player.id
        self.current_scene = None
        self.active_overlay = "status"
        self.log(f"Reincarnated as {self.player.first_name} {self.player.family_name} in Year {self.world.year}.")

    def draw_map(self, map_w: int, map_h: int):
        # Center camera on screen center
        start_tile_x = int(self.cam_x - (map_w / (2 * TILE_DISPLAY_SIZE))) - 1
        start_tile_y = int(self.cam_y - (map_h / (2 * TILE_DISPLAY_SIZE))) - 1
        end_tile_x = start_tile_x + int(map_w / TILE_DISPLAY_SIZE) + 3
        end_tile_y = start_tile_y + int(map_h / TILE_DISPLAY_SIZE) + 3

        start_tile_x = max(0, start_tile_x)
        start_tile_y = max(0, start_tile_y)
        end_tile_x = min(self.world.map_width, end_tile_x)
        end_tile_y = min(self.world.map_height, end_tile_y)

        center_screen_x = map_w // 2
        center_screen_y = map_h // 2

        # Pass 1: Terrain
        for ty in range(start_tile_y, end_tile_y):
            for tx in range(start_tile_x, end_tile_x):
                if ty < len(self.world.tiles) and tx < len(self.world.tiles[ty]):
                    tile = self.world.tiles[ty][tx]
                else:
                    tile = {"terrain": "void"}

                terrain = tile.get("terrain", "dirt")
                pos = _pick_terrain_tile(terrain, tx, ty)
                if pos:
                    surf = self.tile_cache.get_tile(pos[0], pos[1])
                    screen_x = center_screen_x + int((tx - self.cam_x) * TILE_DISPLAY_SIZE)
                    screen_y = center_screen_y + int((ty - self.cam_y) * TILE_DISPLAY_SIZE)
                    self.screen.blit(surf, (screen_x, screen_y))

        # Pass 2: Buildings
        for b in self.world.buildings.values():
            if not b.footprint:
                continue
            for f_x, f_y in b.footprint:
                world_x = b.x + f_x
                world_y = b.y + f_y
                if start_tile_x <= world_x <= end_tile_x and start_tile_y <= world_y <= end_tile_y:
                    pos = _pick_wall_tile(b.type, f_x + f_y)
                    surf = self.tile_cache.get_tile(pos[0], pos[1])
                    screen_x = center_screen_x + int((world_x - self.cam_x) * TILE_DISPLAY_SIZE)
                    screen_y = center_screen_y + int((world_y - self.cam_y) * TILE_DISPLAY_SIZE)
                    self.screen.blit(surf, (screen_x, screen_y))

        # Pass 3: NPCs
        for npc in self.world.living_npcs():
            # Assign deterministic tile position on map if not set
            tx = (hash(npc.id) * 17) % self.world.map_width
            ty = (hash(npc.id) * 31) % self.world.map_height
            if start_tile_x <= tx <= end_tile_x and start_tile_y <= ty <= end_tile_y:
                col, row = _pick_npc_tile(npc)
                surf = self.tile_cache.get_tile(col, row)
                screen_x = center_screen_x + int((tx - self.cam_x) * TILE_DISPLAY_SIZE)
                screen_y = center_screen_y + int((ty - self.cam_y) * TILE_DISPLAY_SIZE)
                self.screen.blit(surf, (screen_x, screen_y))

                # Highlight player
                if npc.is_player:
                    pygame.draw.rect(self.screen, (255, 215, 0), (screen_x, screen_y, TILE_DISPLAY_SIZE, TILE_DISPLAY_SIZE), 2)

    def draw_hud(self, sidebar_x: int, sidebar_w: int):
        # Draw Sidebar Background
        pygame.draw.rect(self.screen, (24, 20, 18), (sidebar_x, 0, sidebar_w, self.screen_height))
        pygame.draw.line(self.screen, (60, 50, 40), (sidebar_x, 0), (sidebar_x, self.screen_height), 2)

        # Header Info
        season = self.world.weather_state.current_season.value.capitalize() if self.world.weather_state else "Spring"
        weather = self.world.weather_state.current.value.capitalize() if self.world.weather_state else "Clear"
        rep_tier = self.world.reputation.town_tier().capitalize() if self.world.reputation else "Stranger"

        y = 15
        title_surf = self.font_title.render(self.world.name.upper(), True, (230, 200, 150))
        self.screen.blit(title_surf, (sidebar_x + 15, y))
        y += 30

        time_surf = self.font_main.render(f"Year {self.world.year} (Day {self.sim.day_in_year+1}/360)", True, (200, 200, 200))
        self.screen.blit(time_surf, (sidebar_x + 15, y))
        y += 22

        env_surf = self.font_small.render(f"Season: {season} ({weather}) | Rep: {rep_tier}", True, (160, 160, 160))
        self.screen.blit(env_surf, (sidebar_x + 15, y))
        y += 30

        pygame.draw.line(self.screen, (60, 50, 40), (sidebar_x + 15, y), (sidebar_x + sidebar_w - 15, y), 1)
        y += 15

        # Player Stats Box
        p = self.player
        age = self.world.year - p.birth_year if not p.death_year else (p.death_year - p.birth_year)
        p_color = (220, 70, 70) if p.death_year else (100, 220, 100)
        p_status = f"DEAD (d. Y{p.death_year})" if p.death_year else "ALIVE"

        name_surf = self.font_main.render(f"Player: {p.first_name} {p.family_name}", True, (240, 240, 240))
        self.screen.blit(name_surf, (sidebar_x + 15, y))
        y += 22

        status_surf = self.font_small.render(f"Status: {p_status} | Age: {age}", True, p_color)
        self.screen.blit(status_surf, (sidebar_x + 15, y))
        y += 20

        stats_surf = self.font_small.render(f"Job: {p.status.occupation} | Coins: {p.status.coins}", True, (180, 180, 180))
        self.screen.blit(stats_surf, (sidebar_x + 15, y))
        y += 20

        vitals_surf = self.font_small.render(f"Health: {p.body.health}/100 | Hunger: {p.body.hunger}/100", True, (180, 180, 180))
        self.screen.blit(vitals_surf, (sidebar_x + 15, y))
        y += 30

        pygame.draw.line(self.screen, (60, 50, 40), (sidebar_x + 15, y), (sidebar_x + sidebar_w - 15, y), 1)
        y += 15

        # Controls List
        controls = [
            "[Space] Step 1 Day",
            "[Y] Step 1 Year",
            "[S] Status Panel",
            "[N] NPCs Directory",
            "[C] Town Chronicle",
            "[R] Reincarnate",
            "[Q / Esc] Quit & Save",
        ]
        ctrl_title = self.font_main.render("CONTROLS", True, (200, 180, 140))
        self.screen.blit(ctrl_title, (sidebar_x + 15, y))
        y += 24

        for ctrl in controls:
            c_surf = self.font_small.render(ctrl, True, (140, 140, 140))
            self.screen.blit(c_surf, (sidebar_x + 15, y))
            y += 18

        y += 15
        pygame.draw.line(self.screen, (60, 50, 40), (sidebar_x + 15, y), (sidebar_x + sidebar_w - 15, y), 1)
        y += 15

        # Message Log
        log_title = self.font_main.render("LOG", True, (200, 180, 140))
        self.screen.blit(log_title, (sidebar_x + 15, y))
        y += 24

        max_log_lines = max(1, (self.screen_height - y - 15) // 18)
        for msg in self.message_log[-max_log_lines:]:
            m_surf = self.font_small.render(msg[:45], True, (160, 160, 160))
            self.screen.blit(m_surf, (sidebar_x + 15, y))
            y += 18

    def draw_event_scene_dialog(self):
        if not self.current_scene:
            return

        box_w = 600
        box_h = 400
        box_x = (self.screen_width - box_w) // 2
        box_y = (self.screen_height - box_h) // 2

        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Dialog Box
        pygame.draw.rect(self.screen, (30, 26, 22), (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, (200, 160, 100), (box_x, box_y, box_w, box_h), 2)

        # Title
        t_surf = self.font_title.render(f"EVENT: {self.current_scene.title.upper()}", True, (240, 200, 120))
        self.screen.blit(t_surf, (box_x + 20, box_y + 20))

        # Description
        y = box_y + 60
        for paragraph in self.current_scene.description.split("\n"):
            lines = textwrap.wrap(paragraph, width=65)
            for l in lines:
                l_surf = self.font_main.render(l, True, (220, 220, 220))
                self.screen.blit(l_surf, (box_x + 20, y))
                y += 22

        y += 20
        c_title = self.font_main.render("Choices:", True, (200, 180, 140))
        self.screen.blit(c_title, (box_x + 20, y))
        y += 25

        for idx, choice in enumerate(self.current_scene.choices, 1):
            ch_str = f"[{idx}] {choice.text}"
            ch_surf = self.font_main.render(ch_str, True, (100, 220, 255))
            self.screen.blit(ch_surf, (box_x + 30, y))
            y += 24

    def run(self):
        running = True
        while running:
            self.clock.tick(30)

            # Camera follows player position on map
            self.cam_x = 32.0
            self.cam_y = 32.0

            map_w = self.screen_width - 340
            map_h = self.screen_height

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    save_world(self.world, self.save_path)
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        save_world(self.world, self.save_path)
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_d):
                        self.step_day()
                    elif event.key == pygame.K_y:
                        self.step_year()
                    elif event.key == pygame.K_r:
                        self.spawn_new_life()
                    elif pygame.K_1 <= event.key <= pygame.K_9 and self.current_scene:
                        choice_idx = event.key - pygame.K_1
                        if choice_idx < len(self.current_scene.choices):
                            self.current_scene.apply_choice(choice_idx, self.world, self.chronicle)
                            self.log(f"Choice #{choice_idx+1}: {self.current_scene.choices[choice_idx].text}")
                            self.current_scene = None

            self.screen.fill((10, 8, 6))
            self.draw_map(map_w, map_h)
            self.draw_hud(map_w, 340)

            if self.current_scene:
                self.draw_event_scene_dialog()

            pygame.display.flip()

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Borough Graphical Pygame Launcher")
    parser.add_argument("--seed", type=str, default=None, help="World generation seed")
    args = parser.parse_args()

    gui = BoroughGUI(seed=args.seed)
    gui.run()


if __name__ == "__main__":
    main()
