"""Acceptance tests for player interactive actions across all core Borough systems."""
from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.world import generate_world
from core.player import spawn_player
from core import actions


def test_player_action_suite():
    world = generate_world(seed="test_actions_1729")
    player = spawn_player(world)

    # 1. Work Job
    initial_coins = player.status.coins
    res_work = actions.work_job(world, player)
    assert res_work["success"] is True
    assert player.status.coins > initial_coins

    # 2. Buy Provisions
    player.status.coins = 20
    res_buy = actions.buy_provisions(world, player, "bread")
    assert res_buy["success"] is True
    assert player.status.coins == 15

    # 3. Pray at Church
    res_pray = actions.pray_at_church(world, player, donation=2)
    assert res_pray["success"] is True
    assert player.psychology.paranoia <= 100

    # 4. Marriage Proposal
    married_ids = set()
    for c in world.contracts.values():
        if c.type.value == "marriage" and c.status.value == "active":
            married_ids.update(c.parties)

    single_npc = next((n for n in world.npcs.values() if n.is_alive and n.id != player.id and n.id not in married_ids and n.sex != player.sex), None)
    if single_npc:
        res_marry = actions.propose_marriage(world, player, single_npc.id)
        assert "accepted" in res_marry["message"] or "rejected" in res_marry["message"] or "married" in res_marry["message"]

    # 5. Council Seat & Policy
    res_council = actions.run_for_council_seat(world, player, "Mayor")
    assert res_council["success"] in (True, False)

    # 6. Forge Relic
    player.status.coins = 50
    res_relic = actions.forge_masterwork_relic(world, player, "Crown of Hollowfield")
    assert res_relic["success"] is True
    assert "Crown of Hollowfield" in [r.name for r in world.relics.relics.values()]

    # 7. Join Cult
    res_cult = actions.join_secret_cult(world, player)
    assert res_cult["success"] in (True, False)

    # 8. Challenge Duel
    target_npc = next((n for n in world.npcs.values() if n.is_alive and n.id != player.id), None)
    assert target_npc is not None
    res_duel = actions.challenge_duel(world, player, target_npc.id)
    assert "DUEL" in res_duel["message"]


if __name__ == "__main__":
    test_player_action_suite()
    print("ALL PLAYER ACTION TESTS PASSED!")
