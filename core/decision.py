"""Per-NPC decision tree. The 1:1 promise lives here.
Every decision runs against the NPC's actual state, knowledge, memory,
and relationships — never aggregated into a single random roll.
"""
from __future__ import annotations
from typing import Optional

from .npc import NPC, Relationship


def evaluate_npc_decision(
    npc: NPC,
    choice: str,
    context: dict,
) -> dict:
    """Run a single decision for an NPC.

    `choice` is a string key like "steal", "marry", "help", "flee".
    `context` provides environmental state: target, witnesses, hunger, etc.

    Returns a dict with `tendency: float` (0..1) and `reasons: list[str]`.
    The simulation uses tendency to roll vs. context-specific thresholds.
    """
    funcs = {
        "steal": _decide_steal,
        "help": _decide_help,
        "marry": _decide_marry,
        "apprentice_to": _decide_apprentice_to,
        "flee": _decide_flee,
        "call_in_debt": _decide_call_in_debt,
        "break_contract": _decide_break_contract,
    }
    fn = funcs.get(choice, _decide_default)
    return fn(npc, context)


def _weighted(npc: NPC, parts: list[tuple[float, float, str]]) -> dict:
    """Sum weighted contributions into a tendency 0..1.
    Each part is (weight, value_0_to_1, reason).
    """
    total_weight = sum(p[0] for p in parts)
    if total_weight <= 0:
        return {"tendency": 0.5, "reasons": ["no_signal"]}
    tendency = sum(p[0] * p[1] for p in parts) / total_weight
    reasons = [p[2] for p in parts if p[1] > 0.5]
    return {"tendency": max(0.0, min(1.0, tendency)), "reasons": reasons}


def _decide_steal(npc: NPC, ctx: dict) -> dict:
    target_npc_id: Optional[str] = ctx.get("target_npc_id")
    is_hungry: bool = ctx.get("is_hungry", False)
    is_watched: bool = ctx.get("is_watched", False)
    knows_owner: bool = ctx.get("knows_owner", True)

    parts = []
    parts.append((0.3, 1.0 if is_hungry else 0.0, "hungry"))
    parts.append((0.15, 1.0 - npc.mind.honesty / 100, "dishonest"))
    parts.append((0.2, npc.mind.greed / 100, "greedy"))
    parts.append((0.1, 1.0 - npc.mind.courage / 100, "cowardly_or_desperate"))
    parts.append((0.15, 1.0 if is_watched else 0.0, "witnessed_deterrent"))
    parts.append((0.1, 1.0 - npc.mind.prudence / 100, "imprudent"))

    if target_npc_id and target_npc_id in npc.relationships:
        rel = npc.relationships[target_npc_id]
        parts.append((0.1, max(0, -rel.affinity) / 100, "grudge_hurts_more"))
        parts.append((0.05, 1.0 - rel.trust / 100, "low_trust_in_target"))

    return _weighted(npc, parts)


def _decide_help(npc: NPC, ctx: dict) -> dict:
    target_npc_id: Optional[str] = ctx.get("target_npc_id")
    is_dangerous: bool = ctx.get("is_dangerous", False)
    cost: float = ctx.get("cost", 0.0)  # 0..1

    parts = []
    parts.append((0.25, npc.mind.sociability / 100, "social"))
    parts.append((0.2, npc.mind.honesty / 100, "honest"))
    parts.append((0.2, 1.0 - npc.mind.prudence / 100, "rash"))
    parts.append((0.15, 1.0 - cost, "low_cost"))
    parts.append((0.1, 1.0 - npc.mind.courage / 100, "cowardly_flees_not_helps"))

    if target_npc_id and target_npc_id in npc.relationships:
        rel = npc.relationships[target_npc_id]
        parts.append((0.2, (rel.affinity + 100) / 200, "affinity"))
        parts.append((0.1, rel.trust / 100, "trust"))

    if is_dangerous:
        parts.append((0.2, 1.0 - npc.mind.courage / 100, "danger_aversion"))

    return _weighted(npc, parts)


