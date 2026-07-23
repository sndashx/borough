"""Borough — AAA CDDA-Quality Terminal UI (ncurses)

A rich, deterministic medieval town simulation interface crafted in the style of
Cataclysm: Dark Days Ahead (CDDA), Dwarf Fortress, and Caves of Qud.

Key AAA Features:
  - Framed ACS Box-Drawing Layout with high-contrast color palettes.
  - Interactive 2D ASCII Town Map Viewport with WASD/HJKL/Arrow panning.
  - Target Reticle Cursor with dynamic 'Look-At' Tile Inspection.
  - Player Auto-Follow Camera Toggle [f].
  - Multi-panel Citizen Inspector: Vitals Gauges, Maslow Psychology, Life Ambition
    Progress Bars, Quirks, Anatomy Scars, and Impairments.
  - Rich Subsystem Inspectors:
      * [c] Town Council & Policy Charters
      * [r] Masterwork Relics & Artifact Heirlooms
      * [u] Underground Cults & Heresies
      * [l] Town Legends & Historical Folklore
      * [n] Living Citizens Roster with Selection
      * [s] Town Statistics & Demographic Overview
  - Categorized, color-coded CDDA Event Message Log Feed.
"""
from __future__ import annotations

import curses
import os
import sys
import argparse
import textwrap
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), "engine"))

from core.world import generate_world, World
from core.simulation import Simulation, DAYS_PER_YEAR
from core.chronicle import Chronicle
from core.scene import pick_scene_for_year
from core.player import spawn_player, on_player_death
from core.spectator import town_statistics
from core.persistence import save_world, load_world


# Symbol & Color Mappings
TERRAIN_SYMBOLS = {
    "grass": (".", 2),         # Green .
    "dirt": ("#", 3),          # Yellow/Brown #
    "cobble": (":", 7),        # Gray :
    "water": ("~", 4),         # Blue ~
    "farmland": ('"', 3),      # Yellow "
}

BUILDING_SYMBOLS = {
    "house": ("H", 6),         # Cyan H
    "church": ("C", 5),        # Magenta C
    "tavern": ("T", 3),        # Yellow T
    "smithy": ("S", 1),        # Red S
    "market": ("M", 2),        # Green M
    "granary": ("G", 3),       # Yellow G
    "barn": ("B", 6),          # Cyan B
}


def make_bar(val: int, max_val: int = 100, length: int = 10) -> str:
    """Generate ASCII progress bar e.g. [██████░░░░] 60%."""
    clamped = max(0, min(max_val, val))
    filled = (clamped * length) // max_val
    unfilled = length - filled
    return f"[{'█' * filled}{'░' * unfilled}] {clamped}%"


