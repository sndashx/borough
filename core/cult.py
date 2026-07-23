"""Secret Societies, Occult Cults, and Underground Heresy. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World
    from .npc import NPC


@dataclass
class Cult:
    id: str
    name: str                           # "Order of the Black Dawn", "The Whispering Unborn", "Cult of the Pale Comet"
    leader_id: str
    doctrine: str                       # "Venerates ancient spirits of the forest", "Promises immunity to plague", "Seeks overthrow of Council"
    secret_symbol: str                  # "Shattered Moon", "Black Feather", "Twin Serpents"
    members: list[str] = field(default_factory=list)
    secrecy_level: int = 90              # 0..100 (if drops below 30, exposed to Constable)
    rituals_performed: int = 0

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> Cult:
        return cls(**d)


class CultRegistry:
    def __init__(self, world: Optional[World] = None):
        self.world = world
        self.cults: dict[str, Cult] = {}
        self._cult_counter = 0

    def tick_cults(self, world: World, rng) -> list[str]:
        logs = []
        living_npcs = [n for n in world.npcs.values() if n.is_alive]
        if not living_npcs:
            return logs

        # 1. Form cult if grief/paranoia is high and few cults exist
        distressed = [n for n in living_npcs if n.psychology.grief > 50 or n.psychology.paranoia > 50]
        if len(distressed) >= 3 and len(self.cults) < 2 and rng.random() < 0.4:
            self._cult_counter += 1
            leader = rng.choice(distressed)
            cult_id = f"cult_{self._cult_counter}"
            
            names = ["Order of the Eclipse", "The Whispering Unborn", "Children of the Pale Star", "Brotherhood of Ashes"]
            doctrines = [
                "Seeks occult protection against starvation and sickness.",
                "Venerates dark spirits beneath the town's roots.",
                "Plots to overthrow the wealthy merchant guilds.",
            ]
            symbols = ["Shattered Crescent", "Coiled Viper", "Black Feather", "Eyeless Skull"]
            
            cult = Cult(
                id=cult_id,
                name=rng.choice(names),
                leader_id=leader.id,
                doctrine=rng.choice(doctrines),
                secret_symbol=rng.choice(symbols),
                members=[leader.id],
            )
            # Recruiter followers
            for candidate in distressed:
                if candidate.id != leader.id and candidate.id not in cult.members and len(cult.members) < 5:
                    cult.members.append(candidate.id)
            
            self.cults[cult_id] = cult
            logs.append(f"Year {world.year}: An underground secret society, '{cult.name}', formed in the shadows of Borough.")

        # 2. Perform secret rituals
        for cult in list(self.cults.values()):
            # Filter dead members
            cult.members = [m_id for m_id in cult.members if world.npcs.get(m_id) and world.npcs[m_id].is_alive]
            if not cult.members:
                del self.cults[cult.id]
                continue

            if rng.random() < 0.5:
                cult.rituals_performed += 1
                # Lower grief / paranoia for members
                for m_id in cult.members:
                    npc = world.npcs[m_id]
                    npc.psychology.grief = max(0, npc.psychology.grief - 15)
                    npc.psychology.paranoia = max(0, npc.psychology.paranoia - 10)
                    npc.psychology.belonging_need = min(100, npc.psychology.belonging_need + 20)

                # Secrecy decay
                cult.secrecy_level = max(0, cult.secrecy_level - rng.randint(2, 8))
                
                # Exposure check
                if cult.secrecy_level < 30:
                    leader_npc = world.npcs.get(cult.leader_id)
                    leader_str = f"{leader_npc.first_name} {leader_npc.family_name}" if leader_npc else "an unknown heretic"
                    logs.append(f"Year {world.year}: Constable uncovered secret cult '{cult.name}' led by {leader_str}! Marked by symbol of {cult.secret_symbol}.")

        return logs

    def to_dict(self) -> dict:
        return {
            "cult_counter": self._cult_counter,
            "cults": {k: v.to_dict() for k, v in self.cults.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, world: Optional[World] = None) -> CultRegistry:
        reg = cls(world=world)
        reg._cult_counter = d.get("cult_counter", 0)
        for k, v in d.get("cults", {}).items():
            reg.cults[k] = Cult.from_dict(v)
        return reg
