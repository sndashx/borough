"""Scene system — the moments the player actually sees.

Most NPC decisions happen off-screen. The player only sees *moments*:
scenes where they make a meaningful choice. Between scenes, time advances
in weeks/years and the simulation runs without them.

The town does not auto-remember the player. Scenes are *bids* for the
town to remember. Most bids fail.

Scene types:
  - life_milestone: birth, apprenticeship, marriage, childbirth, inheritance, death
  - witnessed_event: crime, accident, public feud
  - character_beat: rare, character-defining choices

The default flow is visual-novel style: portrait + text + 2-5 choices.
~10% of scenes are top-down map moments (the player is placed at the
scene location and can click on objects/NPCs).
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any

from .world import World
from .npc import NPC, LifecycleState, Sex
from .chronicle import Chronicle


class SceneType(str, Enum):
    BIRTH = "birth"
    CHILDHOOD_BEAT = "childhood_beat"
    APPRENTICESHIP_OFFER = "apprenticeship_offer"
    MARRIAGE_PROPOSAL = "marriage_proposal"
    CHILDBIRTH_WITNESSED = "childbirth_witnessed"
    INHERITANCE = "inheritance"
    CRIME_WITNESSED = "crime_witnessed"
    DEATH_FAMILY = "death_family"
    ELDER_DEATH_PREP = "elder_death_prep"
    MARRIAGE_PROPOSED_BY_OTHER = "marriage_proposed_by_other"
    DEBT_CALLED = "debt_called"
    FEAST_DAY = "feast_day"
    DISASTER = "disaster"
    GUILD_DISPUTE = "guild_dispute"
    PLAGUE_REMEDY = "plague_remedy"


@dataclass
class Choice:
    """A player choice in a scene. Each choice has predicted consequences."""
    label: str
    effects: dict = field(default_factory=dict)
    """Effects shape:
        - relationship: { npc_id: affinity_delta, trust_delta }
        - fame_delta: float (how much the town will remember you for this)
        - chronicle: { type, summary } if fame_delta > 0.3
        - add_contract: { type, parties, terms }
        - set_flag: { name, value }
    """


@dataclass
class Scene:
    type: SceneType
    year: int
    location: str  # building name or map region
    title: str
    body: str  # the narrative text
    choices: list[Choice] = field(default_factory=list)
    involved_npc_ids: list[str] = field(default_factory=list)
    is_map_scene: bool = False  # True = top-down map moment
    map_objects: list[dict] = field(default_factory=list)  # for map scenes
    salience: float = 0.0  # how much the town will remember THIS moment
    auto_resolved: bool = False
    resolved_choice_index: Optional[int] = None

    def apply_choice(self, choice_index: int, world: World, chronicle: Chronicle) -> None:
        """Apply the chosen choice's effects to the simulation."""
        if choice_index < 0 or choice_index >= len(self.choices):
            return
        choice = self.choices[choice_index]
        self.auto_resolved = True
        self.resolved_choice_index = choice_index

        for effect_name, effect in choice.effects.items():
            if effect_name == "relationship":
                for npc_id, deltas in effect.items():
                    if npc_id in world.npcs:
                        other = world.npcs[npc_id]
                        if world.player_id not in other.relationships:
                            from .npc import Relationship
                            other.relationships[world.player_id] = Relationship()
                        rel = other.relationships[world.player_id]
                        rel.affinity += deltas.get("affinity_delta", 0)
                        rel.trust += deltas.get("trust_delta", 0)
                        # Symmetric — player remembers them too
                        player = world.npcs.get(world.player_id)
                        if player:
                            if npc_id not in player.relationships:
                                from .npc import Relationship
                                player.relationships[npc_id] = Relationship()
                            rel2 = player.relationships[npc_id]
                            rel2.affinity += deltas.get("affinity_delta", 0)
                            rel2.trust += deltas.get("trust_delta", 0)
            elif effect_name == "fame_delta":
                # We don't track fame as a number on the player directly;
                # the salience of THIS scene determines chronicle inclusion.
                pass
            elif effect_name == "chronicle":
                chronicle.record(
                    self.year,
                    effect.get("type", "player_event"),
                    effect.get("summary", ""),
                    notable=True,
                    involved_npc_ids=self.involved_npc_ids + ([world.player_id] if world.player_id else []),
                )
            elif effect_name == "add_contract":
                from .contract import Contract, ContractType, ContractStatus
                c = Contract(
                    type=ContractType(effect["type"]),
                    parties=effect.get("parties", []),
                    year_created=self.year,
                    terms=effect.get("terms", {}),
                    status=ContractStatus.ACTIVE,
                )
                world.add_contract(c)
            elif effect_name == "set_flag":
                world.flags[effect["name"]] = effect.get("value", True)


