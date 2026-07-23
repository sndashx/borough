"""Dialogue system. Talk to an NPC — they greet, answer questions, gossip.

Stateless text generation: same input -> same output (deterministic per seed).
Conversations log a record that can feed the chronicle.
"""
from __future__ import annotations
import random as _random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Topic(str, Enum):
    GREETING = "greeting"
    FAMILY = "family"
    WORK = "work"
    TOWN = "town"
    WEATHER = "weather"
    CRisis = "crisis"
    GOSSIP = "gossip"
    PLAYER = "player"
    FAITH = "faith"
    TRADE = "trade"


# Greeting templates (lowercase; capitalized by caller)
GREETINGS_BY_DISPOSITION = {
    "friendly":  ["ah, {name}!", "good {time_of_day}, {name}.", "well met.", "back again, eh?"],
    "neutral":   ["hmm?", "aye?", "what is it.", "{name}.", "you."],
    "hostile":   ["what do you want.", "off with you.", "i've nothing to say to you.", "..."],
    "devoted":   ["{name}! thank the gods.", "i was hoping you'd come by.", "blessings, {name}."],
}


FAMILY_LINES = {
    "has_family": [
        "my {relation} is well, thanks be.",
        "{relation}? aye, working hard as always.",
        "the {relation} keeps the home, i keep the field.",
    ],
    "no_family": [
        "i've no one left.",
        "family? ...no.",
        "the dead don't answer.",
    ],
    "mourning": [
        "i buried {relation} last season.",
        "we lost {relation} to {cause}.",
        "still fresh. don't speak of it.",
    ],
}


WORK_LINES = [
    "there's always more work to do.",
    "the {job} work doesn't wait for weather.",
    "aye, work is work.",
    "could use an extra hand at work, if you ask.",
]


WEATHER_LINES = {
    "clear":  "fair skies today.",
    "rain":   "wet again. the roads will be mud.",
    "storm":  "best stay indoors.",
    "snow":   "cold enough to freeze the words in your mouth.",
    "fog":    "can barely see the church spire.",
    "drought":"the wells are running low.",
    "cloudy": "grey, but no rain yet.",
}


@dataclass
class DialogueLine:
    speaker_id: str
    text: str
    topic: Topic
    year: int


