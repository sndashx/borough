# Borough — System Architecture & Academic Specification (v1.0.0)

**Author:** Matthew Alexander Taylor ([@sndashx](https://github.com/sndashx))  
**Repository:** `sndashx/borough`  
**License:** MIT

---

## 🏛 System Architecture Overview

Borough is structured as a decoupled, deterministic life-simulation engine with a Python backend core and a Godot 4.3+ frontend visualization layer.

```
+-------------------------------------------------------------------+
|                        Godot 4.3+ Frontend                        |
|                                                                   |
|   +------------------+   +-------------------+   +------------+   |
|   | TileMapLayer (4x)|   |  UI Canvas (HUD)  |   | Camera2D   |   |
|   +--------+---------+   +---------+---------+   +-----+------+   |
|            |                       |                   |          |
|            +-----------------------+-------------------+          |
|                                    |                              |
|                            game_state.gd                          |
+------------------------------------+------------------------------+
                                     |
                         OS.execute JSON IPC
                                     |
+------------------------------------+------------------------------+
|                         sim_bridge.py                             |
+------------------------------------+------------------------------+
                                     |
+------------------------------------+------------------------------+
|                        Python 3.12 Core                           |
|                                                                   |
|   World (State) <----> Simulation (Loop) <----> Chronicle         |
|     |                      |                      |               |
|     +-- Anatomy            +-- Governance         +-- Ghost       |
|     +-- Relics             +-- Cults              +-- Family      |
|     +-- Lore               +-- Crises             +-- Reputation  |
+-------------------------------------------------------------------+
```

---

## 🔬 Core Subsystems

### 1. Deterministic State Machine Engine (`core/simulation.py`)
- **Calendar Wrap**: 360 days per year (`DAYS_PER_YEAR = 360`), divided into 4 seasons of 90 days each.
- **RNG Isolation**: Every simulation instance owns a private `random.Random` initialized by hashing the world seed string with SHA-256.
- **Daily Loop**: Updates weather, processes NPC hunger/fatigue/work/eat/sleep, ticks crises, advances religious calendar, propagates gossip, and decays building conditions.
- **Annual Boundary (`_on_year_boundary`)**: Executes heavy demographic phases: aging, memory decay, marriages, births, deaths, inheritance, contract resolution, governance elections, cult rituals, lore mythologizing, and relic forging.

### 2. Anatomical Injury & Medical History (`core/anatomy.py`)
- **Anatomy Model**: `body_part` (head, torso, limbs, eyes, organs), `severity` (1..100), `scar_description`, `year_acquired`, `cause`.
- **Healing Cycle**: Wounds transition into permanent scars after 1 simulation year.
- **Impairments**: Severely damaged body parts yield permanent status impairments (`Limping`, `Impaired Sight`, `Traumatic Brain Fog`).

### 3. Maslow Need Hierarchy & Dynamic Psychology (`core/npc.py`)
- **Traits (`TraitSet`)**: 18 genetic personality traits (honesty, courage, ambition, piety, vengefulness, patience, greed, sociability, curiosity, prudence, charisma, cunning, stubbornness, frugality, devotion, superstition, creativity, loyalty) mutated across generations.
- **Needs Hierarchy (`Psychology`)**:
  - `safety_need`: Decreases during crises, tax hikes, and brawls.
  - `belonging_need`: Increases from marriage, family time, and secret cult rituals.
  - `esteem_need`: Driven by gold wealth, house size, and council titles.
  - `self_actualization_need`: Boosted when learning legends or forging masterwork relics.

### 4. Masterwork Relics & Artifact System (`core/relic.py`)
- **Creative Inspiration**: High-skill artisans (smith > 75) experience creative bursts to forge named Relics.
- **Data Model**: `id`, `name`, `creator_id`, `item_type`, `material`, `engraving_description`, `renown_value`, `history_log`.
- **Inheritance Pipeline**: On creator death, relics are transferred to primary heirs via testamentary wills.

### 5. Governance Council & Town Charters (`core/governance.py`)
- **Council Seats**: Mayor, High Constable, Chief Guildmaster, Grand Prelate.
- **Policies**: Tax Rate (0..50%), Curfew, Grain Subsidies, Treasury Gold.
- **Elections**: Annual democratic or council voting where citizens cast votes weighted by Maslow safety/esteem needs.

### 6. Underground Heresies & Secret Cults (`core/cult.py`)
- **Formation**: Triggered when aggregate town grief or paranoia exceeds 50%.
- **Rituals**: Conducted annually to decrease grief and paranoia for members.
- **Secrecy Decay**: Secrecy degrades over time until exposed by the High Constable in the town chronicle.

---

## 📡 Godot - Python IPC Protocol (`sim_bridge.py`)

Godot communicates with Python via CLI JSON execution (`OS.execute`):
- `sim_bridge.py --action gen --seed <seed> --pop <pop> --output-file <file>`
- `sim_bridge.py --action tick_days --days <n> --input-file <in> --output-file <out>`
- `sim_bridge.py --action tick_years --years <n> --input-file <in> --output-file <out>`
- `sim_bridge.py --action player_act --player-cmd <cmd> --target-id <id>`

---

## ⚡ Performance & Memory Optimization

- **Item Cap**: World items are capped at 2,000 items; older non-sacred items are automatically garbage-collected.
- **Contract Cap**: Active contracts are pruned to 1,000 items.
- **Memory Decay**: Memory confidence decays 3-6 points per year; memories under 5% confidence are dropped.
- **TileMap Layering**: Godot 4.3+ `TileMapLayer` nodes optimize draw calls into a single batch for 64x64 grids.