# ----------------------------------------------------------------------
# Scene generators — each returns a Scene or None
# ----------------------------------------------------------------------

def birth_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """The first scene of every life. A woman in labor. The town does not
    know you are about to be born. You are one of many children born this
    year. The midwife works. The neighbors gossip. Nobody turns to look.

    In a normal life, the only choice is: keep living. That's the point.
    In a *remembered* life — if the player has a previous-life ghost — the
    midwife tells a story before you are born.
    """
    mother = world.npcs.get(player.mother_id) if player.mother_id else None
    father = world.npcs.get(player.father_id) if player.father_id else None
    location = ""
    if mother and mother.status.household_id:
        h = world.buildings.get(mother.status.household_id)
        if h:
            location = h.name

    mother_name = mother.first_name if mother else "a woman"
    father_name = father.first_name if father else "no one"
    fam = player.family_name

    # Ghost check: does the town remember a previous player ancestor?
    ghost_text = _ghost_preface(world, player)

    if not ghost_text:
        # Default opening. The town is indifferent.
        body = (
            f"A woman is in labor. Her name is {mother_name}, and she is the "
            f"wife of {father_name}. They live in {location or 'a small house'}, "
            f"and they are not important people. There is nothing special about "
            f"this day. The midwife works. The neighbors gossip. The baby that "
            f"will be born tonight will not be remembered by anyone but its "
            f"parents. The town continues.\n\n"
            f"You are born. The child is named {player.first_name} {fam}. "
            f"The midwife hands you to your mother. She does not look at your "
            f"face for long. There are other babies to deliver this season."
        )
    else:
        # A ghost remembers. The town *knows* you are coming.
        body = (
            f"A woman is in labor. Her name is {mother_name}, and she is the "
            f"wife of {father_name}. They live in {location or 'a small house'}, "
            f"and they are not important people. But as the midwife arrives, "
            f"she tells your mother a story.\n\n"
            f"\"{ghost_text}\"\n\n"
            f"That is who you are named for. The midwife hands you to your "
            f"mother. This time, she looks at your face for a long time. You "
            f"are not the first of your name. You will not be the last. But "
            f"this night, the town remembers."
        )

    # The first scene has no real choices. The only choice is to keep being alive.
    return Scene(
        type=SceneType.BIRTH,
        year=world.year,
        location=location,
        title=f"Birth of {player.first_name} {fam}",
        body=body,
        choices=[
            Choice("Continue", effects={}),
        ],
        involved_npc_ids=[n for n in [player.mother_id, player.father_id] if n],
        salience=0.1 if not ghost_text else 0.6,
    )


def _ghost_preface(world: World, player: NPC) -> str:
    """If a previous player-life was remembered and is an ancestor, return
    a story the midwife tells. Otherwise empty string.
    """
    for entry in world.chronicle:
        if entry.get("type") == "ghost":
            # Find which NPC is the ghost
            for npc_id in entry.get("involved", []):
                ghost = world.npcs.get(npc_id)
                if not ghost:
                    continue
                # Is ghost an ancestor of current player?
                if _is_ancestor(ghost, player, world):
                    return (
                        f"Your great-grandmother, {ghost.first_name} {ghost.family_name}, "
                        f"once {random.choice(_ghost_legends(ghost, world))}."
                    )
    return ""


def _is_ancestor(ancestor: NPC, descendant: NPC, world: World) -> bool:
    """Walk descendant's lineage up to see if ancestor is in it."""
    if descendant.mother_id == ancestor.id or descendant.father_id == ancestor.id:
        return True
    cur = descendant
    seen = set()
    for _ in range(8):  # max 4 generations
        if not cur.mother_id and not cur.father_id:
            return False
        if cur.mother_id and cur.mother_id not in seen:
            seen.add(cur.mother_id)
            cur = world.npcs.get(cur.mother_id)
        elif cur.father_id and cur.father_id not in seen:
            seen.add(cur.father_id)
            cur = world.npcs.get(cur.father_id)
        else:
            return False
        if not cur:
            return False
        if cur.id == ancestor.id:
            return True
    return False


