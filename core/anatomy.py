"""Anatomical Body Parts, Scars, Impairments, and Medical History. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Wound:
    body_part: str               # "head", "torso", "left_arm", "right_arm", "left_leg", "right_leg", "eyes"
    severity: int                # 1..100
    cause: str                   # "Famine Wolf Attack", "Plague Buboes", "Roof Collapse", "Riot Mace"
    year_acquired: int
    treated: bool = False
    is_healed: bool = False
    scar_description: Optional[str] = None


@dataclass
class Anatomy:
    wounds: list[Wound] = field(default_factory=list)
    scars: list[str] = field(default_factory=list)
    impairments: list[str] = field(default_factory=list)
    medical_treatments: list[dict] = field(default_factory=list)
    cause_of_death_detail: Optional[str] = None

    def add_wound(self, body_part: str, severity: int, cause: str, year: int) -> Wound:
        w = Wound(
            body_part=body_part,
            severity=severity,
            cause=cause,
            year_acquired=year,
        )
        self.wounds.append(w)
        if severity >= 60:
            if body_part in ("left_leg", "right_leg") and "Limping" not in self.impairments:
                self.impairments.append("Limping")
            elif body_part == "eyes" and "Impaired Sight" not in self.impairments:
                self.impairments.append("Impaired Sight")
            elif body_part == "head" and "Traumatic Brain Fog" not in self.impairments:
                self.impairments.append("Traumatic Brain Fog")
        return w

    def tick_healing(self, current_year: int) -> None:
        for w in self.wounds:
            if not w.is_healed and (current_year - w.year_acquired) >= 1:
                w.is_healed = True
                scar = f"{w.body_part.capitalize()} scar from {w.cause} ({w.year_acquired})"
                if scar not in self.scars:
                    self.scars.append(scar)
                w.scar_description = scar

    def to_dict(self) -> dict:
        return {
            "wounds": [w.__dict__ for w in self.wounds],
            "scars": self.scars,
            "impairments": self.impairments,
            "medical_treatments": self.medical_treatments,
            "cause_of_death_detail": self.cause_of_death_detail,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Anatomy:
        a = cls(
            scars=d.get("scars", []),
            impairments=d.get("impairments", []),
            medical_treatments=d.get("medical_treatments", []),
            cause_of_death_detail=d.get("cause_of_death_detail"),
        )
        for wd in d.get("wounds", []):
            a.wounds.append(Wound(**wd))
        return a
