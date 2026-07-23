"""Historical Mythology, Folklore, and Oral Legend System. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World


@dataclass
class Legend:
    id: str
    original_event: str
    year_occurred: int
    year_mythologized: int
    mythic_description: str
    hero_npc_name: str
    cultural_impact: str

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> Legend:
        return cls(**d)


class LoreRegistry:
    def __init__(self, world: Optional[World] = None):
        self.world = world
        self.legends: dict[str, Legend] = {}
        self._legend_counter = 0

    def process_mythology(self, world: World, rng) -> list[str]:
        logs = []
        # Find chronicle events from 15+ years ago that haven't been mythologized
        old_events = [e for e in world.chronicle if (world.year - e.get("year", world.year)) >= 15]
        if not old_events or rng.random() > 0.3:
            return logs

        sample_event = rng.choice(old_events)
        event_text = sample_event.get("text", "")
        event_year = sample_event.get("year", world.year - 15)

        self._legend_counter += 1
        legend_id = f"legend_{self._legend_counter}"

        # Generate legendary myth
        if "plague" in event_text.lower() or "famine" in event_text.lower():
            myth = f"The Myth of the Great Trial (Year {event_year}): It is said the gods tested Borough with shadow, but the town's spirit proved invincible."
            impact = "Increases Town Courage"
        elif "married" in event_text.lower():
            myth = f"The Legend of the Blessed Union (Year {event_year}): An ancient love that bound bloodlines together and ended old feuds."
            impact = "Increases Harmony"
        elif "witch" in event_text.lower() or "fire" in event_text.lower():
            myth = f"The Tale of the Crimson Night (Year {event_year}): Elders warn children of the spectral flames that cleansed heresy."
            impact = "Increases Superstition"
        else:
            myth = f"The Chronicle Legend of Year {event_year}: A sacred memory passed down by hearth fires across generations."
            impact = "Increases Cultural Heritage"

        legend = Legend(
            id=legend_id,
            original_event=event_text,
            year_occurred=event_year,
            year_mythologized=world.year,
            mythic_description=myth,
            hero_npc_name="The Ancestors",
            cultural_impact=impact,
        )
        self.legends[legend_id] = legend
        logs.append(f"Year {world.year}: Elders established a new town legend: '{myth}'")

        # Teach legend to children
        living_children = [n for n in world.npcs.values() if n.is_alive and n.lifecycle(world.year).value in ("child", "adolescent")]
        for child in living_children:
            child.psychology.self_actualization_need = min(100, child.psychology.self_actualization_need + 10)
            child.mind.devotion = min(100, child.mind.devotion + 5)

        return logs

    def to_dict(self) -> dict:
        return {
            "legend_counter": self._legend_counter,
            "legends": {k: v.to_dict() for k, v in self.legends.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, world: Optional[World] = None) -> LoreRegistry:
        reg = cls(world=world)
        reg._legend_counter = d.get("legend_counter", 0)
        for k, v in d.get("legends", {}).items():
            reg.legends[k] = Legend.from_dict(v)
        return reg