@dataclass
class Conversation:
    """A record of a player-NPC dialogue."""
    year: int
    npc_id: str
    lines: List[DialogueLine] = field(default_factory=list)
    reputation_delta: int = 0

    def to_dict(self) -> dict:
        return {
            "year": self.year, "npc_id": self.npc_id,
            "lines": [{"speaker_id": l.speaker_id, "text": l.text,
                       "topic": l.topic.value, "year": l.year} for l in self.lines],
            "reputation_delta": self.reputation_delta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        c = cls(year=d["year"], npc_id=d["npc_id"],
                reputation_delta=d.get("reputation_delta", 0))
        for ld in d.get("lines", []):
            c.lines.append(DialogueLine(
                speaker_id=ld["speaker_id"], text=ld["text"],
                topic=Topic(ld["topic"]), year=ld["year"],
            ))
        return c


def _disposition(rep_score: int) -> str:
    if rep_score >= 60:
        return "devoted"
    if rep_score >= 10:
        return "friendly"
    if rep_score >= -10:
        return "neutral"
    return "hostile"


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def generate_greeting(npc, rep_score: int, hour: int = 12,
                      rng: Optional[_random.Random] = None) -> str:
    rng = rng or _random.Random(hash(npc.id) & 0xFFFFFFFF)
    disposition = _disposition(rep_score)
    template = rng.choice(GREETINGS_BY_DISPOSITION[disposition])
    return template.format(name=npc.first_name, time_of_day=_time_of_day(hour))


def generate_family_line(npc, rng: Optional[_random.Random] = None,
                         world=None) -> str:
    rng = rng or _random.Random(hash(npc.id) ^ 0xDEAD)
    # Crude check for family via parent / marriage contract (Status has no
    # spouse_id / children_ids fields, so derive from contracts + ancestry).
    has_family = False
    if world is not None:
        for c in world.contracts.values():
            if c.type.value == "marriage" and c.status.value == "active" and npc.id in c.parties:
                has_family = True
                break
        if not has_family:
            for other in world.npcs.values():
                if other is npc:
                    continue
                if other.mother_id == npc.id or other.father_id == npc.id:
                    has_family = True
                    break
    bucket = "has_family" if has_family else "no_family"
    template = rng.choice(FAMILY_LINES[bucket])
    relation = rng.choice(["spouse", "mother", "father", "son", "daughter", "kin"])
    return template.format(relation=relation)


def generate_work_line(npc, rng: Optional[_random.Random] = None) -> str:
    rng = rng or _random.Random(hash(npc.id) ^ 0xBEEF)
    template = rng.choice(WORK_LINES)
    job = (npc.knowledge.skills and
           max(npc.knowledge.skills, key=npc.knowledge.skills.get) if npc.knowledge.skills
           else "labor")
    return template.format(job=job)


def generate_weather_line(weather, rng: Optional[_random.Random] = None) -> str:
    return WEATHER_LINES.get(weather.current.value, "weather is weather.")


def talk(npc, topic: Topic, year: int, *, rep_score: int = 0,
         hour: int = 12, weather=None,
         rng: Optional[_random.Random] = None) -> DialogueLine:
    """Single-line response from NPC to player's topic."""
    rng = rng or _random.Random(hash((npc.id, topic.value, year)) & 0xFFFFFFFF)
    if topic == Topic.GREETING:
        text = generate_greeting(npc, rep_score, hour, rng)
    elif topic == Topic.FAMILY:
        text = generate_family_line(npc, rng, world)
    elif topic == Topic.WORK:
        text = generate_work_line(npc, rng)
    elif topic == Topic.WEATHER and weather is not None:
        text = generate_weather_line(weather, rng)
    elif topic == Topic.TOWN:
        text = rng.choice([
            "the town holds.",
            "i hear trouble from the south.",
            "we've had worse.",
            "could be better, could be worse.",
        ])
    elif topic == Topic.GOSSIP:
        text = rng.choice([
            "they say the miller's daughter is sweet on a soldier.",
            "old wickham is sleeping with the pigs again.",
            "the priest keeps to himself these days.",
            "saw lights in the wood last week.",
        ])
    elif topic == Topic.PLAYER:
        if rep_score >= 30:
            text = rng.choice(["good folk.", "you've done well by us.", "the town remembers."])
        elif rep_score <= -30:
            text = rng.choice(["watch yourself.", "folk talk.", "we remember too."])
        else:
            text = rng.choice(["i don't know you.", "you'll do.", "passing through?"])
    elif topic == Topic.FAITH:
        text = rng.choice([
            "the gods keep their own counsel.",
            "i go to temple on the solstice, like anyone.",
            "faith is a private thing.",
        ])
    elif topic == Topic.TRADE:
        text = rng.choice([
            "ask the merchant.",
            "i've got grain to sell, if you've coin.",
            "no credit.",
        ])
    else:
        text = "..."
    return DialogueLine(speaker_id=npc.id, text=text, topic=topic, year=year)


class DialogueLog:
    """World-owned log of all conversations."""
    def __init__(self):
        self.conversations: List[Conversation] = []

    def add(self, conv: Conversation) -> None:
        self.conversations.append(conv)
        if len(self.conversations) > 200:
            self.conversations = self.conversations[-200:]

    def with_npc(self, npc_id: str) -> List[Conversation]:
        return [c for c in self.conversations if c.npc_id == npc_id]

    def to_dict(self) -> dict:
        return {"conversations": [c.to_dict() for c in self.conversations]}

    def from_dict(self, d: dict) -> None:
        self.conversations = [Conversation.from_dict(cd)
                            for cd in d.get("conversations", [])]