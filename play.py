"""Playable Borough loop.

A real headless playable game. One full session: choose a town, spawn as
a player, live a life with scenes, die, and either continue or end.

This is what the player runs. It exercises every system.
"""
from __future__ import annotations
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))

from core.world import generate_world
from core.simulation import Simulation, DAYS_PER_YEAR
from core.chronicle import Chronicle
from core.scene import pick_scene_for_year, render_scene_for_console
from core.player import spawn_player
from core.spectator import (
    list_living_npcs, town_statistics, find_player_ghosts,
    render_chronicle_section,
)
from engine.render import render_map


def play_one_life(world, sim, chronicle, player, max_years: int = 60,
                  fast: bool = False) -> bool:
    """Run one life for the player. Returns True if died within max_years."""
    scenes_seen = 0
    for year in range(max_years):
        if player.death_year:
            return True
        if not fast:
            sim.run_days(DAYS_PER_YEAR)
        else:
            # Fast-forward: only run until next scene or death
            scene = pick_scene_for_year(world, player, chronicle)
            if scene:
                # Step the sim up to this year boundary
                sim.run_days(DAYS_PER_YEAR)
            else:
                sim.run_days(DAYS_PER_YEAR)
                continue
        scene = pick_scene_for_year(world, player, chronicle)
        if scene:
            scenes_seen += 1
            text = render_scene_for_console(scene)
            print(text)
            if len(scene.choices) == 1:
                choice = 1
            else:
                try:
                    raw = input(f"  Your choice [1-{len(scene.choices)}]: ").strip()
                    choice = int(raw) if raw else 1
                except (EOFError, ValueError, KeyboardInterrupt):
                    choice = 1
            scene.apply_choice(choice - 1, world, chronicle)
    return player.death_year is not None


def show_town_status(world):
    s = town_statistics(world)
    ghosts = find_player_ghosts(world)
    print()
    print(f"  Town: {world.name} — Year {s['year']}")
    print(f"  Population: {s['population_living']} living, {s['population_dead']} dead")
    print(f"  Contracts: {s['active_contracts']} active of {s['total_contracts_ever']} ever")
    print(f"  Coins in circulation: {s['coins_in_circulation']}")
    print(f"  Active debt: {s['active_debt']}")
    print(f"  Chronicle entries: {s['chronicle_entries']}")
    print(f"  Player ghosts (ancestors remembered): {len(ghosts)}")
    print()


def show_living_npcs(world, max_show: int = 20):
    living = list_living_npcs(world)
    print(f"  Living NPCs ({len(living)}):")
    for v in living[:max_show]:
        age = v.age_now
        print(f"    - {v.first_name} {v.family_name}, age {age}, {v.occupation}")
    if len(living) > max_show:
        print(f"    ... and {len(living) - max_show} more")
    print()


def main():
    ap = argparse.ArgumentParser(description="Borough — playable headless loop")
    ap.add_argument("--seed", type=str, default=None,
                    help="Seed for world generation. Any string; auto-generated if omitted.")
    ap.add_argument("--years", type=int, default=60, help="Max years per life")
    ap.add_argument("--lives", type=int, default=1, help="How many lives to play")
    ap.add_argument("--render-dir", type=str, default=None,
                    help="If set, save a map PNG every N years to this dir")
    ap.add_argument("--fast", action="store_true",
                    help="Fast-forward: don't show every year")
    args = ap.parse_args()

    print("=" * 64)
    print("  BOROUGH — a town that does not need you")
    print("=" * 64)
    print()
    print(f"  Generating town at seed {args.seed}...")
    world = generate_world(seed=args.seed)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)

    if args.render_dir:
        os.makedirs(args.render_dir, exist_ok=True)
        render_map(world, os.path.join(args.render_dir, f"map_y{world.year:03d}.png"))
        print(f"  Saved initial map to {args.render_dir}/")

    show_town_status(world)

    for life_n in range(args.lives):
        print(f"  --- LIFE {life_n + 1} ---")
        ghosts = find_player_ghosts(world)
        if ghosts:
            print(f"  A ghost from a previous player-life walks with you.")
            for g in ghosts[:1]:
                for npc_id in g.get("involved", []):
                    n = world.npcs.get(npc_id)
                    if n:
                        print(f"    {n.first_name} {n.family_name} ({n.birth_year}-{n.death_year or 'alive'})")

        player = spawn_player(world)
        world.player_id = player.id
        print(f"  You are born: {player.first_name} {player.family_name}, year {world.year}.")
        print(f"  Mother: {world.npcs[player.mother_id].first_name if player.mother_id and player.mother_id in world.npcs else 'unknown'}")
        print(f"  Father: {world.npcs[player.father_id].first_name if player.father_id and player.father_id in world.npcs else 'unknown'}")
        print()

        died = play_one_life(world, sim, chronicle, player, args.years, args.fast)
        if died:
            age = player.death_year - player.birth_year
            print()
            print(f"  {player.first_name} {player.family_name} has died at age {age}.")
            fame = sum(1 for o in world.npcs.values()
                       if o.is_alive and not o.death_year
                       and player.id in o.relationships
                       and (o.relationships[player.id].affinity > 30
                            or o.relationships[player.id].trust > 60))
            if fame >= 5:
                print(f"  The town remembers you. ({fame} NPCs still know your name.)")
                chronicle.record(world.year, "ghost",
                                 f"The name of {player.first_name} {player.family_name} persists in the village memory.",
                                 involved_npc_ids=[player.id])
            else:
                print(f"  The town does not remember you. ({fame} NPCs know your name.)")
        print()

        if args.render_dir:
            render_map(world, os.path.join(args.render_dir, f"map_y{world.year:03d}.png"))

        if life_n < args.lives - 1:
            print("  --- CHRONICLE OF YOUR LIFE ---")
            for entry in world.chronicle[-30:]:
                if player.id in entry.get("involved", []):
                    print(f"    Y{entry['year']:>3} [{entry['type']}] {entry['summary'][:80]}")
            print()
            show_town_status(world)
            try:
                ans = input("  Spawn a new life in the same town? [Y/n]: ").strip().lower()
                if ans == "n":
                    break
            except (EOFError, KeyboardInterrupt):
                break

    print()
    print("  --- FINAL CHRONICLE (last 20 years) ---")
    print(render_chronicle_section(world, max(0, world.year - 20), world.year, max_entries=20))
    print()
    show_town_status(world)


if __name__ == "__main__":
    main()