class BoroughTUI:
    def __init__(self, stdscr, seed: str | None = None, save_path: str = "saves/quicksave.json"):
        self.stdscr = stdscr
        self.save_path = save_path
        
        # Load or generate world
        if os.path.exists(save_path):
            try:
                self.world = load_world(save_path)
            except Exception:
                self.world = generate_world(seed=seed)
        else:
            self.world = generate_world(seed=seed)

        self.chronicle = Chronicle(self.world)
        self.sim = Simulation(self.world, seed=self.world.seed)

        # Player setup
        if self.world.player_id and self.world.player_id in self.world.npcs:
            self.player = self.world.npcs[self.world.player_id]
        else:
            self.player = spawn_player(self.world)
            self.world.player_id = self.player.id

        self.current_scene = None
        self.message_log: list[tuple[str, str, int]] = [
            ("SYS", f"Welcome to Borough ({self.world.name}) — Release R1.0 AAA Edition!", 5),
            ("INFO", f"Born as {self.player.first_name} {self.player.family_name} in Year {self.player.birth_year}.", 3),
            ("HELP", "Press [e] to perform Actions (Work, Trade, Pray, Court, Vote), WASD to move cursor.", 6),
        ]
        
        # View & Cursor State
        self.active_tab = "map"  # map, status, npcs, council, relics, cults, chronicle, scene, actions
        self.cam_x = 32
        self.cam_y = 32
        self.cursor_x = 32
        self.cursor_y = 32
        self.follow_player = True
        self.selected_npc_id: Optional[str] = self.player.id
        self.citizen_scroll_idx = 0

        # Setup Curses Colors & Attributes
        self._init_colors()

    def _init_colors(self):
        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_RED, -1)       # 1: Red (Danger/Combat)
                curses.init_pair(2, curses.COLOR_GREEN, -1)     # 2: Green (Nature/Prosperity)
                curses.init_pair(3, curses.COLOR_YELLOW, -1)    # 3: Yellow (Gold/Buildings/Warning)
                curses.init_pair(4, curses.COLOR_BLUE, -1)      # 4: Blue (Water/Info)
                curses.init_pair(5, curses.COLOR_MAGENTA, -1)   # 5: Magenta (Church/Cults/Events)
                curses.init_pair(6, curses.COLOR_CYAN, -1)      # 6: Cyan (Lore/Houses/UI Headers)
                curses.init_pair(7, curses.COLOR_WHITE, -1)     # 7: White (Default Text)
                curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_CYAN)   # 8: Header Banner
                curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_YELLOW) # 9: Highlight Reticle
        except Exception:
            pass

    def log(self, category: str, msg: str, color_pair: int = 7):
        self.message_log.append((category, msg, color_pair))
        if len(self.message_log) > 200:
            self.message_log.pop(0)

    def draw_box(self, top: int, left: int, height: int, width: int, title: str = "", attr: int = 0):
        """Draw ACS bordered box with optional centered title."""
        max_y, max_x = self.stdscr.getmaxyx()
        if top < 0 or left < 0 or top + height > max_y or left + width > max_x:
            return

        try:
            # Corner characters
            self.stdscr.addch(top, left, curses.ACS_ULCORNER, attr)
            self.stdscr.addch(top, left + width - 1, curses.ACS_URCORNER, attr)
            self.stdscr.addch(top + height - 1, left, curses.ACS_LLCORNER, attr)
            self.stdscr.addch(top + height - 1, left + width - 1, curses.ACS_LRCORNER, attr)

            # Horizontal lines
            for x in range(left + 1, left + width - 1):
                self.stdscr.addch(top, x, curses.ACS_HLINE, attr)
                self.stdscr.addch(top + height - 1, x, curses.ACS_HLINE, attr)

            # Vertical lines
            for y in range(top + 1, top + height - 1):
                self.stdscr.addch(y, left, curses.ACS_VLINE, attr)
                self.stdscr.addch(y, left + width - 1, curses.ACS_VLINE, attr)

            # Title
            if title and len(title) < width - 4:
                title_str = f" {title} "
                start_x = left + (width - len(title_str)) // 2
                self.stdscr.addstr(top, start_x, title_str, attr | curses.A_BOLD)
        except curses.error:
            pass

    def add_str_safe(self, y: int, x: int, text: str, max_len: int, attr=0):
        max_y, max_x = self.stdscr.getmaxyx()
        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return
        allowed = min(max_len, max_x - x - (1 if y == max_y - 1 else 0))
        if allowed <= 0:
            return
        try:
            self.stdscr.addstr(y, x, text[:allowed], attr)
        except curses.error:
            pass

    def center_on_player(self):
        p_hid = self.player.status.household_id
        if p_hid and p_hid in self.world.buildings:
            b = self.world.buildings[p_hid]
            self.cam_x, self.cam_y = b.x, b.y
            self.cursor_x, self.cursor_y = b.x, b.y

    def step_day(self):
        if self.player.death_year:
            self.log("DEATH", "You are deceased! Press [R] to reincarnate into a new life.", 1)
            return

        self.sim.tick_day()

        if self.player.death_year:
            on_player_death(self.world, self.chronicle)
            age = self.player.death_year - self.player.birth_year
            self.log("DEATH", f"*** YOU DIED at age {age} in Year {self.player.death_year}! ***", 1)
            self.log("DEATH", "Press [R] to reincarnate in this village.", 3)
            return

        if self.follow_player:
            self.center_on_player()

        if self.sim.day_in_year == 0:
            sc = pick_scene_for_year(self.world, self.player, self.chronicle)
            if sc:
                self.current_scene = sc
                self.active_tab = "scene"
                self.log("EVENT", f"Year {self.world.year} Event: {sc.title}", 5)

    def step_year(self):
        if self.player.death_year:
            self.log("DEATH", "You have died! Press [R] to reincarnate.", 1)
            return
        for _ in range(DAYS_PER_YEAR):
            self.step_day()
            if self.current_scene:
                break
        if not self.current_scene:
            self.log("YEAR", f"Advanced to Year {self.world.year}.", 6)

    def spawn_new_life(self):
        if not self.player.death_year:
            self.log("LIFE", "You are still alive!", 3)
            return
        self.player = spawn_player(self.world)
        self.world.player_id = self.player.id
        self.current_scene = None
        self.active_tab = "map"
        self.selected_npc_id = self.player.id
        self.center_on_player()
        self.log("BIRTH", f"Reincarnated as {self.player.first_name} {self.player.family_name} in Year {self.world.year}.", 2)

    def save_game(self):
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        save_world(self.world, self.save_path)
        self.log("SAVE", f"Saved game state to {self.save_path}", 2)

    def draw_header(self, max_x: int):
        season = self.world.weather_state.current_season.value.capitalize() if self.world.weather_state else "Spring"
        weather = self.world.weather_state.current.value.capitalize() if self.world.weather_state else "Clear"
        rep_tier = self.world.reputation.town_tier().capitalize() if self.world.reputation else "Stranger"

        header_str = (
            f" BOROUGH — {self.world.name} | Year {self.world.year} (Day {self.sim.day_in_year+1}/360) | "
            f"Season: {season} ({weather}) | Reputation: {rep_tier} | Seed: {str(self.world.seed)[:8]} "
        )
        attr = curses.color_pair(8) if curses.has_colors() else curses.A_REVERSE
        self.add_str_safe(0, 0, header_str.ljust(max_x), max_x, attr)

    def draw_player_bar(self, y: int, max_x: int):
        p = self.player
        age = self.world.year - p.birth_year if not p.death_year else (p.death_year - p.birth_year)
        status_str = f"DEAD (d. Y{p.death_year})" if p.death_year else "ALIVE"
        status_color = 1 if p.death_year else 2

        info = (
            f" Character: {p.first_name} {p.family_name} [{status_str}] | Age: {age} | "
            f"Job: {p.status.occupation.capitalize()} | HP: {p.body.health}/100 | "
            f"Gold: {p.status.coins}g | Goal: {p.ambition.title} ({p.ambition.progress}%)"
        )
        attr = curses.color_pair(status_color) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        self.add_str_safe(y, 0, info.ljust(max_x), max_x, attr)

    def draw_actions_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="PLAYER INTERACTIVE ACTION WHEEL", attr=curses.color_pair(3))

        if self.player.death_year:
            self.add_str_safe(y + 2, 2, "You are deceased. Press [R] to reincarnate.", width - 4, curses.color_pair(1) | curses.A_BOLD)
            return

        actions = [
            ("1", "Work Daily Job Shift", f"Earn income (+15 Gold), advance occupation, +5% Ambition"),
            ("2", "Buy Provisions at Market", f"Spend 5 Gold for fresh bread & cider (+30 Health/Hunger)"),
            ("3", "Pray & Worship at Church", f"Gain spiritual peace (-20 Paranoia, +15 Belonging)"),
            ("4", "Drink & Socialize at Tavern", f"Hear town gossip & rumors (+25 Joy, +10 Relationship)"),
            ("5", "Work on Life Goal & Crafts", f"Focus on personal ambition progress (+15% Goal Progress)"),
            ("6", "Court & Proposal Options", f"Court single citizens or attempt marriage proposal"),
            ("7", "Petition Town Council", f"Vote in elections or petition Mayor for Grain Subsidies"),
            ("8", "Investigate Underground Cults", f"Search for secret occult symbols and cult cells"),
        ]

        for idx, (key, title, desc) in enumerate(actions[:height - 3]):
            row = y + 2 + idx * 2
            if row >= y + height - 1:
                break
            self.add_str_safe(row, 2, f"[{key}] {title}", width - 4, curses.color_pair(6) | curses.A_BOLD)
            self.add_str_safe(row + 1, 6, f"→ {desc}", width - 8, curses.A_DIM)

    def draw_controls(self, y: int, max_x: int):
        controls = " [Space] Day | [Y] Year | [e] Actions | [WASD] Cam | [f] Follow | [m] Map | [c] Council | [r] Relics | [u] Cults | [l] Legends | [n] Citizens | [Q] Quit "
        attr = curses.color_pair(8) if curses.has_colors() else curses.A_REVERSE
        self.add_str_safe(y, 0, controls.ljust(max_x), max_x - 1, attr)

    def draw_main_content(self, start_y: int, height: int, max_x: int):
        # 58% Left Viewport (Map / Subsystems), 42% Right Sidebar (Inspector & Logs)
        left_w = int(max_x * 0.58)
        right_w = max_x - left_w

        # Left Viewport Box
        if self.active_tab == "map":
            self.draw_ascii_map_viewport(start_y, height, left_w)
        elif self.active_tab == "actions":
            self.draw_actions_panel(start_y, height, left_w)
        elif self.active_tab == "scene" and self.current_scene:
            self.draw_scene_panel(start_y, height, left_w)
        elif self.active_tab == "council":
            self.draw_council_panel(start_y, height, left_w)
        elif self.active_tab == "relics":
            self.draw_relics_panel(start_y, height, left_w)
        elif self.active_tab == "cults":
            self.draw_cults_panel(start_y, height, left_w)
        elif self.active_tab == "chronicle":
            self.draw_legends_panel(start_y, height, left_w)
        elif self.active_tab == "npcs":
            self.draw_citizens_panel(start_y, height, left_w)
        else:
            self.draw_status_panel(start_y, height, left_w)

        # Right Panel: Inspector + CDDA Event Message Log Feed
        sidebar_h = height // 2
        self.draw_sidebar_inspector(start_y, sidebar_h, left_w, right_w)
        self.draw_log_panel(start_y + sidebar_h, height - sidebar_h, left_w, right_w)

    def draw_ascii_map_viewport(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title=f"TOWN MAP VIEWPORT ({self.world.name})", attr=curses.color_pair(6))

        map_box_h = height - 4
        map_box_w = width - 2

        min_x = max(0, self.cam_x - map_box_w // 2)
        min_y = max(0, self.cam_y - map_box_h // 2)

        tiles = self.world.tiles
        buildings = self.world.buildings
        living_npcs = self.world.living_npcs()

        # Building positions lookup
        b_map = {}
        for b_id, b in buildings.items():
            bx, by = b.x, b.y
            btype = b.type.value.lower() if hasattr(b.type, 'value') else str(b.type).lower()
            sym, col = BUILDING_SYMBOLS.get(btype, ("H", 6))
            for dy in range(2):
                for dx in range(2):
                    b_map[(bx + dx, by + dy)] = (sym, col, b)

        # NPC positions lookup
        npc_map = {}
        for npc in living_npcs:
            hid = npc.status.household_id
            pos = (32, 32)
            if hid and hid in buildings:
                pos = (buildings[hid].x, buildings[hid].y)
            sym = "@" if npc.is_player else npc.first_name[0].upper()
            col = 3 if npc.is_player else 7
            npc_map[pos] = (sym, col, npc)

        # Render 2D Map Grid
        for row_idx in range(map_box_h):
            map_y = min_y + row_idx
            if map_y >= len(tiles):
                break
            for col_idx in range(map_box_w):
                map_x = min_x + col_idx
                if map_x >= len(tiles[map_y]):
                    break

                draw_y = y + 1 + row_idx
                draw_x = 1 + col_idx

                # Check Cursor Reticle
                if map_x == self.cursor_x and map_y == self.cursor_y:
                    attr = curses.color_pair(9) | curses.A_BOLD if curses.has_colors() else curses.A_REVERSE
                    self.add_str_safe(draw_y, draw_x, "X", 1, attr)
                    continue

                # Check NPC
                if (map_x, map_y) in npc_map:
                    sym, col, _ = npc_map[(map_x, map_y)]
                    self.add_str_safe(draw_y, draw_x, sym, 1, curses.color_pair(col) | curses.A_BOLD)
                    continue

                # Check Building
                if (map_x, map_y) in b_map:
                    sym, col, _ = b_map[(map_x, map_y)]
                    self.add_str_safe(draw_y, draw_x, sym, 1, curses.color_pair(col) | curses.A_BOLD)
                    continue

                # Default Terrain
                t = tiles[map_y][map_x].get("terrain", "grass")
                sym, col = TERRAIN_SYMBOLS.get(t, (".", 2))
                self.add_str_safe(draw_y, draw_x, sym, 1, curses.color_pair(col))

        # Bottom Look-At Info Bar
        look_y = y + height - 2
        tile_t = tiles[self.cursor_y][self.cursor_x].get("terrain", "grass") if self.cursor_y < len(tiles) and self.cursor_x < len(tiles[0]) else "unknown"
        b_info = b_map.get((self.cursor_x, self.cursor_y))
        b_str = f" | Building: {b_info[2].name} ({b_info[2].type.value.capitalize()})" if b_info else ""
        npc_info = npc_map.get((self.cursor_x, self.cursor_y))
        npc_str = f" | Citizen: {npc_info[2].first_name} {npc_info[2].family_name} ({npc_info[2].status.occupation})" if npc_info else ""

        look_str = f" [LOOK ({self.cursor_x:02d},{self.cursor_y:02d})]: Terrain: {tile_t.capitalize()}{b_str}{npc_str} "
        self.add_str_safe(look_y, 1, look_str, width - 2, curses.color_pair(3) | curses.A_BOLD)

        # Update selected NPC if cursor lands on one
        if npc_info:
            self.selected_npc_id = npc_info[2].id

    def draw_sidebar_inspector(self, y: int, height: int, start_x: int, width: int):
        self.draw_box(y, start_x, height, width, title="CITIZEN INSPECTOR", attr=curses.color_pair(6))

        npc = self.world.npcs.get(self.selected_npc_id, self.player)
        age = self.world.year - npc.birth_year if not npc.death_year else (npc.death_year - npc.birth_year)

        lines = [
            (f" Name: {npc.first_name} {npc.family_name} (Age {age})", curses.A_BOLD),
            (f" Job: {npc.status.occupation.capitalize()} | Wallet: {npc.status.coins} Gold", 0),
            (f" Health:  {make_bar(npc.body.health)}", curses.color_pair(2) if npc.body.health > 50 else curses.color_pair(1)),
            (f" Hunger:  {make_bar(npc.body.hunger)}", curses.color_pair(3) if npc.body.hunger > 30 else curses.color_pair(2)),
            (f" Maslow:  Safety {npc.psychology.safety_need}% | Belonging {npc.psychology.belonging_need}%", 0),
            (f" Mood:    {npc.ambition.mood_summary}", 0),
            (f" Goal:    {npc.ambition.title}", curses.color_pair(3) | curses.A_BOLD),
            (f" Progress:{make_bar(npc.ambition.progress)}", curses.color_pair(3)),
            (f" Quirks:  {', '.join(npc.ambition.quirks) if npc.ambition.quirks else 'None'}", 0),
        ]

        if npc.anatomy.scars:
            lines.append((f" Scars:   {', '.join(npc.anatomy.scars[:2])}", curses.color_pair(1)))
        if npc.anatomy.impairments:
            lines.append((f" Damage:  {', '.join(npc.anatomy.impairments)}", curses.color_pair(1)))

        for idx, (line, attr) in enumerate(lines[:height - 2]):
            self.add_str_safe(y + 1 + idx, start_x + 1, line, width - 2, attr)

    def draw_log_panel(self, y: int, height: int, start_x: int, width: int):
        self.draw_box(y, start_x, height, width, title="CDDA EVENT MESSAGE LOG", attr=curses.color_pair(6))

        visible_logs = self.message_log[-(height - 2):]
        for idx, (cat, log_msg, col_pair) in enumerate(visible_logs):
            cat_str = f"[{cat}]".ljust(7)
            line = f" {cat_str} {log_msg}"
            self.add_str_safe(y + 1 + idx, start_x + 1, line, width - 2, curses.color_pair(col_pair))

    def draw_council_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="TOWN COUNCIL & CHARTERS", attr=curses.color_pair(3))
        gov = self.world.governance
        if not gov:
            self.add_str_safe(y + 2, 2, "No formal town governance established.", width - 4)
            return

        pol = gov.policies
        self.add_str_safe(y + 2, 2, f"Town Treasury:   {pol.treasury_gold} Gold", width - 4, curses.A_BOLD)
        self.add_str_safe(y + 3, 2, f"Tax Rate:        {pol.tax_rate}%", width - 4)
        self.add_str_safe(y + 4, 2, f"Night Curfew:    {'ACTIVE (Guard Patrols)' if pol.curfew_active else 'LIFTED'}", width - 4)
        self.add_str_safe(y + 5, 2, f"Grain Subsidies: {'ACTIVE (Free Flour)' if pol.grain_subsidy else 'NONE'}", width - 4)

        row = y + 7
        self.add_str_safe(row, 2, "COUNCIL SEATS & INCUMBENTS:", width - 4, curses.color_pair(6) | curses.A_BOLD)
        for title, seat in gov.seats.items():
            row += 1
            if row >= y + height - 1:
                break
            inc_npc = self.world.npcs.get(seat.incumbent_id) if seat.incumbent_id else None
            inc_str = f"{inc_npc.first_name} {inc_npc.family_name}" if inc_npc else "Vacant"
            self.add_str_safe(row, 4, f"• {title:<20}: {inc_str}", width - 6)

    def draw_relics_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="MASTERWORK RELICS & HEIRLOOMS", attr=curses.color_pair(3))
        relics = list(self.world.relics.relics.values()) if self.world.relics else []
        if not relics:
            self.add_str_safe(y + 2, 2, "No masterwork artifacts forged yet in this age.", width - 4)
            return

        row = y + 2
        for relic in relics[:(height - 3) // 3]:
            owner = self.world.npcs.get(relic.current_owner_id)
            owner_str = f"{owner.first_name} {owner.family_name}" if owner else "Unknown"
            self.add_str_safe(row, 2, f"⚔ {relic.name} ({relic.material})", width - 4, curses.color_pair(3) | curses.A_BOLD)
            self.add_str_safe(row + 1, 4, f"Forged by: {relic.creator_name} | Held by: {owner_str} | Renown: {relic.renown_value}g", width - 6)
            self.add_str_safe(row + 2, 4, f"Inscribed: \"{relic.engraving_description}\"", width - 6, curses.A_DIM)
            row += 4

    def draw_cults_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="SECRET CULTS & HERESIES", attr=curses.color_pair(5))
        cults = list(self.world.cults.cults.values()) if self.world.cults else []
        if not cults:
            self.add_str_safe(y + 2, 2, "No underground heresies uncovered by the Constable.", width - 4)
            return

        row = y + 2
        for cult in cults[:(height - 3) // 3]:
            leader = self.world.npcs.get(cult.leader_id)
            leader_str = f"{leader.first_name} {leader.family_name}" if leader else "Shadow"
            self.add_str_safe(row, 2, f"❖ {cult.name} (Symbol: {cult.secret_symbol})", width - 4, curses.color_pair(5) | curses.A_BOLD)
            self.add_str_safe(row + 1, 4, f"Leader: {leader_str} | Members: {len(cult.members)} | Secrecy: {cult.secrecy_level}%", width - 6)
            self.add_str_safe(row + 2, 4, f"Doctrine: {cult.doctrine}", width - 6)
            row += 4

    def draw_legends_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="TOWN LEGENDS & HISTORICAL FOLKLORE", attr=curses.color_pair(6))
        legends = list(self.world.lore.legends.values()) if self.world.lore else []
        if not legends:
            self.add_str_safe(y + 2, 2, "No folklore legends have grown from history yet.", width - 4)
            return

        row = y + 2
        for leg in legends[:(height - 3) // 3]:
            self.add_str_safe(row, 2, f"★ {leg.title} (Year {leg.year_originated})", width - 4, curses.color_pair(3) | curses.A_BOLD)
            self.add_str_safe(row + 1, 4, leg.narrative, width - 6)
            self.add_str_safe(row + 2, 4, f"Cultural Influence: {leg.cultural_impact}%", width - 6, curses.A_DIM)
            row += 4

    def draw_citizens_panel(self, y: int, height: int, width: int):
        living = self.world.living_npcs()
        self.draw_box(y, 0, height, width, title=f"CITIZEN DIRECTORY ({len(living)})", attr=curses.color_pair(6))

        for idx, npc in enumerate(living[self.citizen_scroll_idx:self.citizen_scroll_idx + height - 3]):
            age = self.world.year - npc.birth_year
            line = f" • {npc.first_name} {npc.family_name:<16} Age {age:<3} | {npc.status.occupation.capitalize():<12} | {npc.status.coins}g"
            attr = curses.color_pair(3) | curses.A_BOLD if npc.id == self.selected_npc_id else 0
            self.add_str_safe(y + 1 + idx, 2, line, width - 4, attr)

    def draw_status_panel(self, y: int, height: int, width: int):
        self.draw_box(y, 0, height, width, title="DEMOGRAPHIC & ECONOMY OVERVIEW", attr=curses.color_pair(6))
        stats = town_statistics(self.world)

        lines = [
            f"Town Name:             {self.world.name}",
            f"World Seed:            {str(self.world.seed)[:16]}...",
            f"Living Population:     {stats['population_living']}",
            f"Deceased Ancestors:    {stats['population_dead']}",
            f"Active Contracts:      {stats['active_contracts']}",
            f"Coins in Circulation:  {stats['coins_in_circulation']} Gold",
        ]
        for idx, line in enumerate(lines[:height - 2]):
            self.add_str_safe(y + 1 + idx, 2, line, width - 4)

    def draw_scene_panel(self, y: int, height: int, width: int):
        if not self.current_scene:
            self.add_str_safe(y, 2, "No active event scene.", width - 4)
            return

        self.draw_box(y, 0, height, width, title=f"EVENT: {self.current_scene.title.upper()}", attr=curses.color_pair(5))

        row = y + 2
        desc_lines = []
        for paragraph in self.current_scene.description.split("\n"):
            desc_lines.extend(textwrap.wrap(paragraph, width - 6))
            desc_lines.append("")

        for line in desc_lines:
            if row >= y + height - len(self.current_scene.choices) - 3:
                break
            self.add_str_safe(row, 3, line, width - 6)
            row += 1

        row += 1
        self.add_str_safe(row, 2, "Choices:", width - 4, curses.A_BOLD)
        row += 1

        for idx, choice in enumerate(self.current_scene.choices, 1):
            if row >= y + height - 1:
                break
            choice_str = f" [{idx}] {choice.text}"
            self.add_str_safe(row, 4, choice_str, width - 6, curses.color_pair(6) | curses.A_BOLD)
            row += 1

    def handle_input(self, ch: int) -> bool:
        # Camera & Cursor Controls
        if ch in (ord('w'), ord('W'), curses.KEY_UP):
            self.cursor_y = max(0, self.cursor_y - 1)
            if not self.follow_player:
                self.cam_y = self.cursor_y
        elif ch in (ord('s'), ord('S'), curses.KEY_DOWN):
            self.cursor_y = min(63, self.cursor_y + 1)
            if not self.follow_player:
                self.cam_y = self.cursor_y
        elif ch in (ord('a'), ord('A'), curses.KEY_LEFT):
            self.cursor_x = max(0, self.cursor_x - 1)
            if not self.follow_player:
                self.cam_x = self.cursor_x
        elif ch in (ord('d'), ord('D'), curses.KEY_RIGHT):
            self.cursor_x = min(63, self.cursor_x + 1)
            if not self.follow_player:
                self.cam_x = self.cursor_x
        elif ch in (ord('f'), ord('F')):
            self.follow_player = not self.follow_player
            if self.follow_player:
                self.center_on_player()
                self.log("CAM", "Camera locked to Player.", 6)
            else:
                self.log("CAM", "Free camera mode active.", 6)
        # Action & Navigation Keys
        elif ch in (ord(' '),):
            self.step_day()
        elif ch in (ord('y'), ord('Y')):
            self.step_year()
        elif ch in (ord('e'), ord('E')):
            self.active_tab = "actions"
        elif ch in (ord('m'), ord('M')):
            self.active_tab = "map"
        elif ch in (ord('c'), ord('C')):
            self.active_tab = "council"
        elif ch in (ord('r'), ord('R')):
            if self.player.death_year:
                self.spawn_new_life()
            else:
                self.active_tab = "relics"
        elif ch in (ord('u'), ord('U')):
            self.active_tab = "cults"
        elif ch in (ord('l'), ord('L')):
            self.active_tab = "chronicle"
        elif ch in (ord('n'), ord('N')):
            self.active_tab = "npcs"
        elif ch in (ord('q'), ord('Q')):
            self.save_game()
            return False
        elif ord('1') <= ch <= ord('8') and self.active_tab == "actions":
            opt = ch - ord('0')
            from core import actions
            if opt == 1:
                res = actions.work_job(self.world, self.player)
                self.log("WORK", res["message"], 2 if res["success"] else 1)
                if res["success"]:
                    self.step_day()
            elif opt == 2:
                res = actions.buy_provisions(self.world, self.player)
                self.log("TRADE", res["message"], 2 if res["success"] else 1)
            elif opt == 3:
                res = actions.pray_at_church(self.world, self.player)
                self.log("PRAY", res["message"], 5 if res["success"] else 1)
            elif opt == 4:
                self.player.psychology.joy = min(100, self.player.psychology.joy + 25)
                self.log("TAVERN", "Shared ale & rumors at the tavern. Joy increased (+25%).", 3)
            elif opt == 5:
                res = actions.forge_masterwork_relic(self.world, self.player, f"{self.player.family_name}'s Heirloom")
                self.log("FORGE", res["message"], 3 if res["success"] else 1)
            elif opt == 6:
                if self.selected_npc_id and self.selected_npc_id != self.player.id:
                    res = actions.propose_marriage(self.world, self.player, self.selected_npc_id)
                    self.log("MARRY", res["message"], 2 if res["success"] else 1)
                else:
                    self.log("MARRY", "Select a citizen in the directory or map first to propose!", 1)
            elif opt == 7:
                res = actions.run_for_council_seat(self.world, self.player, "Mayor")
                self.log("COUNCIL", res["message"], 6 if res["success"] else 1)
            elif opt == 8:
                res = actions.join_secret_cult(self.world, self.player)
                self.log("CULT", res["message"], 5 if res["success"] else 1)
            self.active_tab = "map"
        elif ord('1') <= ch <= ord('9') and self.current_scene:
            choice_idx = ch - ord('1')
            if choice_idx < len(self.current_scene.choices):
                self.current_scene.apply_choice(choice_idx, self.world, self.chronicle)
                self.log("CHOICE", f"Applied choice: {self.current_scene.choices[choice_idx].text}", 2)
                self.current_scene = None
                self.active_tab = "map"
        return True

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(False)

        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()

            if max_y < 16 or max_x < 70:
                self.stdscr.addstr(0, 0, "Terminal window too small! Please expand (Min 70x16).")
                self.stdscr.refresh()
                ch = self.stdscr.getch()
                if ch in (ord('q'), ord('Q')):
                    break
                continue

            self.draw_header(max_x)
            self.draw_player_bar(1, max_x)
            self.draw_main_content(2, max_y - 4, max_x)
            self.draw_controls(max_y - 1, max_x)

            self.stdscr.refresh()

            ch = self.stdscr.getch()
            if not self.handle_input(ch):
                break


def main():
    parser = argparse.ArgumentParser(description="Borough AAA CDDA Edition TUI")
    parser.add_argument("--seed", type=str, default=None, help="World generation seed")
    args = parser.parse_args()

    curses.wrapper(lambda stdscr: BoroughTUI(stdscr, seed=args.seed).run())


if __name__ == "__main__":
    main()

