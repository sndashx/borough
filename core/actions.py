"""Player Interaction API for Borough.

Provides direct, authoritative player actions that mutate world state, contracts,
governance, relics, cults, anatomy, items, and chronicle.
"""
from __future__ import annotations

import random
from typing import Optional, Dict, Any

from .world import World
from .npc import NPC, Relationship, TraitSet
from .contract import Contract, ContractType, ContractStatus
from .chronicle import Chronicle
from .anatomy import Wound, Anatomy
from .relic import Relic


def work_job(world: World, player: NPC) -> Dict[str, Any]:
    """Perform a day of labor in player's current occupation."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    wage = random.randint(10, 25)
    player.status.coins += wage
    player.body.hunger = max(0, player.body.hunger - 15)
    player.body.fatigue = max(0, player.body.fatigue - 20)

    # Goal / Ambition progress
    player.ambition.progress = min(100, player.ambition.progress + random.randint(3, 8))

    # Skill advancement
    occ = player.status.occupation or "unskilled"
    current_skill = player.knowledge.skills.get(occ, 10)
    player.knowledge.skills[occ] = min(100, current_skill + 2)

    msg = f"Worked a shift as a {occ}. Earned {wage} Gold and improved {occ} skill to {player.knowledge.skills[occ]}."
    
    if world.chronicle:
        Chronicle(world).record(
            world.year, "player_work",
            f"{player.first_name} {player.family_name} worked as a {occ}, earning {wage} Gold.",
            notable=False, involved_npc_ids=[player.id]
        )

    return {"success": True, "message": msg, "wage": wage}


def buy_provisions(world: World, player: NPC, food_type: str = "bread") -> Dict[str, Any]:
    """Purchase food/provisions from the town market or bakery."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    cost = 5
    if player.status.coins < cost:
        return {"success": False, "message": f"Insufficient gold! {food_type.capitalize()} costs {cost} Gold."}

    player.status.coins -= cost
    player.body.hunger = min(100, player.body.hunger + 40)
    player.body.health = min(100, player.body.health + 15)

    msg = f"Purchased fresh {food_type} for {cost} Gold. Health and Hunger restored!"
    return {"success": True, "message": msg}


def pray_at_church(world: World, player: NPC, donation: int = 2) -> Dict[str, Any]:
    """Pray and worship at the local church/temple."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    if donation > 0:
        actual_donation = min(player.status.coins, donation)
        player.status.coins -= actual_donation
        if world.governance and world.governance.policies:
            world.governance.policies.treasury_gold += actual_donation

    player.psychology.paranoia = max(0, player.psychology.paranoia - 20)
    player.psychology.grief = max(0, player.psychology.grief - 15)
    player.psychology.belonging_need = min(100, player.psychology.belonging_need + 15)

    # Heal small wounds
    if player.anatomy.wounds:
        healed = player.anatomy.wounds.pop(0)
        heal_msg = f" Spiritual healing closed a wound on your {healed.location.value}."
    else:
        heal_msg = ""

    msg = f"Prayed at the altar. Paranoia and grief eased.{heal_msg}"
    return {"success": True, "message": msg}


def propose_marriage(world: World, player: NPC, target_npc_id: str) -> Dict[str, Any]:
    """Propose marriage to a single living citizen."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    target = world.npcs.get(target_npc_id)
    if not target or not target.is_alive:
        return {"success": False, "message": "Target citizen is not living."}

    # Check if either party is already married
    for c in world.contracts.values():
        if c.type.value == "marriage" and c.status.value == "active" and (player.id in c.parties or target.id in c.parties):
            return {"success": False, "message": "One or both parties are already married!"}

    # Check affinity
    rel = target.relationships.get(player.id)
    affinity = rel.affinity if rel else 0
    if affinity < 20 and random.random() > 0.3:
        return {"success": False, "message": f"{target.first_name} rejected your marriage proposal!"}

    # Create Marriage Contract
    m_contract = Contract(
        type=ContractType.MARRIAGE,
        parties=[player.id, target.id],
        year_created=world.year,
        terms={"dowry_gold": 20},
        status=ContractStatus.ACTIVE,
    )
    world.add_contract(m_contract)

    # Symlink relationships
    if player.id not in target.relationships:
        target.relationships[player.id] = Relationship()
    target.relationships[player.id].affinity += 40
    target.relationships[player.id].trust += 30

    # Share household if available
    if target.status.household_id and not player.status.household_id:
        player.status.household_id = target.status.household_id

    msg = f"{target.first_name} {target.family_name} accepted your proposal! You are now wed."
    
    Chronicle(world).record(
        world.year, "marriage",
        f"{player.first_name} {player.family_name} wed {target.first_name} {target.family_name}.",
        notable=True, involved_npc_ids=[player.id, target.id]
    )

    return {"success": True, "message": msg}


