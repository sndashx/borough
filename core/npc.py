"""NPC schema and behavior. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .anatomy import Anatomy


# Counter-based ID for performance
_npc_counter = [0]
def _next_npc_id() -> str:
    _npc_counter[0] += 1
    return f"n_{_npc_counter[0]}"


class Sex(str, Enum):
    M = "M"
    F = "F"


class LifecycleState(str, Enum):
    INFANT = "infant"        # 0-3
    CHILD = "child"          # 4-12
    ADOLESCENT = "adolescent"  # 13-17
    ADULT = "adult"          # 18-59
    ELDER = "elder"          # 60+


def lifecycle_for_age(age: int) -> LifecycleState:
    if age < 4:
        return LifecycleState.INFANT
    if age < 13:
        return LifecycleState.CHILD
    if age < 18:
        return LifecycleState.ADOLESCENT
    if age < 60:
        return LifecycleState.ADULT
    return LifecycleState.ELDER


@dataclass
class TraitSet:
    """Personality. All 0-100. Inherited + small mutation."""
    honesty: int = 50
    courage: int = 50
    ambition: int = 50
    piety: int = 50
    vengefulness: int = 50
    patience: int = 50
    greed: int = 50
    sociability: int = 50
    curiosity: int = 50
    prudence: int = 50
    charisma: int = 50
    cunning: int = 50
    stubbornness: int = 50
    frugality: int = 50
    devotion: int = 50
    superstition: int = 50
    creativity: int = 50
    loyalty: int = 50

    @staticmethod
    def random(rng, base: Optional["TraitSet"] = None) -> "TraitSet":
        import random
        if base is None:
            return TraitSet(
                honesty=rng.randint(20, 80),
                courage=rng.randint(20, 80),
                ambition=rng.randint(20, 80),
                piety=rng.randint(20, 80),
                vengefulness=rng.randint(20, 80),
                patience=rng.randint(20, 80),
                greed=rng.randint(20, 80),
                sociability=rng.randint(20, 80),
                curiosity=rng.randint(20, 80),
                prudence=rng.randint(20, 80),
                charisma=rng.randint(20, 80),
                cunning=rng.randint(20, 80),
                stubbornness=rng.randint(20, 80),
                frugality=rng.randint(20, 80),
                devotion=rng.randint(20, 80),
                superstition=rng.randint(20, 80),
                creativity=rng.randint(20, 80),
                loyalty=rng.randint(20, 80),
            )
        def mut(v: int) -> int:
            return max(0, min(100, v + rng.randint(-10, 10)))
        return TraitSet(
            honesty=mut(base.honesty),
            courage=mut(base.courage),
            ambition=mut(base.ambition),
            piety=mut(base.piety),
            vengefulness=mut(base.vengefulness),
            patience=mut(base.patience),
            greed=mut(base.greed),
            sociability=mut(base.sociability),
            curiosity=mut(base.curiosity),
            prudence=mut(base.prudence),
            charisma=mut(base.charisma),
            cunning=mut(base.cunning),
            stubbornness=mut(base.stubbornness),
            frugality=mut(base.frugality),
            devotion=mut(base.devotion),
            superstition=mut(base.superstition),
            creativity=mut(base.creativity),
            loyalty=mut(base.loyalty),
        )


@dataclass
class Memory:
    """An NPC's memory of an event. confidence decays over time."""
    year: int
    event_type: str
    participants: list[str] = field(default_factory=list)  # npc_ids
    emotional_valence: int = 0  # -100..+100
    confidence: int = 100  # 0..100
    witnessed_directly: bool = True
    source_npc_id: Optional[str] = None  # if learned via gossip

    def decay(self, years: int = 1) -> None:
        # lose 2-5 confidence per year, harder if not witnessed directly
        rate = 3 if self.witnessed_directly else 6
        self.confidence = max(0, self.confidence - rate * years)


@dataclass
class Relationship:
    affinity: int = 0  # -100..100
    trust: int = 50  # 0..100
    grudges: list[str] = field(default_factory=list)  # contract_ids


@dataclass
class Psychology:
    """Dynamic emotions & Maslow needs hierarchy."""
    grief: int = 0         # 0..100
    jealousy: int = 0      # 0..100
    ambition: int = 50     # 0..100
    paranoia: int = 0      # 0..100
    joy: int = 50          # 0..100
    
    # Maslow Needs (0..100)
    safety_need: int = 80
    belonging_need: int = 70
    esteem_need: int = 60
    self_actualization_need: int = 50


@dataclass
class Body:
    health: int = 100  # 0..100
    constitution: int = 50  # 0..100, genetic baseline
    conditions: list[dict] = field(default_factory=list)
    fertility: int = 80  # 0..100, sex+age dependent
    hunger: int = 50  # 0=starving, 100=full
    fatigue: int = 0  # 0=well rested, 100=exhausted


