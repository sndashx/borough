# Game Design Document: Borough — A Town That Does Not Need You

## 1. Executive Summary & Vision

### 1.1 High Concept
**Borough** is a deterministic, headless medieval life simulation game where a town exists, flourishes, decays, and evolves entirely on its own. The player does not play as an omnipotent ruler or a chosen hero, but as an ordinary inhabitant born into an ongoing, living community. When the player character dies, time marches on; the player may choose to be reborn into a future generation of the same persistent village, walking alongside the ghosts and rumors of their previous lives.

### 1.2 Core Pillars
1. **Autonomous Persistence**: The simulation does not pause for the player. NPCs sleep, farm, craft, trade, marry, bear children, form grudges, fall ill, and die according to systemic rules.
2. **Systemic Narrative & Salience**: Narrative is generated through mechanics—contracts, memory decay, gossip propagation, and a salience filter that decides what the town chooses to remember versus what history forgets.
3. **Intergenerational Consequences**: Debt outlives debtors, apprenticeships teach skills that prevent trade extinction, and family feuds span generations.
4. **Indifferent World**: The world does not orbit the player character. The player receives no special plot armor, auto-fame, or artificial advantages.

---

## 2. World & Time Architecture

### 2.1 Calendar & Time Scale
- **Daily Tick**: 1 in-game day = 1 simulation tick.
- **Annual Cycle**: 360 days per year (4 seasons of 90 days: Winter, Spring, Summer, Autumn).
- **Year Boundary Phase**: Annual macro-simulation step handling aging, memory decay, marriages, births, contract inheritance, market settlement, crisis triggers, and skill extinction checks.

### 2.2 Map & Tileset Engine
- **Grid Map**: Procedural 64x64 tile grid generated deterministically from a 256-character seed.
- **Visual Engine**: Top-down rendering powered by the Urizen Onebit v2.0 tileset (16x16 pixel tiles), rendering maps, NPC portraits, and visual scenes.
- **Terrain Types**: Grass, dirt, cobblestone paths, water, sparse/dense forest, mountain ranges, interior wood/stone floors, and color-coded household exteriors.

---

## 3. Systems Architecture

### 3.1 NPC Simulation (`core/npc.py`)
- **Lifecycle States**:
  - `Infant` (0–3 yrs): Dependent on mother/caretaker; susceptible to infant mortality.
  - `Child` (4–12 yrs): Schooling / play; baseline hunger and low fatigue.
  - `Adolescent` (13–17 yrs): Eligible for apprenticeships; partial work capacity.
  - `Adult` (18–59 yrs): Full labor output, eligible for marriage, contracts, and parenting.
  - `Elder` (60+ yrs): Increased old-age mortality risk; wisdom/mastery.
- **Body Dynamics**:
  - `Health` (0–100): Decreases from starvation, disease, or old age; recovers slowly when fed and rested.
  - `Hunger` (0–100): Decreases daily based on work intensity; restored by consuming food items (grain, bread, meat, herbs).
  - `Fatigue` (0–100): Accumulates from daily labor; restored via periodic rest cycles.
  - `Fertility` (0–100): Age- and sex-dependent baseline governing reproduction probabilities.
- **Mind & Personality (`TraitSet`)**:
  - 10 core traits rated 0–100: *Honesty, Courage, Ambition, Piety, Vengefulness, Patience, Greed, Sociability, Curiosity, Prudence*.
  - Inherited genetically from parents with small stochastic mutations.

### 3.2 Memory & Gossip System (`core/gossip.py`)
- **Memories**:
  - Structure: `(year, event_type, participants, emotional_valence, confidence, witnessed_directly, source_npc_id)`.
  - Confidence decays yearly (-3 if directly witnessed, -6 if learned via gossip).
- **Gossip Propagation**:
  - Occurs probabilistically during daily ticks among socially connected NPCs, transferring facts with decaying confidence.

