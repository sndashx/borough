# Borough — Official Player & Academic Guide (v1.0.0)

**Authored by:** Matthew Alexander Taylor ([@sndashx](https://github.com/sndashx))  
**Academic Simulation Engine:** Deterministic Headless Life-Simulation in Python 3.12+ & Godot 4.3+

---

## 📚 Table of Contents
1. [Introduction](#1-introduction)
2. [Launching the Game](#2-launching-the-game)
3. [Understanding Your Citizens](#3-understanding-your-citizens)
4. [Moment-to-Moment Gameplay & Controls](#4-moment-to-moment-gameplay--controls)
5. [Town Governance & Policy Charters](#5-town-governance--policy-charters)
6. [Masterwork Relics & Family Heirlooms](#6-masterwork-relics--family-heirlooms)
7. [Underground Heresies & Secret Cults](#7-underground-heresies--secret-cults)
8. [Genealogy & Lineage Trees](#8-genealogy--lineage-trees)
9. [Running Decadal & Centennial Research Simulations](#9-running-decadal--centennial-research-simulations)

---

## 1. Introduction

Borough is a deterministic life-simulation game set in an evolving medieval settlement. Every citizen is simulated with complete psychological drives (Maslow's hierarchy of needs), dynamic emotions (grief, jealousy, ambition, paranoia, joy), 18 inherited personality traits, anatomical body parts, wounds, and permanent scars.

As a player, you can observe the town unfold over centuries, or step directly into the boots of an individual citizen to work, trade, brawl, rest, and influence the governance of Borough.

---

## 2. Launching the Game

### Graphical User Interface (Godot 4.3 Engine)
Launch the interactive 16x16 pixel GUI:
```bash
godot --path /home/command/borough
```
- Use `WASD` or Arrow keys to pan the camera.
- Mouse wheel to zoom in and out.
- Left-click any tile, building, or citizen to inspect them in the Inspector panel.
- Right-click any tile or citizen to open the **Soulash 2 Style Action Context Menu**.

### Terminal User Interface (Ncurses)
Launch the terminal GUI:
```bash
PYTHONPATH=. python tui.py
```

### Headless CLI Mode (Academic Simulations)
Run multi-decade simulations from the command line:
```bash
PYTHONPATH=. python play.py --seed 1729 --years 100 --fast
```

---

## 3. Understanding Your Citizens

When you select a citizen on the map or from the Citizen Roster, the **Inspector Panel** displays their complete status:

### Physical Condition & Anatomy
- **Health**: 0 to 100. Decreases from starvation, fatigue, violence, or disease.
- **Hunger**: 0 to 100. Starvation sets in below 20.
- **Fatigue**: 0 to 100. Exhaustion increases hunger loss and reduces work efficiency.
- **Anatomy**: Head, torso, limbs, eyes, heart, lungs.
- **Scars & Impairments**: Permanent battle scars ("Torso scar from Famine Wolf Attack") and impairments ("Limping", "Impaired Sight").

### Psychological Needs & Emotions
- **Maslow Needs**: Safety, Belonging, Esteem, and Self-Actualization (0..100).
- **Emotions**: Joy, Grief, Ambition, Paranoia, Jealousy. High grief or paranoia can trigger secret cult formation or witch trials.

---

## 4. Moment-to-Moment Gameplay & Controls

Above every citizen on the map, a **Thought Bubble** indicates their current activity:
- `Farming` / `Crafting` / `Serving` / `Trading` / `Praying` / `Eating` / `Sleeping` / `Injured` / `Socializing`

Right-click any citizen or tile to open the Context Menu:
- **Talk**: Initiate conversation. Generates dynamic greetings based on town reputation and status.
- **Trade**: Exchange coppers and goods.
- **Work**: Perform daily labor to earn coins and fatigue.
- **Rest**: Sleep to reduce fatigue and restore health.
- **Fight**: Engage in brawls, inflicting wounds and anatomical scars.
- **Steal**: Attempt pickpocketing coppers from wealthy citizens.

---

## 5. Town Governance & Policy Charters

Click the **Council** button on the Top HUD bar to view the Town Council:
- **Council Seats**: Mayor, High Constable, Chief Guildmaster, Grand Prelate.
- **Treasury Gold**: Collected from annual citizen taxes.
- **Town Charters**:
  - **Tax Rate**: 0% to 50%. Higher taxes fill the treasury but increase citizen paranoia and grief.
  - **Grain Subsidies**: Enacted automatically when hunger rises above 30%.
  - **Night Curfew**: Enacted by High Constable when town paranoia spikes.
  - **Elections**: Held annually during winter boundary ticks.

---

## 6. Masterwork Relics & Family Heirlooms

High-skilled artisans (smiths, carpenters, tailors) who experience creative inspiration forge named **Masterwork Relics** (e.g. *Blade of Unbroken Vows*, *Chalice of the First Harvest*).
- Relics hold gold value, engraved historical inscriptions, and owner logs.
- When an artisan dies, their relics pass to their primary heir as family heirlooms.

---

## 7. Underground Heresies & Secret Cults

When citizens experience extreme grief or paranoia, they may form underground secret societies (e.g. *Order of the Eclipse*, *The Whispering Unborn*).
- Cult members gather for secret midnight rituals to restore belonging and reduce grief.
- If secrecy drops below 30%, the High Constable exposes the cult in the town chronicle.

---

## 8. Genealogy & Lineage Trees

Click **Genealogy** in the Inspector to open the Interactive Family Tree Viewer:
- View mother, father, spouses, and children across generations.
- Trace ancient bloodlines back to the founding year of Borough.

---

## 9. Running Decadal & Centennial Research Simulations

To run headless batch research simulations for demographic or sociological analysis:
```bash
# Run 60 years on seed 42 with map rendering
PYTHONPATH=. python play.py --seed 42 --years 60 --render-dir ./maps
```
Map PNGs will be rendered to `./maps` showing urban development over time.
