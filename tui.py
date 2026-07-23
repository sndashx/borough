"""Borough — Terminal UI (ncurses) for interactive, turn-based life simulation.

KISS approach:
  - Turn-based daily/yearly step.
  - Interactive menu system for scenes, decisions, NPC inspection, and chronicle log.
  - Full integration with core world, simulation, player, and chronicle.
"""
from __future__ import annotations

import curses
import os
import sys
import argparse
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), "engine"))

from core.world import generate_world
from core.simulation import Simulation, DAYS_PER_YEAR
from core.chronicle import Chronicle
from core.scene import pick_scene_for_year
from core.player import spawn_player, on_player_death
from core.spectator import town_statistics
from core.persistence import save_world, load_world


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

        # Player
        if self.world.player_id and self.world.player_id in self.world.npcs:
            self.player = self.world.npcs[self.world.player_id]
        else:
            self.player = spawn_player(self.world)
            self.world.player_id = self.player.id

        self.current_scene = None
        self.message_log: list[str] = [
            f"Welcome to Borough ({self.world.name})!",
            f"You were born as {self.player.first_name} {self.player.family_name} in Year {self.player.birth_year}.",
        ]
        self.active_tab = "status"  # status, npcs, chronicle, scene

        # Setup colors
        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Header
                curses.init_pair(2, curses.COLOR_YELLOW, -1)                   # Status / Highlights
                curses.init_pair(3, curses.COLOR_GREEN, -1)                    # Player Info
                curses.init_pair(4, curses.COLOR_RED, -1)                      # Death / Danger
                curses.init_pair(5, curses.COLOR_CYAN, -1)                     # Events / Headers
        except Exception:
            pass

    def log(self, msg: str):
        self.message_log.append(msg)
        if len(self.message_log) > 100:
            self.message_log.pop(0)

    def add_str_safe(self, y: int, x: int, text: str, max_len: int, attr=0):
        max_y, max_x = self.stdscr.getmaxyx()
        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return
        
        # Avoid writing to the exact bottom-right corner to prevent curses auto-scroll
        allowed = min(max_len, max_x - x - (1 if y == max_y - 1 else 0))
        if allowed <= 0:
            return

        printable = text[:allowed]
        try:
            self.stdscr.addstr(y, x, printable, attr)
        except curses.error:
            pass

    def step_day(self):
        if self.player.death_year:
            self.log("You are deceased! Press [R] to reincarnate into a new life.")
            return

        self.sim.tick_day()

        # Check if player died during the day
        if self.player.death_year:
            on_player_death(self.world, self.chronicle)
            age = self.player.death_year - self.player.birth_year
            self.log(f"*** YOU HAVE DIED at age {age} in Year {self.player.death_year}! ***")
            self.log("Press [R] to reincarnate in this village.")
            return

        # Check for year boundary scene
        if self.sim.day_in_year == 0:
            sc = pick_scene_for_year(self.world, self.player, self.chronicle)
            if sc:
                self.current_scene = sc
                self.active_tab = "scene"
                self.log(f"Year {self.world.year}: {sc.title}")

    def step_year(self):
        if self.player.death_year:
            self.log("You have died! Press [R] to spawn a new life in this town.")
            return

        for _ in range(DAYS_PER_YEAR):
            self.step_day()
            if self.current_scene:
                break
        if not self.current_scene:
            self.log(f"Advanced to Year {self.world.year}.")

    def spawn_new_life(self):
        if not self.player.death_year:
            self.log("You are still alive!")
            return
        self.player = spawn_player(self.world)
        self.world.player_id = self.player.id
        self.current_scene = None
        self.active_tab = "status"
        self.log(f"Reincarnated as {self.player.first_name} {self.player.family_name} in Year {self.world.year}.")

    def save_game(self):
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        save_world(self.world, self.save_path)
        self.log(f"Saved game to {self.save_path}")

    def draw_header(self, max_x: int):
        season = self.world.weather_state.current_season.value.capitalize() if self.world.weather_state else "Spring"
        weather = self.world.weather_state.current.value.capitalize() if self.world.weather_state else "Clear"
        rep_tier = self.world.reputation.town_tier().capitalize() if self.world.reputation else "Stranger"

        header_str = (
            f" BOROUGH — {self.world.name} | Year {self.world.year} (Day {self.sim.day_in_year+1}/360) | "
            f"Season: {season} ({weather}) | Rep: {rep_tier} "
        )
        attr = curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE
        self.add_str_safe(0, 0, header_str.ljust(max_x), max_x, attr)

    def draw_player_bar(self, y: int, max_x: int):
        p = self.player
        age = self.world.year - p.birth_year if not p.death_year else (p.death_year - p.birth_year)
        
        if p.death_year:
            status_attr = curses.color_pair(4) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
            status_str = f"DEAD (d. Y{p.death_year})"
        else:
            status_attr = curses.color_pair(3) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
            status_str = "ALIVE"

        info = (
            f" Player: {p.first_name} {p.family_name} [{status_str}] | Age: {age} | "
            f"Job: {p.status.occupation} | Health: {p.body.health}/100 | "
            f"Hunger: {p.body.hunger}/100 | Coins: {p.status.coins}"
        )
        self.add_str_safe(y, 0, info.ljust(max_x), max_x, status_attr)

    def draw_controls(self, y: int, max_x: int):
        controls = " [Space/D] Step Day | [Y] Step Year | [1-9] Scene Choice | [S] Status | [N] NPCs | [C] Chronicle | [R] Reincarnate | [Q] Quit "
        attr = curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE
        self.add_str_safe(y, 0, controls.ljust(max_x), max_x - 1, attr)

    def draw_main_content(self, start_y: int, height: int, max_x: int):
        # Split: Left 60% view, Right 40% message log
        left_w = int(max_x * 0.6)
        right_w = max_x - left_w - 1

        # Draw divider
        for i in range(height):
            try:
                self.stdscr.addch(start_y + i, left_w, "|")
            except curses.error:
                pass

        # Left side panel content based on active tab
        if self.active_tab == "scene" and self.current_scene:
            self.draw_scene_panel(start_y, height, left_w)
        elif self.active_tab == "npcs":
            self.draw_npcs_panel(start_y, height, left_w)
        elif self.active_tab == "chronicle":
            self.draw_chronicle_panel(start_y, height, left_w)
        else:
            self.draw_status_panel(start_y, height, left_w)

        # Right side: Message Log
        self.draw_log_panel(start_y, height, left_w + 1, right_w)

    def draw_status_panel(self, y: int, height: int, width: int):
        stats = town_statistics(self.world)
        hdr_attr = curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        
        lines = [
            ("=== TOWN OVERVIEW ===", hdr_attr),
            (f" Town Name: {self.world.name}", 0),
            (f" Seed: {str(self.world.seed)[:16]}...", 0),
            (f" Living Population: {stats['population_living']}", 0),
            (f" Deceased Population: {stats['population_dead']}", 0),
            (f" Active Contracts: {stats['active_contracts']}", 0),
            (f" Coins in Circulation: {stats['coins_in_circulation']}", 0),
            ("", 0),
            ("=== YOUR CHARACTER ===", hdr_attr),
            (f" Name: {self.player.first_name} {self.player.family_name}", 0),
            (f" Sex: {self.player.sex.value}", 0),
            (f" Mind Traits: Ambition={self.player.mind.ambition}, Honesty={self.player.mind.honesty}, Courage={self.player.mind.courage}", 0),
            (f" House ID: {self.player.status.household_id or 'None'}", 0),
            (f" Skills: {', '.join(f'{k}:{v}' for k,v in self.player.knowledge.skills.items()) or 'None'}", 0),
        ]
        for idx, (line, attr) in enumerate(lines[:height]):
            self.add_str_safe(y + idx, 1, line, width - 2, attr)

    def draw_scene_panel(self, y: int, height: int, width: int):
        if not self.current_scene:
            self.add_str_safe(y, 1, "No active event scene.", width - 2)
            return

        hdr_attr = curses.color_pair(2) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        self.add_str_safe(y, 1, f"=== EVENT: {self.current_scene.title.upper()} ===", width - 2, hdr_attr)

        row = y + 2
        # Text wrap scene description
        desc_lines = []
        for paragraph in self.current_scene.description.split("\n"):
            desc_lines.extend(textwrap.wrap(paragraph, width - 4))
            desc_lines.append("")

        for line in desc_lines:
            if row >= y + height - len(self.current_scene.choices) - 3:
                break
            self.add_str_safe(row, 2, line, width - 4)
            row += 1

        row += 1
        self.add_str_safe(row, 1, "Choices:", width - 2, curses.A_BOLD)
        row += 1

        for idx, choice in enumerate(self.current_scene.choices, 1):
            if row >= y + height:
                break
            choice_str = f" [{idx}] {choice.text}"
            self.add_str_safe(row, 2, choice_str, width - 4, curses.color_pair(5) if curses.has_colors() else 0)
            row += 1

    def draw_npcs_panel(self, y: int, height: int, width: int):
        hdr_attr = curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        living = self.world.living_npcs()
        self.add_str_safe(y, 1, f"=== LIVING NPCS ({len(living)}) ===", width - 2, hdr_attr)

        for idx, npc in enumerate(living[:height - 2]):
            age = self.world.year - npc.birth_year
            line = f" - {npc.first_name} {npc.family_name} (Age {age}, {npc.status.occupation}) | Coins: {npc.status.coins}"
            self.add_str_safe(y + idx + 1, 1, line, width - 2)

    def draw_chronicle_panel(self, y: int, height: int, width: int):
        hdr_attr = curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        self.add_str_safe(y, 1, "=== TOWN CHRONICLE ===", width - 2, hdr_attr)

        entries = self.world.chronicle[-(height - 2):]
        for idx, entry in enumerate(entries):
            marker = "*" if entry.get("notable") else " "
            line = f" {marker} Y{entry['year']:>3} [{entry['type']}] {entry['summary']}"
            self.add_str_safe(y + idx + 1, 1, line, width - 2)

    def draw_log_panel(self, y: int, height: int, start_x: int, width: int):
        hdr_attr = curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        self.add_str_safe(y, start_x, "=== MESSAGE LOG ===", width - 1, hdr_attr)

        visible_logs = self.message_log[-(height - 2):]
        for idx, log_msg in enumerate(visible_logs):
            self.add_str_safe(y + idx + 1, start_x, log_msg, width - 1)

    def handle_input(self, ch: int) -> bool:
        if ch in (ord('q'), ord('Q')):
            self.save_game()
            return False
        elif ch in (ord(' '), ord('d'), ord('D')):
            self.step_day()
        elif ch in (ord('y'), ord('Y')):
            self.step_year()
        elif ch in (ord('s'), ord('S')):
            self.active_tab = "status"
        elif ch in (ord('n'), ord('N')):
            self.active_tab = "npcs"
        elif ch in (ord('c'), ord('C')):
            self.active_tab = "chronicle"
        elif ch in (ord('r'), ord('R')):
            self.spawn_new_life()
        elif ord('1') <= ch <= ord('9') and self.current_scene:
            choice_idx = ch - ord('1')
            if choice_idx < len(self.current_scene.choices):
                self.current_scene.apply_choice(choice_idx, self.world, self.chronicle)
                self.log(f"Applied choice: {self.current_scene.choices[choice_idx].text}")
                self.current_scene = None
                self.active_tab = "status"
        return True

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(False)

        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()

            if max_y < 12 or max_x < 50:
                self.stdscr.addstr(0, 0, "Terminal too small!")
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
    parser = argparse.ArgumentParser(description="Borough Interactive TUI")
    parser.add_argument("--seed", type=str, default=None, help="World generation seed")
    args = parser.parse_args()

    curses.wrapper(lambda stdscr: BoroughTUI(stdscr, seed=args.seed).run())


if __name__ == "__main__":
    main()
