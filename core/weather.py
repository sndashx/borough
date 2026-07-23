"""Weather + season system. Affects work output, travel, food, mood.

Day-of-year determines season. Daily roll (deterministic per year+day) picks weather.
Effects:
  - WINTER + no food stockpile = starvation risk
  - STORM = no outdoor work
  - DROUGHT (multi-day CLEAR in summer) = crop failure
  - SNOW = travel penalty, white tint
"""
from __future__ import annotations
import random as _random
from enum import Enum
from typing import Optional, Tuple


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class Weather(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    DROUGHT = "drought"


# Day-of-year thresholds (Northern hemisphere inspired)
SEASON_CUTS = (60, 152, 244, 335)  # spring, summer, autumn, winter starts


def season_for_day(day_of_year: int) -> Season:
    d = day_of_year % 365
    if d < SEASON_CUTS[0] or d >= SEASON_CUTS[3]:
        return Season.WINTER
    if d < SEASON_CUTS[1]:
        return Season.SPRING
    if d < SEASON_CUTS[2]:
        return Season.SUMMER
    return Season.AUTUMN


# Weather probability by season (clear/cloudy/rain/storm/snow/fog/drought)
WEATHER_TABLE = {
    Season.SPRING: [("clear", 40), ("cloudy", 25), ("rain", 25), ("storm", 5), ("fog", 5), ("snow", 0), ("drought", 0)],
    Season.SUMMER: [("clear", 50), ("cloudy", 20), ("rain", 12), ("storm", 8), ("fog", 2), ("snow", 0), ("drought", 8)],
    Season.AUTUMN: [("clear", 30), ("cloudy", 30), ("rain", 25), ("storm", 8), ("fog", 7), ("snow", 0), ("drought", 0)],
    Season.WINTER: [("clear", 25), ("cloudy", 35), ("rain", 5), ("storm", 5), ("fog", 10), ("snow", 20), ("drought", 0)],
}


def _weighted_choice(rng: _random.Random, choices) -> str:
    total = sum(w for _, w in choices)
    pick = rng.random() * total
    cum = 0
    for label, w in choices:
        cum += w
        if pick <= cum:
            return label
    return choices[-1][0]


def roll_weather(year: int, day_of_year: int,
                 rng: Optional[_random.Random] = None) -> Weather:
    """Deterministic per (year, day) by default."""
    rng = rng or _random.Random(year * 1000 + day_of_year)
    season = season_for_day(day_of_year)
    label = _weighted_choice(rng, WEATHER_TABLE[season])
    return Weather(label)


class WeatherState:
    """Per-world weather state. Records recent days for crisis detection."""

    def __init__(self):
        self.current: Weather = Weather.CLEAR
        self.current_season: Season = Season.SPRING
        self.day_of_year: int = 0
        self.year: int = 0
        self.history: list = []  # last 30 (year, day, season, weather)
        self.drought_days: int = 0  # consecutive CLEAR days in summer
        self.rain_days: int = 0     # consecutive RAIN/STORM days

    def advance_day(self, year: int, day_of_year: int) -> Weather:
        self.year = year
        self.day_of_year = day_of_year
        self.current_season = season_for_day(day_of_year)
        self.current = roll_weather(year, day_of_year)
        # Track streaks for crisis detection
        if self.current_season == Season.SUMMER and self.current in (Weather.CLEAR, Weather.CLOUDY):
            self.drought_days += 1
        else:
            self.drought_days = 0
        if self.current in (Weather.RAIN, Weather.STORM):
            self.rain_days += 1
        else:
            self.rain_days = 0
        self.history.append((year, day_of_year, self.current_season.value, self.current.value))
        if len(self.history) > 90:
            self.history = self.history[-90:]
        return self.current

    def work_modifier(self) -> float:
        """Multiplier on outdoor work output. 1.0 = normal."""
        return {
            Weather.CLEAR: 1.1,
            Weather.CLOUDY: 1.0,
            Weather.RAIN: 0.7,
            Weather.STORM: 0.2,
            Weather.SNOW: 0.5,
            Weather.FOG: 0.8,
            Weather.DROUGHT: 0.6,
        }.get(self.current, 1.0)

    def travel_blocked(self) -> bool:
        return self.current in (Weather.STORM, Weather.SNOW)

    def food_decay_modifier(self) -> float:
        """Higher = food spoils faster."""
        if self.current_season == Season.SUMMER:
            return 1.5
        if self.current_season == Season.WINTER and self.current == Weather.SNOW:
            return 0.6  # cold preserves
        return 1.0

    def tint(self) -> Tuple[int, int, int]:
        """RGB tint to overlay on the map for this weather."""
        return {
            Weather.CLEAR: (255, 255, 255),
            Weather.CLOUDY: (180, 180, 180),
            Weather.RAIN: (110, 130, 160),
            Weather.STORM: (60, 60, 80),
            Weather.SNOW: (220, 230, 240),
            Weather.FOG: (200, 200, 200),
            Weather.DROUGHT: (200, 170, 100),
        }.get(self.current, (255, 255, 255))

    def to_dict(self) -> dict:
        return {
            "current": self.current.value,
            "current_season": self.current_season.value,
            "day_of_year": self.day_of_year,
            "year": self.year,
            "history": list(self.history),
            "drought_days": self.drought_days,
            "rain_days": self.rain_days,
        }

    def from_dict(self, d: dict) -> None:
        self.current = Weather(d.get("current", "clear"))
        self.current_season = Season(d.get("current_season", "spring"))
        self.day_of_year = d.get("day_of_year", 0)
        self.year = d.get("year", 0)
        self.history = list(d.get("history", []))
        self.drought_days = d.get("drought_days", 0)
        self.rain_days = d.get("rain_days", 0)