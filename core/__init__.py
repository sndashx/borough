"""Borough — engine-agnostic simulation core.

Sprint 0: skeletons only.
World generates with 30 NPCs, 25 buildings, seed-based. Daily tick runs
without crashing for 100 in-game years.
"""
from .world import World, generate_world
from .npc import NPC, Sex, LifecycleState
from .contract import Contract, ContractType, ContractStatus
from .building import Building, BuildingType
from .item import Item, ItemType
from .simulation import Simulation
from .decision import evaluate_npc_decision
from .gossip import propagate_gossip
from .chronicle import Chronicle

__all__ = [
    "World", "generate_world",
    "NPC", "Sex", "LifecycleState",
    "Contract", "ContractType", "ContractStatus",
    "Building", "BuildingType",
    "Item", "ItemType",
    "Simulation",
    "evaluate_npc_decision",
    "propagate_gossip",
    "Chronicle",
]
