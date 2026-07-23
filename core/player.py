"""Player lifecycle: spawn as a baby born to current population, age up.
The town does not auto-remember the player.
"""
from __future__ import annotations
import random
import uuid

from .world import World, FIRST_NAMES_M, FIRST_NAMES_F, FAMILY_NAMES
from .npc import NPC, Sex, TraitSet, LifecycleState
from .chronicle import Chronicle
from .contract import Contract, ContractType


def spawn_player(world: World, name: str | None = None, age: int = 0) -> NPC:
    """Mark a newly born NPC as the player. By default, find the most recent
    baby born this year. If none, force-spawn a newborn into a random household.
    """
    # Try to find a baby born this year
    candidates = [n for n in world.npcs.values()
                  if n.is_alive
                  and n.birth_year == world.year
                  and not n.is_player
                  and not n.death_year]
    if candidates:
        baby = random.choice(candidates)
        baby.is_player = True
        baby.player_lifecycle_id = str(uuid.uuid4())
        return baby

    # Else, force-spawn
    living = [n for n in world.npcs.values() if n.is_alive and n.body.fertility > 0
              and n.sex == Sex.F and 16 <= world.year - n.birth_year <= 42]
    if not living:
        # Fallback: spawn an orphan
        return _force_spawn_orphan(world, age)
    mother = random.choice(living)
    return _birth_to(world, mother, age)


def _force_spawn_orphan(world: World, age: int) -> NPC:
    """Spawn a young adult orphan as the player (no parents alive)."""
    sex = Sex.M if random.random() < 0.51 else Sex.F
    first = random.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
    fam = random.choice(FAMILY_NAMES)
    npc = NPC(
        first_name=first, family_name=fam, sex=sex,
        birth_year=world.year - age, legitimacy=False,
    )
    npc.mind = TraitSet.random(random.Random())
    npc.is_player = True
    npc.player_lifecycle_id = str(uuid.uuid4())
    # Place in a random house
    houses = [b for b in world.buildings.values() if b.type.value == "house"]
    if houses:
        h = random.choice(houses)
        npc.status.household_id = h.id
        h.occupant_npc_ids.append(npc.id)
    world.add_npc(npc)
    return npc


def _birth_to(world: World, mother: NPC, age: int = 0) -> NPC:
    sex = Sex.M if random.random() < 0.51 else Sex.F
    first = random.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
    father_id = None
    for c in world.contracts.values():
        if c.type.value == "marriage" and c.status.value == "active" and mother.id in c.parties:
            for p in c.parties:
                if p != mother.id and world.npcs.get(p) and world.npcs[p].is_alive:
                    father_id = p
                    break
            break
    fam = mother.family_name
    if father_id and world.npcs.get(father_id):
        fam = world.npcs[father_id].family_name
    baby = NPC(
        first_name=first, family_name=fam, sex=sex,
        birth_year=world.year - age, mother_id=mother.id, father_id=father_id,
        legitimacy=True,
    )
    baby.mind = TraitSet.random(random.Random(), base=mother.mind)
    baby.is_player = True
    baby.player_lifecycle_id = str(uuid.uuid4())
    if mother.status.household_id:
        baby.status.household_id = mother.status.household_id
        h = world.buildings.get(mother.status.household_id)
        if h:
            h.occupant_npc_ids.append(baby.id)
    world.add_npc(baby)
    return baby


def on_player_death(world: World, chronicle: Chronicle) -> None:
    """Called when the player-character dies. Per spec: the town does not
    remember the player unless they gave it a reason. We compute fame at
    death; if high enough, the player becomes a ghost of the chronicle.
    """
    player = next((n for n in world.npcs.values() if n.is_player and n.death_year == world.year), None)
    if not player:
        return
    # Fame = how many NPCs know of them, weighted by relationship intensity
    fame_score = 0
    for other in world.npcs.values():
        if not other.is_alive or other.id == player.id:
            continue
        if player.id in other.relationships:
            rel = other.relationships[player.id]
            if rel.affinity > 30 or rel.trust > 60:
                fame_score += 1
    # 0 = nobody knew you, 30+ = town remembers
    if fame_score >= 5:
        chronicle.record(
            world.year, "ghost",
            f"The name of {player.first_name} {player.family_name} persists in the village memory.",
            notable=True, involved_npc_ids=[player.id],
        )
    # Spawn a new player life (next session can pick this up).
    # Don't auto-spawn mid-session — the player chooses to continue.
    # Mark the new player slot as ready:
    world.add_contract(Contract(
        type=ContractType.INHERITANCE_CLAIM,
        parties=[],
        year_created=world.year,
        terms={"next_player_spawn_pending": True, "previous_player_id": player.id, "fame_score": fame_score},
    ))
