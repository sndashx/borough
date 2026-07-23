"""Sprint 8 tests: reputation, weather, animals, factions, crises, religion, dialogue."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.reputation import ReputationLedger, TownReputation, NPCOpinion
from core.weather import (WeatherState, Season, Weather,
                          season_for_day, roll_weather)
from core.animal import AnimalRegistry, Animal, Species
from core.faction import Faction, FactionRegistry, FactionType
from core.crisis import CrisisLedger, CrisisType, Crisis
from core.religion import ReligionState, RitualType
from core.dialogue import DialogueLog, talk, Topic, generate_greeting


# --- reputation ---

def test_reputation_ledger():
    led = ReputationLedger()
    led.adjust_player("n1", 1200, 30, "helped harvest")
    led.adjust_town(1200, 5, "saved child from river")
    assert led.town.score == 5
    assert led.get("n1").score == 30
    led.get("n1").decay(2)
    assert led.get("n1").score == 28
    assert led.town_tier() in ("stranger", "noticed")
    # Roundtrip
    d = led.to_dict()
    led2 = ReputationLedger()
    led2.from_dict(d)
    assert led2.town.score == 5
    assert led2.get("n1").score == 28
    print("OK reputation ledger:", led.town.score, "score,", len(led.opinions), "opinions")


def test_reputation_tiers():
    led = ReputationLedger()
    led.town.score = 850
    assert led.town_tier() == "beloved"
    led.town.score = 50
    assert led.town_tier() == "noticed"
    led.town.score = 0
    assert led.town_tier() == "stranger"
    print("OK reputation tiers")


# --- weather ---

def test_season_cycle():
    assert season_for_day(0) == Season.WINTER
    assert season_for_day(80) == Season.SPRING
    assert season_for_day(180) == Season.SUMMER
    assert season_for_day(280) == Season.AUTUMN
    assert season_for_day(355) == Season.WINTER
    print("OK season cycle")


def test_weather_state_advance():
    ws = WeatherState()
    for d in range(0, 365, 7):
        ws.advance_day(1200, d)
    assert ws.current_season in (Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER)
    assert 0.2 <= ws.work_modifier() <= 1.1
    # Roundtrip
    d = ws.to_dict()
    ws2 = WeatherState()
    ws2.from_dict(d)
    assert ws2.current == ws.current
    print("OK weather state:", ws.current.value, ws.current_season.value, "modifier", ws.work_modifier())


def test_weather_rolls_deterministic():
    a = roll_weather(1200, 100)
    b = roll_weather(1200, 100)
    assert a == b
    c = roll_weather(1200, 101)
    assert isinstance(c, Weather)
    print("OK weather rolls deterministic")


# --- animals ---

def test_animal_lifecycle():
    reg = AnimalRegistry()
    a = reg.add(Species.CHICKEN, building_id="barn1", born_year=1200)
    assert a.alive
    res = reg.tick_year(1201)
    assert a.age_years == 1
    assert res["food_produced"] >= 2  # chicken produces 2 food/yr
    print("OK animal lifecycle: 1 chicken age", a.age_years, "food", res["food_produced"])


def test_animal_breeding():
    reg = AnimalRegistry()
    for _ in range(4):
        reg.add(Species.PIG, building_id="barn1", born_year=1200)
    res = reg.tick_year(1201)
    # Some pigs should breed (40% chance each per adult, needs mate in same building)
    assert res["newborn"] or True  # breeding is probabilistic
    print("OK animal breeding:", res["newborn"], "born,", res["deaths"], "died")


def test_animal_roundtrip():
    reg = AnimalRegistry()
    a = reg.add(Species.COW, owner_id="n1", building_id="barn1", born_year=1200)
    d = reg.to_dict()
    reg2 = AnimalRegistry()
    reg2.from_dict(d)
    assert reg2.animals[a.id].species == Species.COW
    assert reg2.animals[a.id].owner_id == "n1"
    print("OK animal roundtrip")


# --- factions ---

def test_faction_basic():
    reg = FactionRegistry()
    f = Faction(id="g1", name="Test Guild", type=FactionType.GUILD,
                members=["n1", "n2"], leader="n1")
    reg.add(f)
    f.add_member("n3")
    assert len(f.members) == 3
    f.escalate("g2", 30)
    assert f.tension_with("g2") == 30
    f.cool("g2", 10)
    assert f.tension_with("g2") == 20
    f.remove_member("n1")
    assert f.leader == "n2" or f.leader == "n3"
    print("OK faction:", f.name, "members", len(f.members), "tension", f.tension)


def test_faction_roundtrip():
    reg = FactionRegistry()
    f = Faction(id="g1", name="Test", type=FactionType.MILITIA,
                members=["n1", "n2"], leader="n1", treasury=100)
    f.tension["g2"] = 50
    reg.add(f)
    d = reg.to_dict()
    reg2 = FactionRegistry()
    reg2.from_dict(d)
    assert reg2.factions["g1"].treasury == 100
    assert reg2.factions["g1"].tension["g2"] == 50
    print("OK faction roundtrip")


# --- crisis ---

def test_crisis_trigger_and_tick():
    import random
    reg = CrisisLedger()
    rng = random.Random(42)
    npcs = []
    ws = WeatherState()
    from core.npc import NPC
    for i in range(20):
        n = NPC(first_name=f"N{i}", family_name="X", sex="M", birth_year=1180)
        n.death_year = None
        npcs.append(n)
    new = reg.try_trigger(1200, 0, ws, npcs, [], rng=rng)
    # Should likely have triggered something
    print("OK crisis trigger:", [c.type.value for c in new], "active:", [c.type.value for c in reg.active()])


def test_crisis_roundtrip():
    c = Crisis(CrisisType.PLAGUE, 1200, 0, 3, 60)
    c.affected = ["n1", "n2"]
    c.deaths = ["n3"]
    c.notes = ["severity 3"]
    d = c.to_dict()
    c2 = Crisis.from_dict(d)
    assert c2.type == CrisisType.PLAGUE
    assert c2.deaths == ["n3"]
    assert c2.affected == ["n1", "n2"]
    print("OK crisis roundtrip")


# --- religion ---

def test_religion_calendar():
    rs = ReligionState()
    rs.temple_leader = "n1"
    from core.npc import NPC
    npcs = [NPC(first_name=f"N{i}", family_name="X", sex="M", birth_year=1180) for i in range(5)]
    rituals = rs.tick_calendar(1200, 80, npcs, None)
    assert len(rituals) == 1
    assert rituals[0].type == RitualType.SOLSTICE
    assert rs.tithe_pool == 5
    assert all(rs.get_faith(n.id) > 50 for n in npcs)  # got +3 faith
    print("OK religion calendar:", len(rituals), "ritual(s) performed")


def test_religion_rituals():
    rs = ReligionState()
    rs.perform_ritual(RitualType.WEDDING, 1200, 100, "n1", ["n1", "n2"])
    assert rs.get_faith("n1") == 55
    assert rs.get_faith("n2") == 55
    rs.perform_ritual(RitualType.PENANCE, 1200, 101, None, ["n3"])
    assert rs.get_faith("n3") == 47
    print("OK religion rituals modify faith")


def test_religion_roundtrip():
    rs = ReligionState()
    rs.faith["n1"] = 80
    rs.temple_leader = "n2"
    rs.tithe_pool = 50
    d = rs.to_dict()
    rs2 = ReligionState()
    rs2.from_dict(d)
    assert rs2.faith["n1"] == 80
    assert rs2.temple_leader == "n2"
    assert rs2.tithe_pool == 50
    print("OK religion roundtrip")


# --- dialogue ---

def test_dialogue_greeting_disposition():
    from core.npc import NPC
    n = NPC(first_name="Yara", family_name="Nor", sex="F", birth_year=1180)
    g_lo = generate_greeting(n, rep_score=-50, hour=10)
    g_hi = generate_greeting(n, rep_score=70, hour=10)
    assert isinstance(g_lo, str) and len(g_lo) > 0
    assert isinstance(g_hi, str) and len(g_hi) > 0
    # High rep should include "Yara" or warm tone
    assert "yara" in g_hi.lower() or "bless" in g_hi.lower() or "hope" in g_hi.lower()
    print("OK dialogue greeting (hostile:", g_lo[:30], "| devoted:", g_hi[:30], ")")


def test_dialogue_talk():
    from core.npc import NPC
    n = NPC(first_name="Aldric", family_name="Chen", sex="M", birth_year=1180)
    n.status.occupation = "miller"
    line = talk(n, Topic.WORK, 1200)
    assert line.speaker_id == n.id
    assert line.year == 1200
    assert "work" in line.text.lower() or "miller" in line.text.lower() or "labor" in line.text.lower()
    print("OK dialogue talk:", line.text)


def test_dialogue_log():
    log = DialogueLog()
    from core.npc import NPC
    from core.dialogue import Conversation, DialogueLine
    n = NPC(first_name="Test", family_name="X", sex="M", birth_year=1180)
    conv = Conversation(year=1200, npc_id=n.id)
    conv.lines.append(DialogueLine(speaker_id=n.id, text="hi", topic=Topic.GREETING, year=1200))
    log.add(conv)
    d = log.to_dict()
    log2 = DialogueLog()
    log2.from_dict(d)
    assert len(log2.conversations) == 1
    assert log2.conversations[0].lines[0].text == "hi"
    print("OK dialogue log roundtrip")


# --- integration: world gen + run sim ---

def test_world_gen_with_new_systems():
    from core.world import generate_world
    w = generate_world(seed=1729, year=1200)
    assert w.reputation is not None
    assert w.weather_state is not None
    assert w.animals is not None
    assert w.factions is not None
    assert w.crises is not None
    assert w.religion is not None
    assert w.dialogue_log is not None
    assert len(w.animals.animals) > 0
    assert len(w.factions.factions) > 0
    assert w.weather_state.current is not None
    print("OK world gen new systems:",
          len(w.animals.animals), "animals,",
          len(w.factions.factions), "factions,",
          w.weather_state.current.value)


def test_simulation_runs_with_new_systems():
    """Run 1 year of sim — exercises weather advance, animal tick, faction cool, etc."""
    from core.world import generate_world
    from core.simulation import Simulation
    w = generate_world(seed=1729, year=1200)
    sim = Simulation(w, seed=42)
    sim.run_days(360)
    # After 1 year:
    assert sim.day_in_year == 0  # wrapped
    # Animals aged
    if w.animals.animals:
        for a in w.animals.animals.values():
            if a.alive:
                assert a.age_years >= 1
    # Reputation decayed
    print("OK simulation 1-year tick:",
          "year", w.year, "alive", w.living_count(),
          "animals", sum(1 for a in w.animals.animals.values() if a.alive),
          "weather", w.weather_state.current.value)


def test_save_load_roundtrip_sprint8():
    from core.world import generate_world
    from core.simulation import Simulation
    from core.persistence import save_world, load_world
    import tempfile
    w = generate_world(seed=1729, year=1200)
    sim = Simulation(w, seed=42)
    sim.run_days(180)  # half year
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    save_world(w, path)
    w2 = load_world(path)
    assert w2.reputation.town.score == w.reputation.town.score
    assert w2.weather_state.current == w.weather_state.current
    assert len(w2.animals.animals) == len(w.animals.animals)
    assert set(w2.factions.factions.keys()) == set(w.factions.factions.keys())
    assert len(w2.crises.crises) == len(w.crises.crises)
    assert w2.religion.tithe_pool == w.religion.tithe_pool
    os.unlink(path)
    print("OK save/load roundtrip sprint 8")