### 3.3 Economy & Contracts (`core/contract.py`, `core/market.py`)
- **Item Production**:
  - Occupations produce physical goods: Farmers/Herders (Grain), Bakers/Millers/Innkeepers (Bread), Butchers (Meat), Smiths (Tools), Carpenters (Wood), Masons (Stone), Weavers (Cloth), Healers/Midwives (Herbs).
  - Output quality is scaled by NPC skill levels (0–100).
- **Market & Loan Systems**:
  - Supply and demand dynamically scale prices relative to base values.
  - Loan system allows liquidity-constrained NPCs to borrow coppers against reputation stakes.
- **Contract System**:
  - Legal framework governing `MARRIAGE`, `DEBT`, `APPRENTICESHIP`, and `INHERITANCE_CLAIM`.
  - Contracts outlive individual NPCs—debts and obligations pass to designated heirs or enter dispute state upon death.

### 3.4 Lineage, Feuds, & Ghosts (`core/family.py`, `core/ghost.py`)
- **Family Registry**:
  - Tracks genealogical links, parentage, and family lines.
  - Enforces incest prevention rules for marriages based on line-of-descent checks.
  - Tracks generational feuds between family names with escalation/cooling mechanics.
- **Ghost Causal Ledger**:
  - Preserves the memory of dead NPCs who exceeded the town's remembrance threshold.
  - Ghosts influence newborn spawn conditions and village folklore.

### 3.5 World-State Subsystems (`core/*.py`)
- **Reputation (`reputation.py`)**: Global town score and individual NPC opinions with tiers (*Stranger, Noticed, Respected, Beloved, Hostile*).
- **Weather (`weather.py`)**: Seasonal cycles affecting daily work productivity modifiers and crisis probabilities.
- **Livestock (`animal.py`)**: Animal registry (chickens, pigs, cows, horses) producing annual food and reproducing in farm buildings.
- **Factions (`faction.py`)**: Guilds and militias with membership rosters, treasuries, and cross-faction tension state machines.
- **Crises (`crisis.py`)**: Systemic hazards (plagues, famines, fires) triggered by population density, weather, or faction conflict.
- **Religion (`religion.py`)**: Temple leadership, tithes, faith ratings, and calendar rituals (e.g., Solstice celebrations, weddings, penance).
- **Dialogue Engine (`dialogue.py`)**: Context-aware procedural dialogue generated from NPC occupation, reputation, topic, and current disposition.

---

## 4. Player Experience & Game Loop

### 4.1 Playable Life Cycle (`play.py`)
1. **Spawning**: Player is born into an existing household as a newborn baby during a selected town year.
2. **Life Progression**: Fast-forward or step year-by-year. Annual procedural scenes present meaningful choices.
3. **Salience Gating**: Player decisions only enter the town's permanent `Chronicle` if they meet the salience threshold (salience >= 0.3 for crimes, marriages, debts, or public acts).
4. **Death & Legacy**: Upon death, the game evaluates the player's fame score (count of living NPCs with high affinity/trust). If fame >= 5, the player's memory enters village legend; otherwise, they fade into obscurity.
5. **Rebirth**: The player may choose to spawn a new life into the same town, inheriting a world shaped by their previous choices.

### 4.2 Spectator Mode
- Headless execution mode allowing researchers or spectators to run centuries of simulation without player intervention, querying statistical demographics, chronicle trends, and lineage histories.

---

## 5. Technical Design & Performance Invariants

### 5.1 Determinism
- All random event generation is bound to `self.rng` (seeded via SHA-256 hash of the 256-character world seed).
- Zero reliance on global unseeded `random` calls for simulation state.

### 5.2 Performance & Memory Controls
- **Item Cap**: World items capped at ~2,000 units by pruning oldest non-essential items.
- **House Inventory Cap**: Household containers capped at ~60–80 items max.
- **Contract Cap**: Expired/fulfilled contracts pruned past ~1,000 entries.
- **Food Cache**: Household food availability cached and recomputed annually to ensure O(1) daily hunger checks.

### 5.3 Persistence & Serialization
- Human-readable JSON save files (`save_world`, `load_world`).
- Strict backward-compatibility tolerance in `from_dict` methods for missing legacy schema keys.
