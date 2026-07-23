"""Daily tick simulation. The heart of the system.
One tick = one in-game day. Every NPC runs daily updates.
"""
from __future__ import annotations
import random
from typing import Optional

from .world import World, seed_to_int, FIRST_NAMES_M, FIRST_NAMES_F
from .npc import NPC, LifecycleState, Sex
from .building import Building, BuildingType
from .contract import Contract, ContractType, ContractStatus
from .item import Item, ItemType
from .gossip import propagate_gossip, form_memory_of
from .chronicle import Chronicle


# 1 in-game year = 360 days for cleaner arithmetic.
DAYS_PER_YEAR = 360
DAYS_PER_SEASON = 90


class Simulation:
    def __init__(self, world: World, seed=None):
        """`seed` may be str | int | None. None falls back to world.seed."""
        self.world = world
        self.chronicle = Chronicle(world)
        chosen = world.seed if seed is None else seed
        self.rng = random.Random(seed_to_int(chosen))
        self.day_in_year = 0  # 0..359

    # --- Top-level drivers ---

    def run_days(self, n: int) -> None:
        for _ in range(n):
            self.tick_day()

    def run_years(self, n: int) -> None:
        self.run_days(n * DAYS_PER_YEAR)

    # --- Daily tick ---

    def tick_day(self) -> None:
        w = self.world
        w.day += 1
        self.day_in_year = (self.day_in_year + 1) % DAYS_PER_YEAR
        if self.day_in_year == 0:
            self.world.year += 1
            self._on_year_boundary()

        # Sprint 8: weather advances, crisis ticks, religion calendar
        if w.weather_state:
            w.weather_state.advance_day(w.year, self.day_in_year)
        if w.crises:
            deaths = w.crises.tick_day(w.year, self.day_in_year, w.living_npcs(), self.rng)
            for d in deaths:
                victim = w.npcs.get(d["npc_id"])
                if victim and victim.is_alive:
                    self._kill(victim, d["cause"])
        if w.religion:
            w.religion.tick_calendar(w.year, self.day_in_year, w.living_npcs(), self.rng)

        # Process every living NPC
        for npc in list(w.living_npcs()):
            self._process_npc_day(npc)

        # Propagate gossip (rare — 10% of days)
        if self.rng.random() < 0.1:
            propagate_gossip(w.living_npcs(), w.year, self.rng)

        # Buildings decay slowly
        if self.day_in_year == 0:
            for b in w.buildings.values():
                if b.type != BuildingType.CHURCH:  # church is maintained
                    b.condition = max(0, b.condition - self.rng.randint(0, 2))

    def _on_year_boundary(self) -> None:
        """Once per year, do the heavy lifting: aging, marriage, deaths, births."""
        w = self.world
        # Memory decay
        for npc in w.living_npcs():
            for m in npc.memory:
                m.decay(years=1)
            # Trim very low-confidence memories annually
            npc.memory = [m for m in npc.memory if m.confidence > 5]

        # Recompute food_count_cache for all buildings
        for b in w.buildings.values():
            count = 0
            for iid in b.item_ids:
                it = w.items.get(iid)
                if it and it.type in (ItemType.GRAIN, ItemType.FLOUR, ItemType.BREAD, ItemType.MEAT, ItemType.HERB, ItemType.CHEESE, ItemType.BEER, ItemType.WINE, ItemType.CIDER):
                    count += 1
            b.food_count_cache = count

        # Item cap — prevent runaway memory growth. Drop excess items in houses.
        if len(w.items) > 2000:
            # Remove the oldest items in non-granary, non-church buildings
            surplus = len(w.items) - 1500
            old_items = sorted(
                ((iid, it) for iid, it in w.items.items()
                 if it.building_id
                 and (b := w.buildings.get(it.building_id))
                 and b.type not in (BuildingType.GRANARY, BuildingType.CHURCH)),
                key=lambda p: p[1].history[0]["year"] if p[1].history else 0
            )
            for iid, it in old_items[:surplus]:
                w.items.pop(iid, None)
                if it.building_id and (b := w.buildings.get(it.building_id)):
                    if iid in b.item_ids:
                        b.item_ids.remove(iid)

        # Contract cap — drop old fulfilled/broken contracts
        if len(w.contracts) > 1000:
            expired = [c for c in w.contracts.values()
                       if c.status in (ContractStatus.FULFILLED, ContractStatus.EXPIRED, ContractStatus.BROKEN)]
            expired.sort(key=lambda c: c.year_created)
            for c in expired[:len(w.contracts) - 800]:
                w.contracts.pop(c.id, None)

        # Process deaths from old age, disease, accident
        self._process_deaths()
        # Process births
        self._process_births()
        # Try marriages
        self._try_marriages()
        # Try apprenticeship assignments
        self._try_apprenticeships()
        # Maybe call in a debt
        if self.rng.random() < 0.2:
            self._maybe_call_in_debt()
        # Annual coin stipend: working adults earn 2-5 coppers/year
        for npc in w.living_npcs():
            age = w.year - npc.birth_year
            if 14 <= age <= 65 and npc.status.occupation not in ("child", "apprentice"):
                npc.status.coins += self.rng.randint(2, 5)
        # Skill teaching
        self._process_skill_teaching()
        self._check_skill_extinction()
        # Market + loans
        from .market import Market, LoanSystem
        market = Market(self.world, self.rng)
        market.run()
        loans = LoanSystem(self.world, self.rng)
        loans.run()

        # Sprint 8: animals tick, factions cool, reputation decays, crises may trigger
        w = self.world
        if w.animals:
            w.animals.tick_year(w.year, self.rng)
        if w.factions:
            w.factions.tick_year(w.year)
        if w.reputation:
            w.reputation.decay_all(1)
        if w.crises:
            w.crises.try_trigger(w.year, 0, w.weather_state, w.living_npcs(),
                                list(w.factions.factions.values()) if w.factions else [],
                                self.rng)

        # Deep PhD Subsystem Ticks
        for npc in w.living_npcs():
            npc.anatomy.tick_healing(w.year)

        if w.governance:
            gov_logs = w.governance.hold_elections_and_council(w, self.rng)
            for log in gov_logs:
                w.chronicle.append({"year": w.year, "text": log, "type": "governance"})
        if w.cults:
            cult_logs = w.cults.tick_cults(w, self.rng)
            for log in cult_logs:
                w.chronicle.append({"year": w.year, "text": log, "type": "cult"})
        if w.lore:
            lore_logs = w.lore.process_mythology(w, self.rng)
            for log in lore_logs:
                w.chronicle.append({"year": w.year, "text": log, "type": "lore"})
        if w.relics:
            # High-skill artisans create relics
            artisans = [n for n in w.living_npcs() if max(n.knowledge.skills.values(), default=0) > 75]
            if artisans and self.rng.random() < 0.2:
                artisan = self.rng.choice(artisans)
                item_type = self.rng.choice(["sword", "goblet", "crown", "tapestry", "anvil"])
                mat = self.rng.choice(["Steel", "Silver", "Oak", "Gold", "Obsidian"])
                relic = w.relics.create_relic(artisan, item_type, mat, w.year, self.rng)
                w.chronicle.append({
                    "year": w.year,
                    "text": f"{artisan.first_name} {artisan.family_name} forged a Masterwork Relic: '{relic.name}'!",
                    "type": "relic"
                })

    def _process_npc_day(self, npc: NPC) -> None:
        """Per-day life: hunger accumulates, fatigue accumulates, work produces,
        eat if food available, sleep at night.
        """
        lifecycle = npc.lifecycle(self.world.year)
        if lifecycle == LifecycleState.INFANT:
            self._infant_day(npc)
            return
        # Hunger rises each day (faster if working, slower if child)
        work_intensity = 0
        if lifecycle in (LifecycleState.ADULT, LifecycleState.ELDER) and npc.status.occupation not in ("child", "apprentice"):
            work_intensity = 1
        elif lifecycle == LifecycleState.ADOLESCENT:
            work_intensity = 0.5
        # Daily hunger drop: ~3 baseline, +3 if working. One food = ~13 days of work.
        npc.body.hunger = max(0, npc.body.hunger - int(3 + 3 * work_intensity))
        # Fatigue rises with work
        npc.body.fatigue = min(100, npc.body.fatigue + int(3 + 4 * work_intensity))
        # Eat if hungry enough
        if npc.body.hunger < 50:
            ate = self._npc_eat(npc)
            if not ate and npc.body.hunger < 20:
                # Starving
                npc.body.health = max(0, npc.body.health - 1)
            elif ate and npc.body.health < 100 and self.world.day % 7 == 0:
                # Fed and resting — slow recovery
                npc.body.health = min(100, npc.body.health + 1)
        # Sleep at night — fatigue recovery
        if self.day_in_year % 3 == 0:  # roughly every 3rd day, full rest
            npc.body.fatigue = max(0, npc.body.fatigue - 40)
        # Work produces — daily
        if work_intensity > 0:
            self._npc_work(npc)
        # Slow daily decline for the sick. Only at critically low health.
        if npc.body.health < 20 and self.rng.random() < 0.02:
            npc.body.health = max(0, npc.body.health - 1)
        elif npc.body.health < 50 and self.rng.random() < 0.005:
            npc.body.health = max(0, npc.body.health - 1)

    def _infant_day(self, npc: NPC) -> None:
        # Infants need a mother present or they may die. Annual check, not daily.
        mother = self.world.npcs.get(npc.mother_id) if npc.mother_id else None
        if not mother or not mother.is_alive:
            # Orphan infant — annual mortality check (~50% over 5 years)
            if self.world.day % DAYS_PER_YEAR == 0 and self.rng.random() < 0.10:
                self._kill(npc, "infant_mortality")
            return
        # Cared for — hunger OK
        npc.body.hunger = max(60, npc.body.hunger)

    def _npc_eat(self, npc: NPC) -> bool:
        """Find food in inventory or household. Return True if ate."""
        FOOD_TYPES = (ItemType.GRAIN, ItemType.FLOUR, ItemType.BREAD, ItemType.MEAT, ItemType.HERB, ItemType.CHEESE, ItemType.BEER, ItemType.WINE, ItemType.CIDER)
        # First try inventory
        for iid in list(npc.status.inventory_item_ids):
            item = self.world.items.get(iid)
            if not item:
                npc.status.inventory_item_ids.remove(iid)
                continue
            if item.type in FOOD_TYPES:
                npc.body.hunger = min(100, npc.body.hunger + 40)
                npc.status.last_meal_day = self.world.day
                self.world.items.pop(iid, None)
                npc.status.inventory_item_ids.remove(iid)
                item.history.append({"year": self.world.year, "event": "consumed", "by": npc.id})
                return True
        # Try household — use cached food_count to short-circuit when empty
        if npc.status.household_id:
            house = self.world.buildings.get(npc.status.household_id)
            if house and house.food_count_cache > 0:
                # Walk the entire item list — a household may have many
                # non-food items ahead of food, and the previous `[:20]` cap
                # silently starved NPCs whose food had drifted past the head.
                for iid in list(house.item_ids):
                    item = self.world.items.get(iid)
                    if not item:
                        house.item_ids.remove(iid)
                        continue
                    if item.type in FOOD_TYPES:
                        npc.body.hunger = min(100, npc.body.hunger + 40)
                        npc.status.last_meal_day = self.world.day
                        self.world.items.pop(iid, None)
                        house.item_ids.remove(iid)
                        house.food_count_cache = max(0, house.food_count_cache - 1)
                        item.history.append({"year": self.world.year, "event": "consumed_by_household", "by": npc.id})
                        return True
        return False

    # Map occupation -> ItemType. Cached for perf.
    OCCUPATION_OUTPUT = {
        "farmer": ItemType.GRAIN, "herder": ItemType.GRAIN,
        "baker": ItemType.BREAD, "butcher": ItemType.MEAT,
        "miller": ItemType.BREAD, "smith": ItemType.TOOL,
        "carpenter": ItemType.WOOD, "mason": ItemType.STONE,
        "weaver": ItemType.CLOTH, "innkeeper": ItemType.BREAD,
        "healer": ItemType.HERB, "midwife": ItemType.HERB,
        "apothecary": ItemType.POTION, "scribe": ItemType.SCROLL,
        "tailor": ItemType.CLOTH, "fletcher": ItemType.ARROW,
        "jeweler": ItemType.JEWELRY, "guardsman": ItemType.WEAPON,
        "alchemist": ItemType.POTION, "cooper": ItemType.BARREL,
        "wheelwright": ItemType.TOOL, "trapper": ItemType.PELT,
        "vintner": ItemType.WINE, "scholar": ItemType.BOOK,
        "priest": None, "minstrel": None, "bailiff": None,
    }

    def _npc_work(self, npc: NPC) -> None:
        """An adult produces a small amount of output each day based on occupation."""
        occ = npc.status.occupation
        production = self.OCCUPATION_OUTPUT.get(occ, ItemType.GRAIN)
        if production is None:
            return
        # Special: miller does its own production
        if occ == "miller":
            self._mill_produce(npc)
        # Special: laborers and similar produce a varied output
        if occ in ("charcoal_burner", "potter", "tanner", "laborer"):
            production = self.rng.choice([ItemType.WOOD, ItemType.STONE, ItemType.GRAIN, ItemType.CLOTH])
        # Quality based on skill
        skill = npc.knowledge.skills.get(occ, 20)
        quality = 30 + (skill * 60 // 100) + self.rng.randint(-5, 5)
        if quality < 1: quality = 1
        if quality > 100: quality = 100
        item = Item(
            type=production, weight=1.0, quality=quality,
            owner_npc_id=npc.id, building_id=npc.status.household_id,
        )
        self.world.add_item(item)
        if npc.status.household_id:
            house = self.world.buildings.get(npc.status.household_id)
            if house:
                house.item_ids.append(item.id)
                # Cap house item count to prevent runaway
                if len(house.item_ids) > 80:
                    excess = len(house.item_ids) - 80
                    for _ in range(excess):
                        old_id = house.item_ids.pop(0)
                        self.world.items.pop(old_id, None)
        else:
            npc.status.inventory_item_ids.append(item.id)
        # Subsistence food: every working adult produces 1 grain every 3 days,
        # ONLY if the household food stockpile is below 20 units. This caps
        # item accumulation and prevents runaway list growth.
        # We use a cached food count on the building, recomputed yearly.
        if self.world.day % 3 == 0 and npc.status.household_id:
            house = self.world.buildings.get(npc.status.household_id)
            if house and house.food_count_cache < 20:
                sub = Item(
                    type=ItemType.GRAIN, weight=1.0, quality=self.rng.randint(20, 50),
                    owner_npc_id=npc.id, building_id=house.id,
                )
                self.world.add_item(sub)
                house.item_ids.append(sub.id)
                # Recompute cache from actual contents — `+=1` against a stale
                # cache would drift if items have been consumed since the last
                # yearly recompute.
                house.food_count_cache = sum(
                    1 for iid in house.item_ids
                    if (it := self.world.items.get(iid))
                    and it.type in (ItemType.GRAIN, ItemType.FLOUR, ItemType.BREAD, ItemType.MEAT, ItemType.HERB, ItemType.CHEESE, ItemType.BEER, ItemType.WINE, ItemType.CIDER)
                )
        # Cap each house's total items to prevent runaway accumulation
        if npc.status.household_id:
            house = self.world.buildings.get(npc.status.household_id)
            if house and len(house.item_ids) > 60:
                # Drop oldest non-food items
                non_food = []
                for iid in house.item_ids:
                    it = self.world.items.get(iid)
                    if it and it.type not in (ItemType.GRAIN, ItemType.FLOUR, ItemType.BREAD, ItemType.MEAT, ItemType.HERB, ItemType.CHEESE, ItemType.BEER, ItemType.WINE, ItemType.CIDER):
                        non_food.append(iid)
                for iid in non_food[:len(house.item_ids) - 60]:
                    house.item_ids.remove(iid)
                    self.world.items.pop(iid, None)

    def _mill_produce(self, npc: NPC) -> None:
        """Miller needs grain. If household has grain, convert some to bread-equivalent
        (or simply mark the mill as producing). For now, millers convert grain to bread.
        """
        if not npc.status.household_id:
            return
        house = self.world.buildings.get(npc.status.household_id)
        if not house:
            return
        # Find a grain item
        for iid in list(house.item_ids):
            item = self.world.items.get(iid)
            if not item or item.type != ItemType.GRAIN:
                continue
            if self.rng.random() < 0.3:
                # Convert this grain to bread
                item.type = ItemType.BREAD
                item.history.append({"year": self.world.year, "event": "milled_to_bread", "by": npc.id})
                return
            else:
                return

    def _process_deaths(self) -> None:
        w = self.world
        for npc in list(w.living_npcs()):
            age = w.year - npc.birth_year
            # Old age death
            if age > 55:
                p_death = min(0.3, (age - 55) * 0.015 + (100 - npc.body.health) * 0.003)
                if self.rng.random() < p_death:
                    self._kill(npc, "old_age")
                    continue
            # Disease — annual roll, very low base rate, scales mildly with density
            pop = w.living_count()
            density_factor = max(1.0, pop / 30.0)
            p_disease = 0.005 * density_factor  # 0.5% annual baseline
            if self.rng.random() < p_disease:
                # Mild illness, not auto-fatal — bottoms at 70
                npc.body.health = max(70, npc.body.health - self.rng.randint(1, 5))
            # Starvation / untreated condition — only if not already killed above
            if npc.body.health <= 0 and npc.is_alive:
                self._kill(npc, "disease")

    def _process_births(self) -> None:
        w = self.world
        # Build marriage lookup: npc_id -> spouse_id
        spouse_of = {}
        for c in w.contracts.values():
            if c.type == ContractType.MARRIAGE and c.status == ContractStatus.ACTIVE:
                if len(c.parties) >= 2:
                    spouse_of[c.parties[0]] = c.parties[1]
                    spouse_of[c.parties[1]] = c.parties[0]
        # Pair up married couples with fertility
        for npc in w.living_npcs():
            if npc.sex.value != "F":
                continue
            if npc.body.fertility <= 0:
                continue
            age = w.year - npc.birth_year
            if age < 14 or age > 48:
                continue
            # Track last birth year for postpartum gap (1-year gap, not 2)
            if w.year - npc.status.last_birth_year < 1:
                continue
            # Find spouse
            spouse = None
            if npc.id in spouse_of:
                sid = spouse_of[npc.id]
                spouse = w.npcs.get(sid)
            if not spouse or not spouse.is_alive:
                continue
            # Population pressure: if above target, lower birth rate (mild)
            pop = w.living_count()
            pressure = max(0.0, (pop - w.target_population) / 50.0)
            base_p = 0.55 * (npc.body.fertility / 100)  # ~50% per fertile woman per year
            p = base_p * (1 - pressure * 0.3)  # gentler pressure
            if self.rng.random() < p:
                self._birth(npc, spouse)
                npc.status.last_birth_year = w.year

    def _try_marriages(self) -> None:
        w = self.world
        # Build set of currently-married NPC ids
        married_ids = set()
        for c in w.contracts.values():
            if c.type == ContractType.MARRIAGE and c.status == ContractStatus.ACTIVE:
                married_ids.update(c.parties)
        eligible = [n for n in w.living_npcs()
                    if w.year - n.birth_year >= 14
                    and w.year - n.birth_year <= 40
                    and n.id not in married_ids]
        if len(eligible) < 2:
            return
        # Shuffle and try pairing. Try to pair as many as we can per year.
        self.rng.shuffle(eligible)
        attempts = min(len(eligible) // 2, 8)  # up to 8 marriages per year
        for i in range(0, attempts * 2, 2):
            a, b = eligible[i], eligible[i + 1]
            if a.sex == b.sex:
                continue
            if (b.id in a.relationships and a.relationships[b.id].affinity > 20) or self.rng.random() < 0.2:
                self._marry(a, b)

    def _try_apprenticeships(self) -> None:
        w = self.world
        # Find adolescents without occupation
        candidates = [n for n in w.living_npcs()
                      if n.lifecycle(w.year).value == "adolescent"
                      and n.status.occupation not in ("apprentice",)]
        for n in candidates:
            # Find a master in town with relevant skill
            masters = [m for m in w.living_npcs()
                       if m.status.occupation not in ("child", "apprentice")
                       and m.id != n.id
                       and m.lifecycle(w.year).value in ("adult", "elder")]
            if not masters:
                continue
            master = self.rng.choice(masters)
            self._apprentice(n, master)

    def _process_skill_teaching(self) -> None:
        """Active apprenticeships teach skills yearly. If the master dies, the
        apprentice must find a new one or the skill is lost from the town."""
        w = self.world
        for c in list(w.contracts.values()):
            if c.type != ContractType.APPRENTICESHIP or c.status != ContractStatus.ACTIVE:
                continue
            if len(c.parties) < 2:
                continue
            apprentice_id, master_id = c.parties[0], c.parties[1]
            apprentice = w.npcs.get(apprentice_id)
            master = w.npcs.get(master_id)
            if not apprentice or not apprentice.is_alive:
                # Apprentice died — close the contract
                c.status = ContractStatus.EXPIRED
                continue
            if not master or not master.is_alive:
                # Master died — apprentice loses mentor, must find a new one
                # The skill level they had is preserved but no more teaching
                c.terms["master_died_year"] = w.year
                c.status = ContractStatus.DISPUTED  # Mark as broken
                self.chronicle.record(
                    w.year, "mentor_died",
                    f"{master.first_name if master else 'The master'} died. {apprentice.first_name} {apprentice.family_name}'s apprenticeship ends unfinished.",
                    notable=True, involved_npc_ids=[apprentice.id, master_id],
                )
                continue
            # Teach the skill
            skill = c.terms.get("skill", master.status.occupation)
            current = apprentice.knowledge.skills.get(skill, 0)
            master_skill = master.knowledge.skills.get(skill, 50)
            # Gain = 5-15 per year, scaled by master's skill
            gain = 5 + (master_skill - 50) // 10 + self.rng.randint(0, 5)
            new_skill = min(100, current + max(1, gain))
            apprentice.knowledge.skills[skill] = new_skill
            # End apprenticeship if 7+ years in
            years_in = w.year - c.year_created
            if years_in >= c.terms.get("term_years", 7):
                c.status = ContractStatus.FULFILLED
                apprentice.status.occupation = skill
                self.chronicle.record(
                    w.year, "apprenticeship_complete",
                    f"{apprentice.first_name} {apprentice.family_name} completed their apprenticeship under {master.first_name} {master.family_name}.",
                    notable=True, involved_npc_ids=[apprentice.id, master.id],
                )

    def _check_skill_extinction(self) -> None:
        """If no living NPC has a skill, log it. The town has lost this knowledge."""
        w = self.world
        skill_holders = {}
        for n in w.living_npcs():
            for skill, level in n.knowledge.skills.items():
                if level > 20:
                    if skill not in skill_holders:
                        skill_holders[skill] = 0
                    skill_holders[skill] += 1
        # We log: for each "important" skill, if no one has it, mark extinction.
        important_skills = ["reading", "writing", "midwifery", "healing", "smithing"]
        for skill in important_skills:
            if skill not in skill_holders:
                # Check if anyone used to have it
                had_it = False
                for n in w.npcs.values():
                    if not n.is_alive and n.knowledge.skills.get(skill, 0) > 20:
                        had_it = True
                        break
                if had_it:
                    # Don't spam — only log once per skill per 10 years
                    key = f"extinct_{skill}"
                    last_logged = getattr(self, key, -999)
                    if w.year - last_logged >= 10:
                        setattr(self, key, w.year)
                        self.chronicle.record(
                            w.year, "skill_lost",
                            f"The knowledge of {skill} has left the village. None now living can practice it.",
                            notable=True,
                        )

    def _maybe_call_in_debt(self) -> None:
        w = self.world
        for c in list(w.contracts.values()):
            if c.type != ContractType.DEBT or c.status != ContractStatus.ACTIVE:
                continue
            if not c.parties:
                continue
            creditor = w.npcs.get(c.parties[0])
            debtor = w.npcs.get(c.parties[1]) if len(c.parties) > 1 else None
            if not creditor or not creditor.is_alive or not debtor or not debtor.is_alive:
                continue
            if self.rng.random() < 0.05:
                # Debt called — debtor pays if can, else contract marked disputed
                amount = c.terms.get("amount", 0)
                if debtor.status.coins >= amount:
                    debtor.status.coins -= amount
                    creditor.status.coins += amount
                    c.status = ContractStatus.FULFILLED
                    self.chronicle.record(
                        w.year, "debt_paid",
                        f"{debtor.first_name} {debtor.family_name} paid {amount} coppers to {creditor.first_name} {creditor.family_name}.",
                        involved_npc_ids=[creditor.id, debtor.id],
                    )

    # --- Domain events ---

    def _birth(self, mother: NPC, father: NPC) -> None:
        w = self.world
        import random as _r
        sex = Sex.M if _r.random() < 0.51 else Sex.F
        first = _r.choice(FIRST_NAMES_M if sex == Sex.M else FIRST_NAMES_F)
        family_name = father.family_name if father else mother.family_name
        # Sprint 7: generational infix
        if w.family is not None:
            infix = w.family.name_for_newborn(family_name)
        else:
            infix = ""
        child = NPC(
            first_name=first,
            family_name=family_name,
            sex=sex,
            birth_year=w.year,
            mother_id=mother.id,
            father_id=father.id if father else None,
            legitimacy=True,
        )
        from .npc import TraitSet
        child.mind = TraitSet.random(self.rng, base=mother.mind if self.rng.random() < 0.5 else
                                     (father.mind if father else mother.mind))
        child.body.constitution = (mother.body.constitution + (father.body.constitution if father else 50)) // 2
        from .world import _assign_npc_ambition_and_quirks
        _assign_npc_ambition_and_quirks(child, self.rng)
        w.add_npc(child)
        # Sprint 7: register parent links + ancestor map
        if w.family is not None:
            w.family.register_parents(child.id, mother.id, father.id if father else None)
        if w.ghost is not None:
            w.ghost.register_ancestry(child.id, [mother.id] + ([father.id] if father else []))
        # Family in same house
        if mother.status.household_id:
            child.status.household_id = mother.status.household_id
            house = w.buildings.get(mother.status.household_id)
            if house:
                house.occupant_npc_ids.append(child.id)
        # Mother witnesses birth
        form_memory_of(mother, w.year, "child_born", [child.id, father.id if father else ""], 80)
        # Chronicle
        self.chronicle.record(
            w.year, "birth",
            f"{mother.first_name} {mother.family_name} bore a child, {first}{infix}.",
            involved_npc_ids=[mother.id, child.id] + ([father.id] if father else []),
        )

    def _marry(self, a: NPC, b: NPC) -> None:
        w = self.world
        # Sprint 7: line-of-descent gate
        if w.family is not None:
            ok, reason = w.family.can_marry(
                a.mother_id, a.father_id, b.mother_id, b.father_id, a.id, b.id,
            )
            if not ok:
                # Refuse the marriage silently — won't be recorded.
                return
        c = Contract(
            type=ContractType.MARRIAGE,
            parties=[a.id, b.id],
            witnesses=[],
            year_created=w.year,
            terms={"union_type": "village_wedding"},
            status=ContractStatus.ACTIVE,
            reputation_stake=30,
            notable=True,
            chronicle_summary=f"{a.first_name} {a.family_name} wed {b.first_name} {b.family_name}.",
        )
        w.add_contract(c)
        # Move into one household
        if a.status.household_id:
            c.terms["household_id"] = a.status.household_id
            b.status.household_id = a.status.household_id
            house = w.buildings.get(a.status.household_id)
            if house and b.id not in house.occupant_npc_ids:
                house.occupant_npc_ids.append(b.id)
        # Memory
        form_memory_of(a, w.year, "marriage", [a.id, b.id], 70)
        form_memory_of(b, w.year, "marriage", [a.id, b.id], 70)
        self.chronicle.record(
            w.year, "marriage", c.chronicle_summary,
            involved_npc_ids=[a.id, b.id], notable=True,
        )
        # Sprint 8: wedding ritual, small reputation gain
        if w.religion is not None:
            from .religion import RitualType
            w.religion.perform_ritual(RitualType.WEDDING, w.year,
                                      self.day_in_year, None, [a.id, b.id])
        if w.reputation is not None:
            w.reputation.adjust_town(w.year, 2,
                f"Wedding of {a.first_name} {a.family_name} and {b.first_name} {b.family_name}")

    def _apprentice(self, child: NPC, master: NPC) -> None:
        w = self.world
        c = Contract(
            type=ContractType.APPRENTICESHIP,
            parties=[child.id, master.id],
            year_created=w.year,
            terms={"skill": master.status.occupation, "term_years": 7},
            status=ContractStatus.ACTIVE,
            reputation_stake=20,
            notable=True,
            chronicle_summary=f"{child.first_name} {child.family_name} apprenticed to {master.first_name} {master.family_name} the {master.status.occupation}.",
        )
        w.add_contract(c)
        child.status.occupation = "apprentice"
        self.chronicle.record(w.year, "apprenticeship", c.chronicle_summary,
                              involved_npc_ids=[child.id, master.id], notable=True)

    def _kill(self, npc: NPC, cause: str) -> None:
        w = self.world
        npc.death_year = w.year
        npc.cause_of_death = cause
        npc.anatomy.cause_of_death_detail = f"Died of {cause} in Year {w.year}"
        heir = self._find_heir(npc)
        if heir and w.relics:
            w.relics.inherit_relics_on_death(npc, heir, w.year)
        # Inherit contracts
        for c in w.contracts.values():
            if npc.id in c.parties and c.status == ContractStatus.ACTIVE:
                # find closest living relative
                heir = self._find_heir(npc)
                if heir and heir.id not in c.parties:
                    c.parties.append(heir.id)
                    c.inherited_by.append(heir.id)
        # Free the household slot
        if npc.status.household_id:
            house = w.buildings.get(npc.status.household_id)
            if house and npc.id in house.occupant_npc_ids:
                house.occupant_npc_ids.remove(npc.id)
        # Sprint 7: bury + register ghost
        if w.family is not None:
            w.family.bury(npc.id, f"{npc.first_name} {npc.family_name}",
                          npc.family_name, w.year, cause)
        if w.ghost is not None:
            w.ghost.register_death(
                npc.id, f"{npc.first_name} {npc.family_name}",
                npc.family_name, w.year, cause,
            )
        # The dead have any players mark them as remembered by 2 living
        # witnesses (family/spouse). Threshold of 2 means quiet deaths fade.
        if w.ghost is not None:
            from .npc import LifecycleState
            rememberers = []
            for other in w.living_npcs():
                if other.id == npc.id:
                    continue
                if other.status.household_id and other.status.household_id == npc.status.household_id:
                    rememberers.append(other.id)
                elif other.mother_id == npc.id or other.father_id == npc.id:
                    rememberers.append(other.id)
                # Spouse
                for c in w.contracts.values():
                    if c.type == ContractType.MARRIAGE and c.status == ContractStatus.ACTIVE:
                        if npc.id in c.parties and other.id in c.parties:
                            rememberers.append(other.id)
            for rid in rememberers[:3]:
                w.ghost.remember(npc.id, rid)
        self.chronicle.record(
            w.year, "death",
            f"{npc.first_name} {npc.family_name} ({cause.replace('_', ' ')}, age {w.year - npc.birth_year}) died.",
            involved_npc_ids=[npc.id], notable=True,
        )
        # Sprint 8: religion burial ritual, reputation penalty for violent deaths
        if w.religion is not None:
            temple = next((f for f in (w.factions.factions.values() if w.factions else [])
                          if f.type.value == "temple"), None)
            officiant = temple.leader if temple else None
            participants = rememberers[:3] if rememberers else []
            from .religion import RitualType
            w.religion.perform_ritual(
                RitualType.BURIAL,
                w.year, self.day_in_year, officiant, participants,
            )
        if w.reputation is not None and cause in ("murder", "raid"):
            w.reputation.adjust_town(w.year, -10,
                f"{npc.first_name} {npc.family_name} was killed by violence")

    def _find_heir(self, npc: NPC) -> Optional[NPC]:
        w = self.world
        # Children first, then siblings, then parents, then spouse
        for other in w.living_npcs():
            if other.mother_id == npc.id or other.father_id == npc.id:
                return other
        for other in w.living_npcs():
            if other.mother_id == npc.mother_id and other.id != npc.id:
                return other
        for other in w.living_npcs():
            if other.id in (npc.mother_id, npc.father_id):
                return other
        # Spouse via marriage contract
        for c in w.contracts.values():
            if c.type == ContractType.MARRIAGE and c.status == ContractStatus.ACTIVE:
                if npc.id in c.parties:
                    for p in c.parties:
                        if p != npc.id and w.npcs.get(p) and w.npcs[p].is_alive:
                            return w.npcs[p]
        return None