def _ghost_legends(ghost: NPC, world: World) -> list[str]:
    """Build 3 possible legendary stories about a ghost from chronicle entries."""
    legends = [f"fed the village through the famine of year {world.year - random.randint(5, 30)}"]
    for entry in world.chronicle:
        if ghost.id in entry.get("involved", []):
            t = entry.get("type", "")
            if t == "death":
                legends.append(f"died refusing to leave the {random.choice(['granary', 'well', 'bridge', 'mill'])}")
            elif t == "ghost":
                legends.append("whose name the priest still speaks on Sundays")
            elif "marriage" in t:
                legends.append("married into a family that did not deserve her")
    legends.append("kept a secret that took three generations to surface")
    return legends[:4]


def childhood_beat_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """A rare character-defining moment in childhood. Maybe once per life."""
    if random.random() > 0.05:
        return None
    if world.year - player.birth_year > 12:
        return None
    if not player.status.household_id:
        return None
    house = world.buildings.get(player.status.household_id)
    if not house:
        return None
    siblings = [n for n in world.npcs.values()
                if n.mother_id == player.mother_id and n.id != player.id
                and n.is_alive and (world.year - n.birth_year) < 18]
    if not siblings:
        # Lonely child — invent a neighbor kid
        return None
    sib = random.choice(siblings)

    # Three flavors of childhood beat: cruelty, kindness, theft
    flavor = random.choice(["cruelty", "kindness", "theft"])
    if flavor == "cruelty":
        body = (
            f"Your sibling {sib.first_name} has been cruel to you for weeks. "
            f"Today, in the yard of your family's house, they pushed you into "
            f"the mud and laughed. The neighbor woman saw. She did not "
            f"intervene. She is waiting to see what you will do."
        )
        return Scene(
            type=SceneType.CHILDHOOD_BEAT,
            year=world.year,
            location=house.name,
            title="The Yard",
            body=body,
            choices=[
                Choice("Hit them back", effects={
                    "relationship": {sib.id: {"affinity_delta": -20, "trust_delta": -10}},
                    "fame_delta": 0.0,
                }),
                Choice("Cry and run inside", effects={
                    "relationship": {sib.id: {"affinity_delta": 5, "trust_delta": 0}},
                }),
                Choice("Say nothing, walk away", effects={
                    "relationship": {sib.id: {"affinity_delta": -5, "trust_delta": 5}},
                }),
            ],
            involved_npc_ids=[sib.id],
            salience=0.05,  # private moment, no witnesses
        )
    elif flavor == "kindness":
        body = (
            f"Your sibling {sib.first_name} is sick with a winter fever. "
            f"The healer says there's nothing to be done. Your mother is "
            f"weeping. Your father has gone to the priest. The house is quiet."
        )
        return Scene(
            type=SceneType.CHILDHOOD_BEAT,
            year=world.year,
            location=house.name,
            title="The Sickbed",
            body=body,
            choices=[
                Choice("Stay with them through the night", effects={
                    "relationship": {sib.id: {"affinity_delta": 30, "trust_delta": 20}},
                }),
                Choice("Go play with the neighbor children", effects={
                    "relationship": {sib.id: {"affinity_delta": -10, "trust_delta": -5}},
                }),
            ],
            involved_npc_ids=[sib.id],
            salience=0.0,  # private moment
        )
    else:  # theft
        body = (
            f"You found {sib.first_name}'s secret hoard — three copper coins "
            f"hidden under a floorboard. They are not looking. No one is "
            f"looking."
        )
        return Scene(
            type=SceneType.CHILDHOOD_BEAT,
            year=world.year,
            location=house.name,
            title="The Hoard",
            body=body,
            choices=[
                Choice("Take the coins", effects={
                    "relationship": {sib.id: {"affinity_delta": -40, "trust_delta": -50}},
                }),
                Choice("Leave them", effects={}),
                Choice("Tell your sibling you found them", effects={
                    "relationship": {sib.id: {"affinity_delta": 20, "trust_delta": 30}},
                }),
            ],
            involved_npc_ids=[sib.id],
            salience=0.0,
        )