@dataclass
class Knowledge:
    skills: dict[str, int] = field(default_factory=dict)  # skill_name -> 0..100
    facts_known: list[dict] = field(default_factory=list)


@dataclass
class Status:
    occupation: str = "child"
    household_id: Optional[str] = None
    coins: int = 0
    debt_contract_ids: list[str] = field(default_factory=list)
    inventory_item_ids: list[str] = field(default_factory=list)  # carried items
    last_meal_day: int = -999  # absolute day counter
    last_sleep_day: int = -999
    last_birth_year: int = -999


@dataclass
class Ambition:
    title: str = "Live a Peaceful Life"
    progress: int = 10                     # 0..100%
    quirks: list[str] = field(default_factory=list)
    mood_summary: str = "Content with life in Borough"


@dataclass
class NPC:
    id: str = field(default_factory=_next_npc_id)
    first_name: str = ""
    family_name: str = ""
    sex: Sex = Sex.M
    birth_year: int = 0
    death_year: Optional[int] = None
    cause_of_death: Optional[str] = None
    mother_id: Optional[str] = None
    father_id: Optional[str] = None
    legitimacy: bool = True

    body: Body = field(default_factory=Body)
    anatomy: Anatomy = field(default_factory=Anatomy)
    mind: TraitSet = field(default_factory=TraitSet)
    psychology: Psychology = field(default_factory=Psychology)
    ambition: Ambition = field(default_factory=Ambition)
    memory: list[Memory] = field(default_factory=list)
    knowledge: Knowledge = field(default_factory=Knowledge)
    relationships: dict[str, Relationship] = field(default_factory=dict)  # npc_id -> Relationship
    status: Status = field(default_factory=Status)

    # Player-character markers (default: not a player)
    is_player: bool = False
    player_lifecycle_id: Optional[str] = None  # ties multiple lives together

    @property
    def age(self) -> int:
        return 0  # computed by World via current_year - birth_year

    def age_at(self, year: int) -> int:
        """Real age at a given year."""
        return max(0, year - self.birth_year)

    @property
    def is_alive(self) -> bool:
        return self.death_year is None

    def lifecycle(self, current_year: int) -> LifecycleState:
        return lifecycle_for_age(current_year - self.birth_year)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "family_name": self.family_name,
            "sex": self.sex.value,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "cause_of_death": self.cause_of_death,
            "mother_id": self.mother_id,
            "father_id": self.father_id,
            "legitimacy": self.legitimacy,
            "body": self.body.__dict__,
            "anatomy": self.anatomy.to_dict(),
            "mind": self.mind.__dict__,
            "psychology": self.psychology.__dict__,
            "ambition": self.ambition.__dict__,
            "memory": [m.__dict__ for m in self.memory],
            "knowledge": {"skills": self.knowledge.skills, "facts_known": self.knowledge.facts_known},
            "relationships": {k: v.__dict__ for k, v in self.relationships.items()},
            "status": self.status.__dict__,
            "is_player": self.is_player,
            "player_lifecycle_id": self.player_lifecycle_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NPC":
        n = cls(
            id=d["id"],
            first_name=d["first_name"],
            family_name=d["family_name"],
            sex=Sex(d["sex"]),
            birth_year=d["birth_year"],
            death_year=d.get("death_year"),
            cause_of_death=d.get("cause_of_death"),
            mother_id=d.get("mother_id"),
            father_id=d.get("father_id"),
            legitimacy=d.get("legitimacy", True),
            is_player=d.get("is_player", False),
            player_lifecycle_id=d.get("player_lifecycle_id"),
        )
        b = d.get("body", {})
        # Tolerate missing fields in old saves
        body_kwargs = {k: v for k, v in b.items()
                       if k in Body.__dataclass_fields__}
        n.body = Body(**body_kwargs)
        if "anatomy" in d:
            n.anatomy = Anatomy.from_dict(d["anatomy"])
        m = d.get("mind", {})
        mind_kwargs = {k: v for k, v in m.items()
                       if k in TraitSet.__dataclass_fields__}
        n.mind = TraitSet(**mind_kwargs)
        psy = d.get("psychology", {})
        psy_kwargs = {k: v for k, v in psy.items()
                      if k in Psychology.__dataclass_fields__}
        n.psychology = Psychology(**psy_kwargs)
        amb = d.get("ambition", {})
        amb_kwargs = {k: v for k, v in amb.items()
                      if k in Ambition.__dataclass_fields__}
        n.ambition = Ambition(**amb_kwargs)
        n.memory = [Memory(**md) for md in d.get("memory", [])]
        k = d.get("knowledge", {})
        n.knowledge = Knowledge(skills=k.get("skills", {}), facts_known=k.get("facts_known", []))
        rels = d.get("relationships", {})
        n.relationships = {k: Relationship(**v) for k, v in rels.items()}
        s = d.get("status", {})
        status_kwargs = {k: v for k, v in s.items()
                         if k in Status.__dataclass_fields__}
        n.status = Status(**status_kwargs)
        return n
