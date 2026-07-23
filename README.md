# Borough (Release 1.0.0)

**Borough** is a deterministic, headless, deep medieval life-simulation game built with Python 3.12+ and Godot 4.3+.

---

## 🌟 Key Features (R1.0 Release)

### 1. Deep PhD Simulation Pillars
- **Anatomical Body Parts & Medical History**: Head, limbs, torso, eyes, organs, dynamic wounds, permanent battle/disease scars, physical impairments (limping, impaired sight), and Cause of Death records.
- **Masterwork Relics & Family Heirlooms**: Artisan creative inspiration, named Relics ("The Bloodforged Ring", "Chalice of First Famine"), engraved descriptions, ownership transfers, and family heirloom inheritance.
- **Town Governance Council & Charters**: Mayor, High Constable, Chief Guildmaster, Grand Prelate, tax collection, grain subsidies, night curfews, and political elections driven by citizen Maslow needs.
- **Secret Societies & Occult Heresies**: Underground cults ("Order of the Eclipse", "The Whispering Unborn"), midnight rituals, secret symbols, and Constable exposures.
- **Historical Mythology & Oral Lore**: Multi-decade chronicle events aging into mythic town folklore recited by hearth fires.

### 2. Soulash 2 Style Interactions & GUI
- **Multi-Layer TileMapLayer 16x16 Grid**: Ground, Buildings, Actors, Selection reticles.
- **NPC Thought Bubbles & Context Menu**: Moment-to-moment NPC activity badges ("Farming", "Crafting", "Praying", "Eating", "Sleeping") and right-click context menu (Talk, Trade, Work, Rest, Inspect, Fight, Steal).
- **Interactive UI Inspectors**: Family Tree / Genealogy Viewer, Council & Town Charters, Relics & Artifacts, Secret Cults, Inventory, Story Cards, and Achievements.
- **AAA Polish**: AAA Main Menu & Settings, Audio Sliders, Screen Shake, Weather Particle Effects, Day/Night Ambient Lighting.

---

## 🎮 How to Play

### Option 1: Interactive Godot GUI
```bash
godot --path /home/command/borough
```

### Option 2: Ncurses TUI
```bash
PYTHONPATH=. python tui.py
```

### Option 3: Headless CLI
```bash
PYTHONPATH=. python play.py --seed 1729 --years 60
```

---

## 🧪 Testing

Run the full automated test suite:
```bash
PYTHONPATH=. pytest tests/ -v
```