def apprenticeship_offer_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """When the player is 13-17, an adult offers to apprentice them.
    This is one of the few choices that *will* be remembered — the
    apprenticeship contract is recorded and witnessed.
    """
    age = world.year - player.birth_year
    if age < 12 or age > 17:
        return None
    if player.status.occupation != "child":
        return None
    # Find adults with skills who could apprentice
    masters = []
    for n in world.npcs.values():
        if not n.is_alive or n.id == player.id:
            continue
        master_age = world.year - n.birth_year
        if master_age < 25 or master_age > 60:
            continue
        # Any skill > 50 qualifies
        for skill, val in n.knowledge.skills.items():
            if val > 50:
                masters.append((n, skill, val))
                break
    if not masters:
        return None
    master, skill, level = random.choice(masters)
    house = world.buildings.get(master.status.household_id) if master.status.household_id else None
    location = house.name if house else "the village"

    body = (
        f"You are {age} years old. {master.first_name} {master.family_name}, "
        f"the village {skill}-worker, has come to your family to discuss an "
        f"apprenticeship. They have {level} in {skill}. They will teach you "
        f"if your parents agree and you serve them for seven years.\n\n"
        f"Your parents look at you. The choice is yours."
    )
    return Scene(
        type=SceneType.APPRENTICESHIP_OFFER,
        year=world.year,
        location=location,
        title="The Offer",
        body=body,
        choices=[
            Choice(f"Accept — become {master.first_name}'s apprentice", effects={
                "add_contract": {
                    "type": "apprenticeship",
                    "parties": [player.id, master.id],
                    "terms": {"skill": skill, "term_years": 7, "master_skill_at_signing": level},
                },
                "relationship": {master.id: {"affinity_delta": 10, "trust_delta": 10}},
                "chronicle": {
                    "type": "apprenticeship_signed",
                    "summary": f"{player.first_name} {player.family_name} is apprenticed to {master.first_name} {master.family_name} in {skill}.",
                },
            }),
            Choice("Refuse — find your own way", effects={
                "relationship": {master.id: {"affinity_delta": -10, "trust_delta": -5}},
            }),
        ],
        involved_npc_ids=[master.id],
        salience=0.7,  # apprenticeships are public, witnessed by family
    )


def marriage_proposal_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """A NPC proposes marriage to the player. Happens in late teens/20s."""
    age = world.year - player.birth_year
    if age < 16 or age > 35:
        return None
    # Already married?
    for c in world.contracts.values():
        if c.type.value == "marriage" and c.status.value == "active" and player.id in c.parties:
            return None
    # Find a candidate
    candidates = []
    for n in world.npcs.values():
        if not n.is_alive or n.id == player.id:
            continue
        c_age = world.year - n.birth_year
        if c_age < 16 or c_age > 40:
            continue
        if (n.sex == player.sex):
            continue
        for cc in world.contracts.values():
            if cc.type.value == "marriage" and cc.status.value == "active" and n.id in cc.parties:
                break
        else:
            candidates.append(n)
    if not candidates:
        return None
    suitor = random.choice(candidates)
    suitor_house = world.buildings.get(suitor.status.household_id) if suitor.status.household_id else None
    location = suitor_house.name if suitor_house else "the village"

    body = (
        f"You are {age}. {suitor.first_name} {suitor.family_name} has come to "
        f"your family with a proposal. They are {world.year - suitor.birth_year}, "
        f"and they are willing. Your parents are willing. The question is yours."
    )
    return Scene(
        type=SceneType.MARRIAGE_PROPOSAL,
        year=world.year,
        location=location,
        title="A Proposal",
        body=body,
        choices=[
            Choice(f"Accept {suitor.first_name}", effects={
                "add_contract": {
                    "type": "marriage",
                    "parties": [player.id, suitor.id],
                    "terms": {"year": world.year},
                },
                "relationship": {suitor.id: {"affinity_delta": 30, "trust_delta": 20}},
                "chronicle": {
                    "type": "marriage",
                    "summary": f"{player.first_name} {player.family_name} weds {suitor.first_name} {suitor.family_name}.",
                },
            }),
            Choice("Refuse", effects={
                "relationship": {suitor.id: {"affinity_delta": -20, "trust_delta": -10}},
            }),
        ],
        involved_npc_ids=[suitor.id],
        salience=0.8,  # marriages are public
    )


