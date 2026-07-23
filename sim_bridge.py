"""Simulation bridge for Godot GUI interface.
Allows Godot to generate worlds, advance simulation days/years, perform player interactions,
and load/save JSON state (Soulash 2 style interaction & simulation).
"""
from __future__ import annotations
import json
import sys
import os
import argparse

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.world import generate_world, World
from core.simulation import Simulation
from core.dialogue import generate_greeting, talk, Topic


def get_npc_activity(npc, world) -> str:
    """Determine moment-to-moment NPC activity for visual thought bubbles."""
    body = npc.get("body", {})
    hunger = int(body.get("hunger", 100))
    fatigue = int(body.get("fatigue", 0))
    health = int(body.get("health", 100))
    status = npc.get("status", {})
    occupation = str(status.get("occupation", "citizen"))

    if health < 50:
        return "Injured"
    if hunger < 40:
        return "Eating"
    if fatigue > 70:
        return "Sleeping"
    if occupation == "priest":
        return "Praying"
    if occupation in ["farmer", "herder"]:
        return "Farming"
    if occupation in ["baker", "smith", "carpenter", "mason"]:
        return "Crafting"
    if occupation == "innkeeper":
        return "Serving"
    if occupation == "merchant":
        return "Trading"
    return "Socializing"


def get_npc_position(npc, data) -> list[int]:
    """Calculate dynamic grid coordinates for NPCs based on activity & occupation."""
    status = npc.get("status", {})
    occ = str(status.get("occupation", "citizen")).lower()
    house_id = str(status.get("household_id", ""))
    buildings = data.get("buildings", {})
    day = int(data.get("day", 0))

    hx, hy = 32, 32
    if house_id in buildings:
        hx = int(buildings[house_id].get("x", 32))
        hy = int(buildings[house_id].get("y", 32))

    work_pos = None
    target_btype = None
    if occ in ("smith", "blacksmith"):
        target_btype = "smithy"
    elif occ in ("baker", "miller"):
        target_btype = "mill"
    elif occ == "priest":
        target_btype = "church"
    elif occ in ("innkeeper", "tavern"):
        target_btype = "tavern"
    elif occ == "merchant":
        target_btype = "market"

    if target_btype:
        for b in buildings.values():
            if str(b.get("type", "")).lower() == target_btype:
                work_pos = (int(b.get("x", hx)), int(b.get("y", hy)))
                break

    act = get_npc_activity(npc, data)
    seed_offset = (abs(hash(str(npc.get("id", "")))) + day) % 3
    dx, dy = (seed_offset % 2), (seed_offset // 2)

    if act in ("Sleeping", "Eating", "Injured") or not work_pos:
        return [hx + dx, hy + dy]
    else:
        return [work_pos[0] + dx, work_pos[1] + dy]


def main():
    parser = argparse.ArgumentParser(description="Borough Simulation Bridge")
    parser.add_argument("--action", choices=["gen", "tick_days", "tick_years", "player_act", "dialogue"], required=True)
    parser.add_argument("--seed", default=None)
    parser.add_argument("--name", default="Hollowfield")
    parser.add_argument("--pop", type=int, default=30)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--player-cmd", default=None)
    parser.add_argument("--target-id", default=None)
    parser.add_argument("--input-file", default=None)
    parser.add_argument("--output-file", default=None)

    args = parser.parse_args()

    if args.action == "gen":
        world = generate_world(seed=args.seed, name=args.name, pop=args.pop)
    else:
        if not args.input_file or not os.path.exists(args.input_file):
            print(json.dumps({"error": "Input file required"}))
            sys.exit(1)
        with open(args.input_file, "r") as f:
            data = json.load(f)
        world = World.from_dict(data)
        sim = Simulation(world, seed=world.seed)

        if args.action == "tick_days":
            sim.run_days(args.days)
        elif args.action == "tick_years":
            sim.run_years(args.years)
        elif args.action == "player_act":
            if world.player_id and world.player_id in world.npcs:
                p = world.npcs[world.player_id]
                from core import actions
                if args.player_cmd == "work":
                    res = actions.work_job(world, p)
                elif args.player_cmd == "buy":
                    res = actions.buy_provisions(world, p)
                elif args.player_cmd == "pray":
                    res = actions.pray_at_church(world, p)
                elif args.player_cmd == "marry" and args.target_id:
                    res = actions.propose_marriage(world, p, args.target_id)
                elif args.player_cmd == "run_council":
                    res = actions.run_for_council_seat(world, p, "Mayor")
                elif args.player_cmd == "policy":
                    res = actions.toggle_council_policy(world, p, "curfew", True)
                elif args.player_cmd == "forge_relic":
                    res = actions.forge_masterwork_relic(world, p, "Excalibur")
                elif args.player_cmd == "join_cult":
                    res = actions.join_secret_cult(world, p)
                elif args.player_cmd == "duel" and args.target_id:
                    res = actions.challenge_duel(world, p, args.target_id)
                elif args.player_cmd == "rest":
                    p.body.fatigue = max(0, p.body.fatigue - 50)
                    p.body.health = min(100, p.body.health + 20)
                sim.run_days(1)

    data = world.to_dict()

    # Calculate moment-to-moment NPC activities and dynamic grid positions
    activities = {}
    positions = {}
    for nid, npc in data.get("npcs", {}).items():
        if npc.get("is_alive", True):
            activities[nid] = get_npc_activity(npc, data)
            positions[nid] = get_npc_position(npc, data)
    data["npc_activities"] = activities
    data["npc_positions"] = positions

    # Deep PhD Subsystem summaries for Godot UI inspectors
    if world.governance:
        data["council_summary"] = {
            "treasury": world.governance.policies.treasury_gold,
            "tax_rate": world.governance.policies.tax_rate,
            "curfew": world.governance.policies.curfew_active,
            "subsidies": world.governance.policies.grain_subsidy,
            "seats": {
                title: {
                    "incumbent_name": f"{world.npcs[seat.incumbent_id].first_name} {world.npcs[seat.incumbent_id].family_name}" if seat.incumbent_id and seat.incumbent_id in world.npcs else "Vacant",
                    "title": seat.title
                }
                for title, seat in world.governance.seats.items()
            }
        }

    if world.cults:
        data["cults_summary"] = [
            {
                "name": cult.name,
                "leader": f"{world.npcs[cult.leader_id].first_name} {world.npcs[cult.leader_id].family_name}" if cult.leader_id in world.npcs else "Shadow",
                "symbol": cult.secret_symbol,
                "doctrine": cult.doctrine,
                "members_count": len(cult.members),
                "secrecy": cult.secrecy_level,
            }
            for cult in world.cults.cults.values()
        ]

    if world.relics:
        data["relics_summary"] = [
            {
                "name": relic.name,
                "type": relic.item_type,
                "material": relic.material,
                "creator": relic.creator_name,
                "owner": f"{world.npcs[relic.current_owner_id].first_name} {world.npcs[relic.current_owner_id].family_name}" if relic.current_owner_id in world.npcs else "Unknown",
                "value": relic.renown_value,
                "description": relic.engraving_description,
                "history": relic.history_log,
            }
            for relic in world.relics.relics.values()
        ]

    if world.lore:
        data["legends_summary"] = [
            {
                "myth": legend.mythic_description,
                "year": legend.year_occurred,
                "impact": legend.cultural_impact,
            }
            for legend in world.lore.legends.values()
        ]

    if args.action == "dialogue" and args.target_id:
        if args.target_id in world.npcs:
            speaker = world.npcs[args.target_id]
            data["last_dialogue"] = generate_greeting(speaker, rep_score=0)

    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(data, f)
    else:
        print(json.dumps(data))


if __name__ == "__main__":
    main()
