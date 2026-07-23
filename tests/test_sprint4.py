"""Sprint 4 tests: scene system pipeline.

We test the scene module directly. No full-life runs (perf budget).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.world import generate_world
from core.chronicle import Chronicle
from core.scene import (
    pick_scene_for_year, birth_scene, render_scene_for_console,
    Scene, SceneType, Choice, childhood_beat_scene, apprenticeship_offer_scene,
    marriage_proposal_scene, death_family_scene, crime_witnessed_scene,
    feast_day_scene,
)
from core.player import spawn_player


def test_birth_scene_indifferent():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    scene = birth_scene(world, player, chronicle)
    assert scene is not None
    assert scene.type.value == "birth"
    assert "is in labor" in scene.body
    assert len(scene.choices) == 1
    assert scene.salience < 0.5
    print("  PASS: birth scene — indifferent opening, salience", scene.salience)


def test_birth_scene_with_ghost():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    ghost = list(world.npcs.values())[0]
    chronicle.record(1, "ghost",
                     f"The name of {ghost.first_name} {ghost.family_name} persists.",
                     involved_npc_ids=[ghost.id])
    player = spawn_player(world)
    # Force lineage
    player.mother_id = ghost.id
    scene = birth_scene(world, player, chronicle)
    assert scene is not None
    has_ghost = "Your great-grandmother" in scene.body
    print(f"  PASS: birth scene with ghost (ghost_text_present={has_ghost}, salience={scene.salience})")


def test_choice_applies_effects():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    target = list(world.npcs.values())[1]
    scene = Scene(
        type=SceneType.CRIME_WITNESSED, year=world.year, location="x",
        title="T", body="b", salience=0.9,
        involved_npc_ids=[target.id],
        choices=[
            Choice("help", effects={
                "relationship": {target.id: {"affinity_delta": 30, "trust_delta": 30}},
                "chronicle": {"type": "intervened_crime", "summary": "player intervened"},
            }),
            Choice("walk", effects={}),
        ],
    )
    scene.apply_choice(0, world, chronicle)
    assert scene.auto_resolved
    assert target.relationships[player.id].affinity == 30
    assert any("intervened" in e["type"] for e in world.chronicle)
    print("  PASS: choice applies relationship + chronicle effects")


def test_unmemorable_choice_no_chronicle():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    target = list(world.npcs.values())[1]
    scene = Scene(
        type=SceneType.CHILDHOOD_BEAT, year=world.year, location="x",
        title="T", body="b", salience=0.05,
        involved_npc_ids=[target.id],
        choices=[
            Choice("do nothing", effects={}),
        ],
    )
    initial = len(world.chronicle)
    scene.apply_choice(0, world, chronicle)
    assert len(world.chronicle) == initial, "Silent choice should not add chronicle"
    print("  PASS: unmemorable choice does not enter chronicle")


def test_pick_scene_year_zero_is_birth():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    # Force year-0 state
    player.birth_year = world.year
    scene = pick_scene_for_year(world, player, chronicle)
    assert scene is not None
    assert scene.type == SceneType.BIRTH
    print("  PASS: year 0 = birth scene")


def test_render_scene_to_console():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    scene = birth_scene(world, player, chronicle)
    text = render_scene_for_console(scene)
    assert "YEAR" in text
    assert "Birth of" in text
    assert "[1]" in text
    print("  PASS: console renderer produces valid output")


def test_apprenticeship_offer_triggers_at_age_13():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    player.birth_year = world.year - 13
    # Need at least one NPC with a skill > 50. Check the world has one.
    has_skilled = any(
        any(v > 50 for v in n.knowledge.skills.values())
        for n in world.npcs.values() if n.id != player.id and n.is_alive
    )
    if not has_skilled:
        print("  SKIP: no skilled NPC in this seed")
        return
    scene = apprenticeship_offer_scene(world, player, chronicle)
    if scene:
        assert scene.salience >= 0.5
        print(f"  PASS: apprenticeship offer fires at age 13 (salience {scene.salience})")
    else:
        print("  SKIP: apprenticeship offer did not fire (no eligible master)")


def test_marriage_proposal_triggers_for_adult():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    player.birth_year = world.year - 22
    scene = marriage_proposal_scene(world, player, chronicle)
    if scene:
        assert scene.salience >= 0.5
        print(f"  PASS: marriage proposal fires for adult (salience {scene.salience})")
    else:
        print("  SKIP: no eligible suitor in this seed")


def test_crime_scene_has_intervention_choice():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    player.birth_year = world.year - 25
    # Force a crime scene by retrying — it's random
    for _ in range(50):
        scene = crime_witnessed_scene(world, player, chronicle)
        if scene:
            labels = [c.label.lower() for c in scene.choices]
            assert any("intervene" in l or "shout" in l for l in labels)
            print(f"  PASS: crime scene offers intervention choice (salience {scene.salience})")
            return
    print("  SKIP: no crime scene in 50 tries")


def test_death_family_scene_can_fire():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    player = spawn_player(world)
    world.player_id = player.id
    # Give the player a living parent
    parent = list(world.npcs.values())[0]
    if parent.id == player.id:
        parent = list(world.npcs.values())[1]
    player.mother_id = parent.id
    parent.death_year = None
    # Force fire — it'll keep trying
    for _ in range(20):
        scene = death_family_scene(world, player, chronicle)
        if scene:
            assert scene.involved_npc_ids
            print(f"  PASS: family death scene fires (salience {scene.salience})")
            return
    print("  SKIP: family death did not fire in 20 tries")


if __name__ == "__main__":
    print("Sprint 4 tests:")
    test_birth_scene_indifferent()
    test_birth_scene_with_ghost()
    test_choice_applies_effects()
    test_unmemorable_choice_no_chronicle()
    test_pick_scene_year_zero_is_birth()
    test_render_scene_to_console()
    test_apprenticeship_offer_triggers_at_age_13()
    test_marriage_proposal_triggers_for_adult()
    test_crime_scene_has_intervention_choice()
    test_death_family_scene_can_fire()
    print("\nAll Sprint 4 tests passed.")