def _decide_marry(npc: NPC, ctx: dict) -> dict:
    target_npc_id: Optional[str] = ctx.get("target_npc_id")
    dowry_offered: int = ctx.get("dowry_offered", 0)
    target_status: str = ctx.get("target_status", "laborer")
    target_wealth: int = ctx.get("target_wealth", 0)

    parts = []
    parts.append((0.2, npc.mind.ambition / 100, "ambitious"))
    parts.append((0.15, npc.mind.greed / 100, "greedy"))
    parts.append((0.1, min(1.0, dowry_offered / 20), "dowry"))
    parts.append((0.1, 1.0 if target_status in ("smith", "miller", "priest", "innkeeper") else 0.3, "status"))
    parts.append((0.1, min(1.0, target_wealth / 50), "wealth"))

    if target_npc_id and target_npc_id in npc.relationships:
        rel = npc.relationships[target_npc_id]
        parts.append((0.25, (rel.affinity + 100) / 200, "affinity"))
        parts.append((0.1, rel.trust / 100, "trust"))

    return _weighted(npc, parts)


def _decide_apprentice_to(npc: NPC, ctx: dict) -> dict:
    master_npc_id: Optional[str] = ctx.get("master_npc_id")
    master_skill: int = ctx.get("master_skill", 50)
    is_kind: bool = ctx.get("master_is_kind", True)

    parts = []
    parts.append((0.3, master_skill / 100, "skill_of_master"))
    parts.append((0.2, npc.mind.curiosity / 100, "curious"))
    parts.append((0.2, npc.mind.ambition / 100, "ambitious"))
    parts.append((0.1, 1.0 if is_kind else 0.0, "kind_master"))
    parts.append((0.2, 1.0 - npc.mind.patience / 100, "impatient"))

    if master_npc_id and master_npc_id in npc.relationships:
        rel = npc.relationships[master_npc_id]
        parts.append((0.1, (rel.affinity + 100) / 200, "affinity_to_master"))

    return _weighted(npc, parts)


def _decide_flee(npc: NPC, ctx: dict) -> dict:
    threat_level: float = ctx.get("threat", 0.5)  # 0..1
    has_dependents: bool = ctx.get("has_dependents", False)

    parts = []
    parts.append((0.4, threat_level, "threat"))
    parts.append((0.3, 1.0 - npc.mind.courage / 100, "cowardly"))
    parts.append((0.2, npc.mind.prudence / 100, "prudent"))
    # Dependents suppress fleeing: have-family = don't flee (low tendency),
    # have-no-family = flee freely (high tendency).
    parts.append((0.3, 0.0 if has_dependents else 1.0, "dependents_tie_down"))

    if has_dependents:
        parts.append((0.2, 0.0, "dependents_hold"))
    else:
        parts.append((0.2, 0.5, "no_dependents"))

    return _weighted(npc, parts)


def _decide_call_in_debt(npc: NPC, ctx: dict) -> dict:
    debtor_npc_id: Optional[str] = ctx.get("debtor_npc_id")
    amount: int = ctx.get("amount", 0)
    need: float = ctx.get("need", 0.0)  # 0..1, how badly npc needs the money

    parts = []
    parts.append((0.3, need, "need"))
    parts.append((0.2, npc.mind.greed / 100, "greedy"))
    parts.append((0.15, npc.mind.prudence / 100, "prudent_collects_now"))
    parts.append((0.15, 1.0 if amount > 20 else 0.3, "large_amount"))

    if debtor_npc_id and debtor_npc_id in npc.relationships:
        rel = npc.relationships[debtor_npc_id]
        parts.append((0.1, (rel.affinity + 100) / 200, "affinity_to_debtor"))
        parts.append((0.1, 1.0 - rel.trust / 100, "low_trust_calls_in"))

    return _weighted(npc, parts)


def _decide_break_contract(npc: NPC, ctx: dict) -> dict:
    cost: float = ctx.get("cost", 0.0)  # 0..1, what they'll lose
    benefit: float = ctx.get("benefit", 0.0)  # 0..1, what they gain

    parts = []
    parts.append((0.3, 1.0 - cost, "low_cost_appealing"))
    parts.append((0.3, benefit, "high_benefit"))
    parts.append((0.2, 1.0 - npc.mind.honesty / 100, "dishonest"))
    parts.append((0.1, 1.0 - npc.mind.prudence / 100, "imprudent"))
    parts.append((0.1, npc.mind.greed / 100, "greedy"))

    return _weighted(npc, parts)


def _decide_default(npc: NPC, ctx: dict) -> dict:
    return {"tendency": 0.5, "reasons": ["default_no_opinion"]}