def run_for_council_seat(world: World, player: NPC, seat_title: str) -> Dict[str, Any]:
    """Run for an official seat on the Town Council."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    gov = world.governance
    if not gov:
        return {"success": False, "message": "No Town Council established."}

    if seat_title not in gov.seats:
        return {"success": False, "message": f"Seat '{seat_title}' does not exist."}

    seat = gov.seats[seat_title]
    
    # Calculate vote likelihood based on reputation and skills
    rep_tier = world.reputation.town_tier() if world.reputation else "stranger"
    rep_bonus = 30 if rep_tier in ("hero", "pillar") else 10 if rep_tier == "respected" else 0
    
    success_chance = (player.mind.ambition + rep_bonus) / 120.0
    
    if random.random() <= success_chance or seat.incumbent_id is None:
        seat.incumbent_id = player.id
        msg = f"ELECTION VICTORY! You have been elected as the Town {seat_title}!"
        Chronicle(world).record(
            world.year, "election",
            f"{player.first_name} {player.family_name} was elected as Town {seat_title}.",
            notable=True, involved_npc_ids=[player.id]
        )
        return {"success": True, "message": msg}
    else:
        inc = world.npcs.get(seat.incumbent_id) if seat.incumbent_id else None
        inc_name = f"{inc.first_name} {inc.family_name}" if inc else "the incumbent"
        msg = f"Election loss. {inc_name} retained the seat of {seat_title}."
        return {"success": False, "message": msg}


def toggle_council_policy(world: World, player: NPC, policy_name: str, value: Any) -> Dict[str, Any]:
    """If player holds a council seat, enact or toggle town policies."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    gov = world.governance
    if not gov:
        return {"success": False, "message": "No Town Council established."}

    # Check if player holds any council seat
    player_seats = [title for title, seat in gov.seats.items() if seat.incumbent_id == player.id]
    if not player_seats:
        return {"success": False, "message": "You must hold a Town Council seat to change policies!"}

    pol = gov.policies
    if policy_name == "tax_rate":
        pol.tax_rate = max(0, min(50, int(value)))
        msg = f"Enacted new Town Tax Rate: {pol.tax_rate}%."
    elif policy_name == "curfew":
        pol.curfew_active = bool(value)
        msg = f"Night Curfew is now {'ACTIVE' if pol.curfew_active else 'LIFTED'}."
    elif policy_name == "grain_subsidy":
        pol.grain_subsidy = bool(value)
        msg = f"Grain Subsidies are now {'ACTIVE' if pol.grain_subsidy else 'CANCELLED'}."
    else:
        return {"success": False, "message": f"Unknown policy: {policy_name}"}

    Chronicle(world).record(
        world.year, "policy_change",
        f"Council member {player.first_name} {player.family_name} enacted policy: {msg}",
        notable=True, involved_npc_ids=[player.id]
    )

    return {"success": True, "message": msg}


