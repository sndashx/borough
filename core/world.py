"""World container + town generator. Seed-based, deterministic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union, Any
import hashlib
import random
import secrets
import string

from .npc import NPC, TraitSet, Sex, Relationship
from .building import Building, BuildingType
from .contract import Contract, ContractType
from .item import Item, ItemType


# Length of auto-generated alphanumeric seed. 256 chars from a 62-char
# alphabet = 256^62 ≈ 2^1500 bits of entropy — well past cryptographic need.
DEFAULT_SEED_LENGTH = 256
_SEED_ALPHABET = string.ascii_letters + string.digits


def _coerce_seed(seed: Union[str, int, None]) -> str:
    """Normalize a user-supplied seed to a non-empty string.

    None  -> freshly generated 256-char alphanumeric string.
    int   -> decimal string (preserves user intent on round-trip).
    str   -> returned as-is (empty string is replaced).
    """
    if seed is None:
        return "".join(secrets.choice(_SEED_ALPHABET)
                       for _ in range(DEFAULT_SEED_LENGTH))
    if isinstance(seed, int):
        return str(seed)
    if isinstance(seed, str):
        return seed if seed else "".join(
            secrets.choice(_SEED_ALPHABET) for _ in range(DEFAULT_SEED_LENGTH)
        )
    raise TypeError(f"seed must be str, int, or None; got {type(seed).__name__}")


def seed_to_int(seed: Union[str, int]) -> int:
    """Deterministically map a seed (str or int) to an int for random.Random.

    Uses the first 8 bytes of SHA-256 so the result fits a 64-bit int
    while still being collision-resistant for distinct seeds.
    """
    if isinstance(seed, int):
        return seed & 0xFFFFFFFFFFFFFFFF
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


# Late-medieval name pool — expanded with Anglo-Saxon, Celtic, Germanic, Norse & Frankish pools.
FIRST_NAMES_M = [
    "Aldric", "Bren", "Cedric", "Doran", "Edric", "Falk", "Garrick", "Henrik",
    "Ivor", "Joren", "Kael", "Lothar", "Marek", "Niall", "Orric", "Perrin",
    "Quentin", "Rurik", "Sten", "Tomas", "Ulf", "Vidar", "Wendel", "Yorick",
    "Anselm", "Bartholomew", "Cyprian", "Dietrich", "Everard", "Godfrey",
    "Gideon", "Ignatius", "Julian", "Leopold", "Oswald", "Reynold", "Thether",
    "Aethelstan", "Baldwin", "Corvus", "Dunstan", "Egil", "Frode", "Geoffrey",
    "Hadrian", "Ingvar", "Jaromir", "Konrad", "Leofric", "Magnus", "Norbert",
    "Osric", "Percival", "Roderick", "Sigurd", "Torstein", "Uhtred", "Valdemar",
    "Wilhelm", "Xavier", "Yngvar", "Zephyrus", "Ambrose", "Benedict", "Cuthbert",
    "Dominic", "Emund", "Floki", "Gareth", "Hakon", "Isambard", "Jarl",
]
FIRST_NAMES_F = [
    "Alma", "Bryn", "Cera", "Dalla", "Eira", "Fenna", "Greta", "Hilda",
    "Iona", "Jora", "Kira", "Linnea", "Mira", "Nessa", "Orla", "Petra",
    "Quinn", "Runa", "Sigrid", "Thora", "Una", "Vela", "Wren", "Yara",
    "Adelaide", "Beatrix", "Cecilia", "Genevieve", "Isolde", "Mathilda",
    "Rosamund", "Sibylla", "Theodora", "Ursula", "Wilhelmina", "Ysabel",
    "Aethelgard", "Astrid", "Brunhilda", "Constance", "Dagny", "Elowen",
    "Freya", "Gwyneth", "Helga", "Ingrid", "Freydis", "Kendra", "Lysandra",
    "Maeve", "Nora", "Ottilia", "Rowena", "Swanhilda", "Thalia", "Ulrhild",
    "Valerie", "Winifred", "Xenia", "Yvaine", "Zora", "Agnes", "Bertha",
]
FAMILY_NAMES = [
    "Mendez", "Chen", "Vasquez", "Alder", "Brandt", "Corvin", "Drost",
    "Ebert", "Falk", "Graeb", "Hart", "Iversen", "Jurg", "Kapp", "Lind",
    "Mahr", "Nor", "Olaf", "Parr", "Quist", "Roen", "Sten", "Tarn",
    "Uhr", "Voss", "Wend", "Yost", "Blackwood", "Ironwood", "Oakhaven",
    "Sterling", "Thorne", "Vane", "Winter", "Hawthorne", "Ravenscroft",
    "Ashford", "Bellingham", "Crowley", "Davenport", "Elmhurst", "Fairfax",
    "Grimm", "Holloway", "Kingsley", "Lockwood", "Montague", "Nightingale",
    "Oakhaven", "Pendleton", "Redford", "Somerset", "Timberlake", "Underwood",
    "Vanderbilt", "Westbrook", "Yilmaz", "Zimmerman", "Stonehand", "Swiftfoot",
]

# Occupations an adult NPC can hold.
OCCUPATIONS = [
    "farmer", "miller", "smith", "priest", "innkeeper", "carpenter",
    "weaver", "baker", "butcher", "healer", "midwife", "brewer", "mason",
    "herder", "laborer", "charcoal_burner", "tanner", "potter",
    "apothecary", "scribe", "tailor", "fletcher", "jeweler", "guardsman",
    "minstrel", "bailiff", "alchemist", "cooper", "wheelwright", "trapper",
    "vintner", "scholar",
]

# Skill names — taught by apprenticeship.
SKILL_NAMES = OCCUPATIONS + ["reading", "writing", "alchemy", "archery", "music", "herbalism"]


@dataclass
class World:
    seed: str = "0"
    name: str = "Hollowfield"
    year: int = 0
    day: int = 0  # absolute day counter since town founding
    map_width: int = 64
    map_height: int = 64
    tiles: list[list[dict]] = field(default_factory=list)
    npcs: dict[str, NPC] = field(default_factory=dict)
    buildings: dict[str, Building] = field(default_factory=dict)
    contracts: dict[str, Contract] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    chronicle: list[dict] = field(default_factory=list)

    # Population pressure — what size the simulation is steering toward.
    # Town grows if conditions allow, shrinks if they don't.
    target_population: int = 30

    # Sprint 7: family + ghost subsystems. Lazily created.
    family: Optional["FamilyRegistry"] = None
    ghost: Optional["GhostCausalLedger"] = None

    # Sprint 8 & PhD Deep Subsystems: world-state subsystems.
    reputation: Optional["ReputationLedger"] = None
    weather_state: Optional["WeatherState"] = None
    animals: Optional["AnimalRegistry"] = None
    factions: Optional["FactionRegistry"] = None
    crises: Optional["CrisisLedger"] = None
    religion: Optional["ReligionState"] = None
    dialogue_log: Optional["DialogueLog"] = None
    relics: Optional[Any] = None
    governance: Optional[Any] = None
    cults: Optional[Any] = None
    lore: Optional[Any] = None

    # Player session state (set by play.py; lost on save/load unless we serialize).
    player_id: Optional[str] = None
    flags: dict = field(default_factory=dict)

    def add_npc(self, npc: NPC) -> None:
        self.npcs[npc.id] = npc

    def add_building(self, b: Building) -> None:
        self.buildings[b.id] = b

    def add_contract(self, c: Contract) -> None:
        self.contracts[c.id] = c

    def add_item(self, item: Item) -> None:
        self.items[item.id] = item

    def living_npcs(self) -> list[NPC]:
        return [n for n in self.npcs.values() if n.is_alive]

    def living_count(self) -> int:
        return len(self.living_npcs())

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "name": self.name,
            "year": self.year,
            "day": self.day,
            "map_width": self.map_width,
            "map_height": self.map_height,
            "tiles": self.tiles,
            "npcs": {k: v.to_dict() for k, v in self.npcs.items()},
            "buildings": {k: v.to_dict() for k, v in self.buildings.items()},
            "contracts": {k: v.to_dict() for k, v in self.contracts.items()},
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "chronicle": self.chronicle,
            "target_population": self.target_population,
            "family": self.family.lines if self.family else {},
            "family_feud": {",".join(sorted(k)): v.value for k, v in (self.family.feud.items() if self.family else {})},
            "tombstones": {nid: {"name": t.name, "family_name": t.family_name,
                                 "death_year": t.death_year, "cause": t.cause,
                                 "remembered_by": t.remembered_by}
                           for nid, t in (self.family.tombstone_by_npc.items() if self.family else {})},
            "ghosts": {nid: {"name": g.name, "family_name": g.family_name,
                             "death_year": g.death_year, "cause": g.cause,
                             "remembered_by": g.remembered_by,
                             "remembered_by_ids": list(g.remembered_by_ids),
                             "threshold": g.threshold,
                             "chronicle": g.chronicle}
                       for nid, g in (self.ghost.ghosts.items() if self.ghost else {})},
            "reputation": self.reputation.to_dict() if self.reputation else None,
            "weather_state": self.weather_state.to_dict() if self.weather_state else None,
            "animals": self.animals.to_dict() if self.animals else None,
            "factions": self.factions.to_dict() if self.factions else None,
            "crises": self.crises.to_dict() if self.crises else None,
            "religion": self.religion.to_dict() if self.religion else None,
            "dialogue_log": self.dialogue_log.to_dict() if self.dialogue_log else None,
            "relics": self.relics.to_dict() if self.relics else None,
            "governance": self.governance.to_dict() if self.governance else None,
            "cults": self.cults.to_dict() if self.cults else None,
            "lore": self.lore.to_dict() if self.lore else None,
            "player_id": self.player_id,
            "flags": dict(self.flags),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "World":
        w = cls(
            seed=str(d.get("seed", "0")),
            name=d.get("name", "Hollowfield"),
            year=d.get("year", 0),
            day=d.get("day", 0),
            map_width=d.get("map_width", 64),
            map_height=d.get("map_height", 64),
            target_population=d.get("target_population", 30),
        )
        w.tiles = d.get("tiles", [])
        w.npcs = {k: NPC.from_dict(v) for k, v in d.get("npcs", {}).items()}
        w.buildings = {k: Building.from_dict(v) for k, v in d.get("buildings", {}).items()}
        w.contracts = {k: Contract.from_dict(v) for k, v in d.get("contracts", {}).items()}
        w.items = {k: Item.from_dict(v) for k, v in d.get("items", {}).items()}
        w.chronicle = d.get("chronicle", [])
        # Family + ghost restoration
        from .family import FamilyRegistry, FeudState
        from .ghost import GhostCausalLedger
        w.family = FamilyRegistry()
        for nid, td in d.get("tombstones", {}).items():
            w.family.bury(nid, td["name"], td["family_name"], td["death_year"],
                          td["cause"])
            w.family.tombstone_by_npc[nid].remembered_by = td.get("remembered_by", 0)
        for k, v in d.get("family_feud", {}).items():
            fs = FeudState(v)
            w.family.feud[frozenset(k.split(","))] = fs
        w.ghost = GhostCausalLedger()
        for nid, gd in d.get("ghosts", {}).items():
            g = w.ghost.register_death(
                nid, gd["name"], gd["family_name"], gd["death_year"],
                gd["cause"], threshold=gd.get("threshold", 2),
            )
            g.remembered_by = gd.get("remembered_by", 0)
            g.remembered_by_ids = set(gd.get("remembered_by_ids", []))
            g.chronicle = gd.get("chronicle", [])
        # Sprint 8: load new registries
        from .reputation import ReputationLedger
        from .weather import WeatherState
        from .animal import AnimalRegistry
        from .faction import FactionRegistry
        from .crisis import CrisisLedger
        from .religion import ReligionState
        from .dialogue import DialogueLog
        w.reputation = ReputationLedger()
        if d.get("reputation"):
            w.reputation.from_dict(d["reputation"])
        w.weather_state = WeatherState()
        if d.get("weather_state"):
            w.weather_state.from_dict(d["weather_state"])
        w.animals = AnimalRegistry()
        if d.get("animals"):
            w.animals.from_dict(d["animals"])
        w.factions = FactionRegistry()
        if d.get("factions"):
            w.factions.from_dict(d["factions"])
        w.crises = CrisisLedger()
        if d.get("crises"):
            w.crises.from_dict(d["crises"])
        w.religion = ReligionState()
        if d.get("religion"):
            w.religion.from_dict(d["religion"])
        w.dialogue_log = DialogueLog()
        if d.get("dialogue_log"):
            w.dialogue_log.from_dict(d["dialogue_log"])

        from .relic import RelicRegistry
        from .governance import GovernanceSystem
        from .cult import CultRegistry
        from .lore import LoreRegistry

        w.relics = RelicRegistry(world=w)
        if d.get("relics"):
            w.relics = RelicRegistry.from_dict(d["relics"], world=w)
        w.governance = GovernanceSystem(world=w)
        if d.get("governance"):
            w.governance = GovernanceSystem.from_dict(d["governance"], world=w)
        w.cults = CultRegistry(world=w)
        if d.get("cults"):
            w.cults = CultRegistry.from_dict(d["cults"], world=w)
        w.lore = LoreRegistry(world=w)
        if d.get("lore"):
            w.lore = LoreRegistry.from_dict(d["lore"], world=w)
        w.player_id = d.get("player_id")
        w.flags = dict(d.get("flags", {}))
        return w


def _make_tile(terrain: str) -> dict:
    return {
        "terrain": terrain,
        "building_id": None,
        "items": [],
        "corpses": [],
        "stains": [],
        "wear": 0.0,
    }


def _assign_npc_ambition_and_quirks(npc: NPC, rng: random.Random) -> None:
    AMBITIONS = [
        "Win Election to Town Council",
        "Forge a Legendary Masterwork Relic",
        "Amass 200 Coppers Wealth",
        "Erect a Sacred Temple Shrine",
        "Raise 3 Heir Children",
        "Uncover Underground Secret Societies",
        "Master Craftsmanship Trade",
    ]
    QUIRKS = [
        "Night Owl", "Miserly", "Gourmand", "Gossiper", "Zealot",
        "Melancholic", "Poet", "Brawler", "Superstitious", "Charitable"
    ]
    npc.ambition.title = rng.choice(AMBITIONS)
    npc.ambition.progress = rng.randint(5, 30)
    npc.ambition.quirks = rng.sample(QUIRKS, k=rng.randint(1, 3))
    npc.ambition.mood_summary = f"Content with life in House {npc.family_name}"


def _carve_tiles(w: World, rng: random.Random) -> None:
    w.tiles = [[_make_tile("grass") for _ in range(w.map_width)] for _ in range(w.map_height)]
    # Central village square
    cx, cy = w.map_width // 2, w.map_height // 2
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            x, y = cx + dx, cy + dy
            if 0 <= x < w.map_width and 0 <= y < w.map_height:
                w.tiles[y][x]["terrain"] = "cobble"
    # A main road north-south
    for y in range(4, w.map_height):
        w.tiles[y][cx]["terrain"] = "dirt"
        w.tiles[y][cx - 1]["terrain"] = "dirt"
    # Farmland around the village
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            x, y = cx + dx, cy + dy
            if 0 <= x < w.map_width and 0 <= y < w.map_height:
                if abs(dx) > 4 and abs(dy) > 4 and w.tiles[y][x]["terrain"] == "grass":
                    w.tiles[y][x]["terrain"] = "farmland"
    """Carve a 64x64 map. Grass with a central village, water to the north, paths."""
    w.tiles = [[_make_tile("grass") for _ in range(w.map_width)] for _ in range(w.map_height)]
    # River along the top
    for x in range(w.map_width):
        w.tiles[2][x]["terrain"] = "water"
        w.tiles[3][x]["terrain"] = "water"
    # Central village square
    cx, cy = w.map_width // 2, w.map_height // 2
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            x, y = cx + dx, cy + dy
            if 0 <= x < w.map_width and 0 <= y < w.map_height:
                w.tiles[y][x]["terrain"] = "cobble"
    # A main road north-south
    for y in range(4, w.map_height):
        w.tiles[y][cx]["terrain"] = "dirt"
        w.tiles[y][cx - 1]["terrain"] = "dirt"
    # Farmland around the village
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            x, y = cx + dx, cy + dy
            if 0 <= x < w.map_width and 0 <= y < w.map_height:
                if abs(dx) > 4 and abs(dy) > 4 and w.tiles[y][x]["terrain"] == "grass":
                    w.tiles[y][x]["terrain"] = "farmland"


def generate_world(seed=None, name: str = "Hollowfield", year: int = 0, pop: int = 30) -> World:
    """Generate a fresh town with `pop` initial inhabitants.

    `seed` may be:
      - None  -> a fresh 256-char alphanumeric seed is generated
      - int   -> stored as its decimal string
      - str   -> used verbatim (any length, any alphabet)
    The internal RNG is seeded by SHA-256(seed)[:8] -> int.
    """
    seed_str = _coerce_seed(seed)
    rng = random.Random(seed_to_int(seed_str))
    w = World(seed=seed_str, name=name, year=year, target_population=pop)
    # Sprint 7: family + ghost subsystems
    from .family import FamilyRegistry
    from .ghost import GhostCausalLedger
    w.family = FamilyRegistry()
    w.ghost = GhostCausalLedger()
    # Sprint 8: world-state subsystems
    from .reputation import ReputationLedger
    from .weather import WeatherState
    from .animal import AnimalRegistry
    from .faction import FactionRegistry
    from .crisis import CrisisLedger
    from .religion import ReligionState
    from .dialogue import DialogueLog
    w.reputation = ReputationLedger()
    w.weather_state = WeatherState()
    w.animals = AnimalRegistry()
    w.factions = FactionRegistry()
    w.crises = CrisisLedger()
    w.religion = ReligionState()
    w.dialogue_log = DialogueLog()

    from .relic import RelicRegistry
    from .governance import GovernanceSystem
    from .cult import CultRegistry
    from .lore import LoreRegistry

    w.relics = RelicRegistry(world=w)
    w.governance = GovernanceSystem(world=w)
    w.cults = CultRegistry(world=w)
    w.lore = LoreRegistry(world=w)

    _carve_tiles(w, rng)

    # Buildings — one per NPC roughly, weighted toward houses + key services.
    building_plan = []
    house_count = max(8, pop)
    building_plan.extend([(BuildingType.HOUSE, f"house_{i}") for i in range(house_count)])
    building_plan.extend([
        (BuildingType.CHURCH, "old_church"),
        (BuildingType.TAVERN, "the_wet_barrel"),
        (BuildingType.MILL, "watermill"),
        (BuildingType.SMITHY, "smithy"),
        (BuildingType.MARKET, "market_square"),
        (BuildingType.WELL, "village_well"),
        (BuildingType.GRANARY, "granary"),
        (BuildingType.BARN, "barn_east"),
        (BuildingType.BARN, "barn_west"),
    ])

    # Place buildings near the central square
    cx, cy = w.map_width // 2, w.map_height // 2
    placed = 0
    for btype, bname in building_plan:
        # spiral outward
        radius = 2 + placed // 4
        angle = (placed * 1.3) % 6.28
        bx = cx + int(radius * (1 if (placed // 4) % 2 == 0 else -1) * 1.2) + rng.randint(-1, 1)
        by = cy + radius + rng.randint(-1, 1)
        bx = max(4, min(w.map_width - 5, bx))
        by = max(6, min(w.map_height - 5, by))
        b = Building(type=btype, name=bname, x=bx, y=by, footprint=[(0, 0), (1, 0), (0, 1), (1, 1)])
        w.add_building(b)
        if 0 <= bx < w.map_width and 0 <= by < w.map_height:
            w.tiles[by][bx]["building_id"] = b.id
            w.tiles[by][bx + 1]["building_id"] = b.id if bx + 1 < w.map_width else None
            w.tiles[by + 1][bx]["building_id"] = b.id if by + 1 < w.map_height else None
        placed += 1

    # Generate `pop` NPCs spanning ages 0..70. We first create adults so that
    # children can be assigned to them as offspring (sensible family structure).
    adults = []
    children = []
    # Phase 1: adults (ages 18-40) — these are the prime childbearers/workers
    adult_target = max(int(pop * 0.65), 12)
    for i in range(adult_target):
        # Bias sex toward F so there are many potential mothers
        sex = Sex.F if rng.random() < 0.55 else Sex.M
        age = rng.randint(18, 40)
        first = rng.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
        family = rng.choice(FAMILY_NAMES)
        n = NPC(
            first_name=first, family_name=family, sex=sex, birth_year=year - age,
        )
        n.mind = TraitSet.random(rng)
        n.body.constitution = rng.randint(30, 80)
        n.body.health = 100
        n.body.fertility = rng.randint(40, 90)
        n.body.hunger = rng.randint(60, 100)
        n.body.fatigue = rng.randint(0, 30)
        # Assign occupation
        n.status.occupation = rng.choice(OCCUPATIONS)
        if n.status.occupation == "priest":
            n.knowledge.skills["reading"] = max(50, n.knowledge.skills.get("reading", 30))
        # Assign household
        houses = [b for b in w.buildings.values() if b.type == BuildingType.HOUSE]
        if houses:
            house = rng.choice(houses)
            n.status.household_id = house.id
            if n.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(n.id)
        n.status.coins = rng.randint(0, 20)
        _assign_npc_ambition_and_quirks(n, rng)
        w.add_npc(n)
        adults.append(n)

    # Phase 2: elders (ages 56-75) — small fraction
    elder_count = max(1, pop // 12)
    for i in range(elder_count):
        sex = Sex.M if rng.random() < 0.51 else Sex.F
        age = rng.randint(56, 75)
        first = rng.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
        family = rng.choice(FAMILY_NAMES)
        n = NPC(
            first_name=first, family_name=family, sex=sex, birth_year=year - age,
        )
        n.mind = TraitSet.random(rng)
        n.body.constitution = rng.randint(30, 80)
        n.body.health = rng.randint(40, 80)
        n.body.fertility = 0
        n.body.hunger = rng.randint(60, 100)
        n.body.fatigue = rng.randint(0, 30)
        n.status.occupation = rng.choice(OCCUPATIONS) if rng.random() < 0.3 else "laborer"
        houses = [b for b in w.buildings.values() if b.type == BuildingType.HOUSE]
        if houses:
            house = rng.choice(houses)
            n.status.household_id = house.id
            if n.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(n.id)
        n.status.coins = rng.randint(5, 30)
        _assign_npc_ambition_and_quirks(n, rng)
        w.add_npc(n)
        adults.append(n)

    # Phase 3: adolescents (ages 13-17)
    adolescent_count = max(1, pop // 10)
    for i in range(adolescent_count):
        sex = Sex.M if rng.random() < 0.51 else Sex.F
        age = rng.randint(13, 17)
        first = rng.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
        family = rng.choice(FAMILY_NAMES)
        n = NPC(
            first_name=first, family_name=family, sex=sex, birth_year=year - age,
        )
        n.mind = TraitSet.random(rng)
        n.body.constitution = rng.randint(30, 80)
        n.body.health = 100
        n.body.fertility = 0
        n.body.hunger = rng.randint(60, 100)
        n.body.fatigue = rng.randint(0, 30)
        n.status.occupation = "child"
        houses = [b for b in w.buildings.values() if b.type == BuildingType.HOUSE]
        if houses:
            house = rng.choice(houses)
            n.status.household_id = house.id
            if n.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(n.id)
        _assign_npc_ambition_and_quirks(n, rng)
        w.add_npc(n)
        children.append(n)

    # Phase 4: children (ages 4-12) and infants (0-3) — assigned to adult mothers
    remaining = pop - len(adults) - len(children)
    adult_females = [n for n in adults if n.sex == Sex.F and n.body.fertility > 0]
    for i in range(remaining):
        sex = Sex.M if rng.random() < 0.51 else Sex.F
        # Skew toward children, not infants
        if rng.random() < 0.3:
            age = rng.randint(0, 3)
        else:
            age = rng.randint(4, 12)
        first = rng.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
        family = rng.choice(FAMILY_NAMES)
        # Assign mother
        mother = rng.choice(adult_females) if adult_females and age < 13 else None
        n = NPC(
            first_name=first, family_name=family, sex=sex, birth_year=year - age,
            mother_id=mother.id if mother else None,
            father_id=None,  # we don't track fathers in initial pop
            legitimacy=True,
        )
        n.mind = TraitSet.random(rng)
        n.body.constitution = rng.randint(30, 80)
        n.body.health = 100
        n.body.fertility = 0
        n.body.hunger = rng.randint(70, 100)
        n.body.fatigue = rng.randint(0, 20)
        n.status.occupation = "child"
        # Children live with mother
        if mother and mother.status.household_id:
            n.status.household_id = mother.status.household_id
            house = w.buildings.get(mother.status.household_id)
            if house and n.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(n.id)
        else:
            houses = [b for b in w.buildings.values() if b.type == BuildingType.HOUSE]
            if houses:
                house = rng.choice(houses)
                n.status.household_id = house.id
                if n.id not in house.occupant_npc_ids:
                    house.occupant_npc_ids.append(n.id)
        w.add_npc(n)
        children.append(n)
        # Assign occupation (already set to "child" above for the under-14 branch;
        # 14-17 adolescents get apprentice/child, 18+ an occupation).
        if 14 <= age < 18:
            n.status.occupation = "apprentice" if rng.random() < 0.5 else "child"
        elif age >= 18:
            n.status.occupation = rng.choice(OCCUPATIONS)
            if n.status.occupation == "priest":
                n.knowledge.skills["reading"] = max(50, n.knowledge.skills.get("reading", 30))
        # Adults get coins; children don't.
        if age >= 18:
            n.status.coins = rng.randint(0, 20)
            adults.append(n)

    # Seed initial seed-grain into the granary so the economy has something.
    granary = next((b for b in w.buildings.values() if b.type == BuildingType.GRANARY), None)
    if granary:
        for _ in range(60):
            it = Item(type=ItemType.GRAIN, weight=1.0, quality=rng.randint(40, 80), building_id=granary.id)
            w.add_item(it)
            granary.item_ids.append(it.id)

    # Establish initial relationships — every adult knows 2-4 others.
    for n in adults:
        others = [o for o in adults if o.id != n.id]
        k = min(len(others), rng.randint(2, 4))
        for o in rng.sample(others, k):
            if o.id not in n.relationships:
                n.relationships[o.id] = Relationship(
                    affinity=rng.randint(-30, 60),
                    trust=rng.randint(30, 70),
                )

    # Seed initial marriages among adults. Pair up roughly 60% of adults.
    from .contract import Contract, ContractType, ContractStatus
    unmarried_m = [n for n in adults if n.sex == Sex.M]
    unmarried_f = [n for n in adults if n.sex == Sex.F]
    rng.shuffle(unmarried_m)
    rng.shuffle(unmarried_f)
    pair_count = min(len(unmarried_m), len(unmarried_f), max(8, len(adults) // 2))
    for i in range(pair_count):
        m, f = unmarried_m[i], unmarried_f[i]
        c = Contract(
            type=ContractType.MARRIAGE,
            parties=[m.id, f.id],
            year_created=year - rng.randint(1, 15),
            status=ContractStatus.ACTIVE,
            terms={"household_id": m.status.household_id or f.status.household_id},
            notable=False,
        )
        w.add_contract(c)
        # Spouses co-house — remove from old house first to avoid duplicates
        if m.status.household_id:
            f.status.household_id = m.status.household_id
            # Remove f from her old house
            if f.status.household_id:  # was set above
                pass
            # Find f's old house and remove her
            for old_house in w.buildings.values():
                if f.id in old_house.occupant_npc_ids and old_house.id != m.status.household_id:
                    old_house.occupant_npc_ids.remove(f.id)
                    break
            house = w.buildings.get(m.status.household_id)
            if house and f.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(f.id)
        elif f.status.household_id:
            m.status.household_id = f.status.household_id
            for old_house in w.buildings.values():
                if m.id in old_house.occupant_npc_ids and old_house.id != f.status.household_id:
                    old_house.occupant_npc_ids.remove(m.id)
                    break
            house = w.buildings.get(f.status.household_id)
            if house and m.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(m.id)
        # Couple knows each other well
        m.relationships[f.id] = Relationship(
            affinity=rng.randint(40, 80), trust=rng.randint(60, 90)
        )
        f.relationships[m.id] = Relationship(
            affinity=rng.randint(40, 80), trust=rng.randint(60, 90)
        )

    # Assign children to married couples: pick each unmarried child and assign to a random house.
    married_households = set()
    for c in w.contracts.values():
        if c.type == ContractType.MARRIAGE and c.status == ContractStatus.ACTIVE:
            if c.terms.get("household_id"):
                married_households.add(c.terms["household_id"])
    for c in children:
        if married_households:
            hid = rng.choice(list(married_households))
            # Remove from old house first
            for old_house in w.buildings.values():
                if c.id in old_house.occupant_npc_ids and old_house.id != hid:
                    old_house.occupant_npc_ids.remove(c.id)
                    break
            c.status.household_id = hid
            house = w.buildings.get(hid)
            if house and c.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(c.id)

    # Seed a generous food reserve in every house so initial NPCs don't starve.
    # Done AFTER all occupant assignments so the count is correct.
    for b in w.buildings.values():
        if b.type == BuildingType.HOUSE:
            occupants = max(1, len(b.occupant_npc_ids))
            food_count = occupants * 60  # 60 days of food per occupant
            for _ in range(food_count):
                it = Item(type=ItemType.GRAIN, weight=1.0, quality=rng.randint(30, 70), building_id=b.id)
                w.add_item(it)
                b.item_ids.append(it.id)
            b.food_count_cache = food_count  # Initialize cache for perf

    # Seed a founding chronicle entry.
    w.chronicle.append({
        "year": year,
        "type": "founding",
        "summary": f"The village of {name} is founded. {pop} souls take root.",
    })

    # Sprint 8: seed animals in barns, factions, initial weather.
    from .animal import Species
    barns = [b for b in w.buildings.values() if b.type == BuildingType.BARN]
    houses = [b for b in w.buildings.values() if b.type == BuildingType.HOUSE]
    for b in barns:
        # 4-8 chickens, 1-2 pigs per barn
        for _ in range(rng.randint(4, 8)):
            w.animals.add(Species.CHICKEN, building_id=b.id, born_year=year - rng.randint(0, 3))
        for _ in range(rng.randint(1, 2)):
            w.animals.add(Species.PIG, building_id=b.id, born_year=year - rng.randint(0, 4))
    if not barns and houses:
        # No barns? Put a few chickens in random houses
        for h in rng.sample(houses, min(3, len(houses))):
            for _ in range(rng.randint(2, 4)):
                w.animals.add(Species.CHICKEN, building_id=h.id, born_year=year)
    # Seed factions
    w.factions.seed_builtin(w)
    # Initial weather: roll for day 0
    w.weather_state.advance_day(year, 0)

    return w
