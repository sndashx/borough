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
            if args.player_cmd == "rest":
                if world.player_id and world.player_id in world.npcs:
                    p = world.npcs[world.player_id]
                    p.body.fatigue = max(0, p.body.fatigue - 50)
                    p.body.health = min(100, p.body.health + 20)
                sim.run_days(1)
            elif args.player_cmd == "work":
                if world.player_id and world.player_id in world.npcs:
                    p = world.npcs[world.player_id]
                    p.status.coins += 5
                    p.body.fatigue = min(100, p.body.fatigue + 25)
                sim.run_days(1)
            elif args.player_cmd == "fight" and args.target_id in world.npcs:
                target = world.npcs[args.target_id]
                target.body.health = max(0, target.body.health - 35)
                world.chronicle.append({
                    "year": world.year,
                    "type": "crime",
                    "summary": f"A brawl broke out! {target.first_name} {target.family_name} was struck in anger."
                })
                sim.run_days(1)
            elif args.player_cmd == "steal" and args.target_id in world.npcs:
                target = world.npcs[args.target_id]
                stolen = min(10, target.status.coins)
                target.status.coins -= stolen
                if world.player_id and world.player_id in world.npcs:
                    world.npcs[world.player_id].status.coins += stolen
                world.chronicle.append({
                    "year": world.year,
                    "type": "crime",
                    "summary": f"{stolen} coppers were stolen from {target.first_name} {target.family_name}!"
                })
                sim.run_days(1)

    data = world.to_dict()

    # Calculate moment-to-moment NPC activities for thought bubbles
    activities = {}
    for nid, npc in data.get("npcs", {}).items():
        if npc.get("is_alive", True):
            activities[nid] = get_npc_activity(npc, data)
    data["npc_activities"] = activities

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