def death_family_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """A parent or sibling dies. The player witnesses it. This is one of
    the few scenes that almost always gets remembered.
    """
    if random.random() > 0.10:
        return None
    family = []
    for rel_id in [player.mother_id, player.father_id]:
        if rel_id:
            r = world.npcs.get(rel_id)
            if r and r.is_alive and r.death_year is None:
                family.append(r)
    for sib_id in [c for c in world.npcs.values()
                   if c.mother_id == player.mother_id and c.id != player.id]:
        if sib_id and sib_id.is_alive and not sib_id.death_year:
            family.append(sib_id)
    if not family:
        return None
    deceased = random.choice(family)
    # Mark them dying this year for the scene
    _loc_b = world.buildings.get(deceased.status.household_id) if deceased.status.household_id else None
    location = _loc_b.name if _loc_b else "the village"

    rel = "mother" if deceased.id == player.mother_id else "father" if deceased.id == player.father_id else "sibling"
    body = (
        f"{deceased.first_name} {deceased.family_name} is dying. They are "
        f"your {rel}, and they are not going to survive the season. The house "
        f"is quiet. They have asked to speak to you."
    )
    return Scene(
        type=SceneType.DEATH_FAMILY,
        year=world.year,
        location=location,
        title=f"The Death of {deceased.first_name}",
        body=body,
        choices=[
            Choice("Stay with them until the end", effects={
                "relationship": {deceased.id: {"affinity_delta": 20, "trust_delta": 30}},
                "chronicle": {
                    "type": "death_witnessed",
                    "summary": f"{player.first_name} {player.family_name} kept vigil at {deceased.first_name}'s deathbed.",
                },
            }),
            Choice("Leave the room — you cannot watch", effects={
                "relationship": {deceased.id: {"affinity_delta": -10, "trust_delta": -5}},
            }),
        ],
        involved_npc_ids=[deceased.id],
        salience=0.5,  # family deaths are remembered by family
    )


def crime_witnessed_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """The player witnesses a crime — theft, assault, rarely murder.
    The choices here are the first real test of whether the town
    will remember the player.
    """
    age = world.year - player.birth_year
    if age < 8:
        return None
    if random.random() > 0.03:
        return None
    # Find a thief
    thieves = [n for n in world.npcs.values()
               if n.is_alive and not n.death_year and n.id != player.id
               and (world.year - n.birth_year) >= 14
               and n.mind.honesty < 40]
    if not thieves:
        return None
    thief = random.choice(thieves)
    victims = [n for n in world.npcs.values()
               if n.is_alive and n.id != player.id and n.id != thief.id
               and (world.year - n.birth_year) >= 14
               and n.status.household_id]
    if not victims:
        return None
    victim = random.choice(victims)
    _loc_b = world.buildings.get(victim.status.household_id) if victim.status.household_id else None
    location = _loc_b.name if _loc_b else "the village"

    flavor = random.choice(["theft", "assault"])
    if flavor == "theft":
        body = (
            f"You are walking past {location} when you see {thief.first_name} "
            f"{thief.family_name} climbing out of a window with something "
            f"under their arm. {victim.first_name} {victim.family_name} is "
            f"asleep inside. Nobody else has seen."
        )
    else:
        body = (
            f"You round a corner and see {thief.first_name} {thief.family_name} "
            f"striking {victim.first_name} {victim.family_name} in the street. "
            f"It is not play. {victim.first_name} is on the ground. Nobody "
            f"else is in sight."
        )

    return Scene(
        type=SceneType.CRIME_WITNESSED,
        year=world.year,
        location=location,
        title="What You Saw",
        body=body,
        is_map_scene=False,  # 90% of the time it's a narrative scene
        choices=[
            Choice("Shout and intervene", effects={
                "relationship": {victim.id: {"affinity_delta": 30, "trust_delta": 30},
                                 thief.id: {"affinity_delta": -50, "trust_delta": -60}},
                "chronicle": {
                    "type": "intervened_crime",
                    "summary": f"{player.first_name} {player.family_name} intervened to stop {thief.first_name} {thief.family_name} from harming {victim.first_name} {victim.family_name}.",
                },
            }),
            Choice("Slip away unseen", effects={
                "relationship": {victim.id: {"affinity_delta": 0, "trust_delta": 0},
                                 thief.id: {"affinity_delta": 0, "trust_delta": 0}},
            }),
            Choice("Watch, do nothing", effects={
                "relationship": {victim.id: {"affinity_delta": -10, "trust_delta": -5},
                                 thief.id: {"affinity_delta": 5, "trust_delta": 5}},
            }),
        ],
        involved_npc_ids=[thief.id, victim.id],
        salience=0.9,  # public intervention is *highly* memorable
    )


