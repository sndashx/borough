"""Livestock + wild animals. Animals live in buildings, breed, age, die, give food."""
from __future__ import annotations
import random as _random
from enum import Enum
from typing import Dict, List, Optional


class Species(str, Enum):
    CHICKEN = "chicken"
    PIG = "pig"
    COW = "cow"
    SHEEP = "sheep"
    GOAT = "goat"
    HORSE = "horse"
    DOG = "dog"
    CAT = "cat"


# Species stats: (max_age_years, food_per_year, breed_chance_per_year, value)
SPECIES_STATS = {
    Species.CHICKEN: (6, 2, 0.7, 5),
    Species.PIG: (10, 4, 0.4, 20),
    Species.COW: (12, 3, 0.3, 50),
    Species.SHEEP: (8, 2, 0.4, 25),
    Species.GOAT: (10, 2, 0.4, 22),
    Species.HORSE: (20, 0, 0.15, 200),  # horses don't produce food
    Species.DOG: (12, 0, 0.2, 10),       # working animal
    Species.CAT: (14, 0, 0.3, 3),        # vermin control
}


class Animal:
    """A single animal entity."""
    def __init__(self, id: str, species: Species, owner_id: Optional[str],
                 building_id: Optional[str], born_year: int):
        self.id = id
        self.species = species
        self.owner_id = owner_id       # NPC who owns/cares for this animal
        self.building_id = building_id  # where it lives
        self.born_year = born_year
        self.age_years: int = 0
        self.health: int = 100         # 0..100
        self.alive: bool = True

    @property
    def max_age(self) -> int:
        return SPECIES_STATS[self.species][0]

    @property
    def can_breed(self) -> bool:
        max_age, _, chance, _ = SPECIES_STATS[self.species]
        return self.alive and 1 <= self.age_years < max_age - 2 and self.health > 50

    def to_dict(self) -> dict:
        return {
            "id": self.id, "species": self.species.value, "owner_id": self.owner_id,
            "building_id": self.building_id, "born_year": self.born_year,
            "age_years": self.age_years, "health": self.health, "alive": self.alive,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Animal":
        a = cls(
            id=d["id"], species=Species(d["species"]), owner_id=d.get("owner_id"),
            building_id=d.get("building_id"), born_year=d.get("born_year", 0),
        )
        a.age_years = d.get("age_years", 0)
        a.health = d.get("health", 100)
        a.alive = d.get("alive", True)
        return a


class AnimalRegistry:
    """All animals in the world."""

    def __init__(self):
        self.animals: Dict[str, Animal] = {}
        self._next_id: int = 0

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"a{self._next_id:04d}"

    def add(self, species: Species, owner_id: Optional[str] = None,
            building_id: Optional[str] = None, born_year: int = 0) -> Animal:
        a = Animal(self._gen_id(), species, owner_id, building_id, born_year)
        self.animals[a.id] = a
        return a

    def living(self) -> List[Animal]:
        return [a for a in self.animals.values() if a.alive]

    def in_building(self, building_id: str) -> List[Animal]:
        return [a for a in self.animals.values() if a.alive and a.building_id == building_id]

    def owned_by(self, npc_id: str) -> List[Animal]:
        return [a for a in self.animals.values() if a.alive and a.owner_id == npc_id]

    def tick_year(self, year: int, rng: Optional[_random.Random] = None) -> dict:
        """Aging, breeding, food production. Returns summary of what happened."""
        rng = rng or _random.Random(year)
        newborn = []
        food_produced = 0
        deaths = []

        for a in list(self.animals.values()):
            if not a.alive:
                continue
            a.age_years += 1
            # Winter health penalty (poor shelter)
            # Random sickness
            if rng.random() < 0.05:
                a.health = max(0, a.health - rng.randint(10, 30))
            # Natural recovery
            if a.health < 100 and rng.random() < 0.3:
                a.health = min(100, a.health + rng.randint(5, 15))
            # Death from old age
            max_age = SPECIES_STATS[a.species][0]
            if a.age_years >= max_age and rng.random() < 0.5:
                a.alive = False
                deaths.append(a)
                continue
            # Death from poor health
            if a.health < 10 and rng.random() < 0.4:
                a.alive = False
                deaths.append(a)
                continue
            # Breeding
            _, _, breed_chance, _ = SPECIES_STATS[a.species]
            if a.can_breed and rng.random() < breed_chance:
                # Need a mate in same building
                mates = [b for b in self.in_building(a.building_id)
                         if b.species == a.species and b.id != a.id and b.can_breed]
                if mates and rng.random() < 0.7:
                    newborn.append(self.add(a.species, owner_id=a.owner_id,
                                            building_id=a.building_id, born_year=year))
            # Food production
            _, food_per_year, _, _ = SPECIES_STATS[a.species]
            if food_per_year > 0 and a.health > 30:
                food_produced += food_per_year

        return {
            "year": year,
            "newborn": [a.id for a in newborn],
            "deaths": [a.id for a in deaths],
            "food_produced": food_produced,
        }

    def to_dict(self) -> dict:
        return {
            "_next_id": self._next_id,
            "animals": {aid: a.to_dict() for aid, a in self.animals.items()},
        }

    def from_dict(self, d: dict) -> None:
        self._next_id = d.get("_next_id", 0)
        self.animals = {aid: Animal.from_dict(ad)
                       for aid, ad in d.get("animals", {}).items()}