def forge_masterwork_relic(world: World, player: NPC, relic_name: str, material: str = "Damascus Iron") -> Dict[str, Any]:
    """Forge a custom masterwork relic item."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    cost = 30
    if player.status.coins < cost:
        return {"success": False, "message": f"Forging a relic requires {cost} Gold in raw materials!"}

    player.status.coins -= cost
    
    if not world.relics:
        from .relic import RelicRegistry
        world.relics = RelicRegistry(world)

    import uuid
    relic_id = f"relic_{uuid.uuid4().hex[:6]}"
    relic = Relic(
        id=relic_id,
        name=relic_name,
        creator_id=player.id,
        creator_name=f"{player.first_name} {player.family_name}",
        year_created=world.year,
        item_type="sword",
        material=material,
        engraving_description=f"Masterwork forged by {player.first_name} in Year {world.year}.",
        renown_value=150,
        current_owner_id=player.id,
        family_id=player.family_name,
        history_log=[f"Year {world.year}: Crafted by {player.first_name} {player.family_name}."],
    )
    world.relics.relics[relic_id] = relic

    player.ambition.progress = 100
    msg = f"FORGED MASTERWORK RELIC: '{relic_name}'! Renown value: 150 Gold."

    Chronicle(world).record(
        world.year, "relic_forged",
        f"{player.first_name} {player.family_name} forged the masterwork relic '{relic_name}'.",
        notable=True, involved_npc_ids=[player.id]
    )

    return {"success": True, "message": msg, "relic_id": relic.id}


def join_secret_cult(world: World, player: NPC) -> Dict[str, Any]:
    """Infiltrate or join an underground cult in town."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    if not world.cults or not world.cults.cults:
        return {"success": False, "message": "No underground cults discovered in town."}

    cult = random.choice(list(world.cults.cults.values()))
    if player.id in cult.members:
        return {"success": False, "message": f"You are already an initiated member of {cult.name}!"}

    cult.members.append(player.id)
    player.psychology.paranoia = min(100, player.psychology.paranoia + 15)

    msg = f"SECRET INITIATION: Joined {cult.name} (Symbol: '{cult.secret_symbol}') under doctrine: '{cult.doctrine}'."

    Chronicle(world).record(
        world.year, "cult_initiation",
        f"A shadowy figure joined the ranks of {cult.name}.",
        notable=False, involved_npc_ids=[player.id]
    )

    return {"success": True, "message": msg, "cult_name": cult.name}


def challenge_duel(world: World, player: NPC, target_npc_id: str) -> Dict[str, Any]:
    """Challenge a rival citizen to a combat duel."""
    if not player.is_alive or player.death_year:
        return {"success": False, "message": "Player is deceased."}

    target = world.npcs.get(target_npc_id)
    if not target or not target.is_alive:
        return {"success": False, "message": "Target citizen is not living."}

    player_strength = player.knowledge.skills.get("combat", 30) + (player.body.health // 2)
    target_strength = target.knowledge.skills.get("combat", 30) + (target.body.health // 2)

    if player_strength >= target_strength or random.random() > 0.4:
        # Player wins duel
        part = random.choice(["torso", "right_arm", "left_leg"])
        target.anatomy.add_wound(body_part=part, severity=45, cause=f"Duel with {player.first_name}", year=world.year)
        target.body.health = max(10, target.body.health - 35)

        msg = f"DUEL VICTORY! Defeated {target.first_name} {target.family_name} in combat!"
        
        Chronicle(world).record(
            world.year, "duel",
            f"{player.first_name} {player.family_name} bested {target.first_name} {target.family_name} in a duel.",
            notable=True, involved_npc_ids=[player.id, target.id]
        )
        return {"success": True, "message": msg}
    else:
        # Player suffers wound
        part = random.choice(["head", "left_arm", "right_leg"])
        player.anatomy.add_wound(body_part=part, severity=65, cause=f"Duel with {target.first_name}", year=world.year)
        player.body.health = max(5, player.body.health - 40)

        msg = f"DUEL DEFEAT! {target.first_name} wounded you in combat!"
        return {"success": False, "message": msg}