def feast_day_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """Once a decade, the village holds a feast. A scene about community."""
    if world.year % 10 != 0:
        return None
    if random.random() > 0.5:
        return None
    body = (
        f"It is the feast day. The village gathers in the square. There is "
        f"bread, and there is ale, and there is a pig. The priest speaks. "
        f"Children run. The smith plays a tune on a pipe. People are watching "
        f"each other. This is one of the few days the whole village is in "
        f"one place."
    )
    return Scene(
        type=SceneType.FEAST_DAY,
        year=world.year,
        location="the village square",
        title="Feast Day",
        body=body,
        choices=[
            Choice("Drink with the smith", effects={}),
            Choice("Sit with your family", effects={}),
            Choice("Approach the priest with a question", effects={}),
            Choice("Watch from the edge", effects={}),
        ],
        involved_npc_ids=[],
        salience=0.2,  # feast days are common, but specific deeds stand out
    )


def guild_dispute_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """A dispute erupts between village craftsmen over market prices or guild dues."""
    if random.random() > 0.1:
        return None
    age = world.year - player.birth_year
    if age < 16:
        return None

    body = (
        f"A fierce argument breaks out in the market square. Local artisans "
        f"and craftsmen are deadlocked over guild dues and fixing grain prices. "
        f"Both sides demand the community take a stand."
    )
    return Scene(
        type=SceneType.GUILD_DISPUTE,
        year=world.year,
        location="the market square",
        title="Guild Dispute",
        body=body,
        choices=[
            Choice("Side with the senior guildmasters", effects={"reputation_delta": 5}),
            Choice("Side with independent young craftsmen", effects={"reputation_delta": -2}),
            Choice("Negotiate a compromise using your charm", effects={"reputation_delta": 10}),
            Choice("Remain silent and leave the market", effects={}),
        ],
        involved_npc_ids=[player.id],
        salience=0.4,
    )


def plague_remedy_scene(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """A seasonal fever or sickness spreads through the region."""
    if random.random() > 0.08:
        return None

    body = (
        f"A harsh fever spreads through the cottages of {world.name}. "
        f"Villagers whisper of bad air and cursed water. Families gather herbs "
        f"and seek remedies from the local apothecary."
    )
    return Scene(
        type=SceneType.PLAGUE_REMEDY,
        year=world.year,
        location="your cottage",
        title="Season of Sickness",
        body=body,
        choices=[
            Choice("Purchase herbal potions from the apothecary", effects={"coins_delta": -3}),
            Choice("Care directly for sick neighbors", effects={"health_risk": True, "reputation_delta": 8}),
            Choice("Quarantine inside and pray for health", effects={"piety_delta": 5}),
        ],
        involved_npc_ids=[player.id],
        salience=0.5,
    )


# ----------------------------------------------------------------------
# Scene selection — picks which scene (if any) the player sees this year
# ----------------------------------------------------------------------

def pick_scene_for_year(world: World, player: NPC, chronicle: Chronicle) -> Optional[Scene]:
    """Returns one scene for this year, or None if nothing notable."""
    age = world.year - player.birth_year

    # Always show birth scene on year 0
    if age == 0:
        return birth_scene(world, player, chronicle)

    # Check for family death first (most narratively important)
    s = death_family_scene(world, player, chronicle)
    if s:
        return s

    # Apprenticeship offers at 12-17
    s = apprenticeship_offer_scene(world, player, chronicle)
    if s:
        return s

    # Marriage proposals at 16-35
    s = marriage_proposal_scene(world, player, chronicle)
    if s:
        return s

    # Crime witnessed (rare)
    s = crime_witnessed_scene(world, player, chronicle)
    if s:
        return s

    # Childhood beat
    s = childhood_beat_scene(world, player, chronicle)
    if s:
        return s

    # Feast day
    s = feast_day_scene(world, player, chronicle)
    if s:
        return s

    # Guild dispute
    s = guild_dispute_scene(world, player, chronicle)
    if s:
        return s

    # Plague remedy
    s = plague_remedy_scene(world, player, chronicle)
    if s:
        return s

    return None


def render_scene_for_console(scene: Scene) -> str:
    """Render a scene as text for the terminal. The game's actual UI is
    the map (Sprint 6), but this lets us playtest headlessly."""
    out = []
    out.append("")
    out.append("=" * 64)
    out.append(f"YEAR {scene.year} — {scene.title}")
    out.append(f"Location: {scene.location}")
    out.append("=" * 64)
    out.append("")
    out.append(scene.body)
    out.append("")
    for i, c in enumerate(scene.choices, 1):
        out.append(f"  [{i}] {c.label}")
    out.append("")
    return "\n".join(out)
