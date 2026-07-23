"""Contract schema — the key novelty.
Contracts outlive signatories. Children inherit obligations.
This is what makes the simulation bite.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


_contract_counter = [0]
def _next_contract_id() -> str:
    _contract_counter[0] += 1
    return f"c_{_contract_counter[0]}"


class ContractType(str, Enum):
    DEBT = "debt"
    MARRIAGE = "marriage"
    APPRENTICESHIP = "apprenticeship"
    VENDETTA = "vendetta"
    PURCHASE = "purchase"
    GIFT = "gift"
    INHERITANCE_CLAIM = "inheritance_claim"
    LAND_LEASE = "land_lease"


class ContractStatus(str, Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    DISPUTED = "disputed"
    EXPIRED = "expired"


@dataclass
class Contract:
    id: str = field(default_factory=_next_contract_id)
    type: ContractType = ContractType.DEBT
    parties: list[str] = field(default_factory=list)  # npc_ids
    terms: dict = field(default_factory=dict)
    witnesses: list[str] = field(default_factory=list)  # npc_ids
    year_created: int = 0
    status: ContractStatus = ContractStatus.ACTIVE
    reputation_stake: int = 10  # cost if broken
    # CRITICAL: contracts survive signatories
    inherited_by: list[str] = field(default_factory=list)  # npc_ids

    # The town-memory contract: only notable contracts reach the chronicle
    notable: bool = False
    chronicle_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "parties": self.parties,
            "terms": self.terms,
            "witnesses": self.witnesses,
            "year_created": self.year_created,
            "status": self.status.value,
            "reputation_stake": self.reputation_stake,
            "inherited_by": self.inherited_by,
            "notable": self.notable,
            "chronicle_summary": self.chronicle_summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Contract":
        return cls(
            id=d["id"],
            type=ContractType(d["type"]),
            parties=d.get("parties", []),
            terms=d.get("terms", {}),
            witnesses=d.get("witnesses", []),
            year_created=d.get("year_created", 0),
            status=ContractStatus(d.get("status", "active")),
            reputation_stake=d.get("reputation_stake", 10),
            inherited_by=d.get("inherited_by", []),
            notable=d.get("notable", False),
            chronicle_summary=d.get("chronicle_summary", ""),
        )
