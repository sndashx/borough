"""Sprint 7: Family + Ghost subsystems.

Tests:
  test_family_no_incest — multi-generation in-pair coupling yields no overlap
  test_ghost_threshold  — only ≥2 remembers write preface
  test_feud_state_machine — attack/murder escalate, truce lowers
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.family import FamilyRegistry, FeudState
from core.ghost import GhostCausalLedger


class TestFamilyNoIncest(unittest.TestCase):
    def test_family_no_incest(self):
        reg = FamilyRegistry()
        # Simulate 4 generations of in-pair coupling.
        # Each gen: parents from prior gen's children, but cousin-cousin
        # coupling must be caught.
        # p0, p1 are founding couple
        # g1a, g1b are their children
        # g2 is g1a's child
        # g3 is g2's child
        # Forbid: g3 marrying g1a (grandparent) or g1b (great-uncle/aunt)
        reg.register_parents("g1a", "p0", "p1")
        reg.register_parents("g1b", "p0", "p1")
        reg.register_parents("g2", "g1a", "x1")
        reg.register_parents("g3", "g2", "x2")
        # g3 <-> g1a: grandparent — must be forbidden
        ok, reason = reg.can_marry(None, None, "p0", "p1", "g3", "g1a")
        self.assertFalse(ok, "grandparent marriage should be blocked")
        self.assertTrue(reason.startswith("line_of_descent"))
        # g3 <-> g1b: great-aunt — must be forbidden
        ok, _ = reg.can_marry(None, None, "p0", "p1", "g3", "g1b")
        self.assertFalse(ok, "great-aunt marriage should be blocked")
        # g3 <-> x1: great-grandparent (parent's mother) — must be forbidden
        ok, _ = reg.can_marry(None, None, "g1a", None, "g3", "x1")
        self.assertFalse(ok, "parent-of-parent marriage should be blocked")
        # g3 <-> outsider y — allowed
        ok, _ = reg.can_marry(None, None, "ym", "yf", "g3", "y")
        self.assertTrue(ok, "marriage to unrelated outsider should be allowed")

    def test_can_marry_unrelated(self):
        reg = FamilyRegistry()
        ok, _ = reg.can_marry("a", "b", "c", "d", "x", "y")
        self.assertTrue(ok)

    def test_name_for_newborn(self):
        reg = FamilyRegistry()
        self.assertEqual(reg.name_for_newborn("Alder"), "")
        self.assertEqual(reg.name_for_newborn("Alder"), " the Younger")
        self.assertEqual(reg.name_for_newborn("Alder"), " the Elder")
        self.assertEqual(reg.name_for_newborn("Alder"), " the Middle")
        # Family counter is per-family
        self.assertEqual(reg.name_for_newborn("Brandt"), "")


class TestGhostThreshold(unittest.TestCase):
    def test_ghost_threshold(self):
        led = GhostCausalLedger(default_threshold=2)
        # Register a ghost
        led.register_death("g1", "Aldric", "Alder", 100, "old_age")
        # No one remembers yet — preface is empty
        self.assertEqual(led.preface_for_player("p1", "Alder"), [])
        # One rememberer — still under threshold
        led.remember("g1", "n1")
        self.assertEqual(led.preface_for_player("p1", "Alder"), [])
        # Two rememberers — clears threshold
        led.remember("g1", "n2")
        preface = led.preface_for_player("p1", "Alder")
        self.assertEqual(len(preface), 1)
        self.assertIn("Aldric", preface[0])
        self.assertIn("Alder", preface[0])

    def test_has_remembrance(self):
        led = GhostCausalLedger()
        led.register_death("g1", "Bryn", "Brandt", 50, "disease")
        self.assertFalse(led.has_remembrance("g1"))
        led.remember("g1", "n1")
        self.assertFalse(led.has_remembrance("g1", n=2))
        led.remember("g1", "n2")
        self.assertTrue(led.has_remembrance("g1", n=2))

    def test_ancestor_filter(self):
        led = GhostCausalLedger()
        led.register_death("g1", "Cera", "Chen", 100, "old_age")
        led.register_death("g2", "Dalla", "Drost", 110, "old_age")
        # g1 is a direct ancestor of p1, g2 is not
        led.register_ancestry("p1", ["g1"])
        # Both remembered equally
        led.remember("g1", "n1")
        led.remember("g1", "n2")
        led.remember("g2", "n1")
        led.remember("g2", "n2")
        preface = led.preface_for_player("p1")
        # Only g1 qualifies
        self.assertEqual(len(preface), 1)
        self.assertIn("Cera", preface[0])


class TestFeudStateMachine(unittest.TestCase):
    def test_feud_state_machine(self):
        reg = FamilyRegistry()
        # Initial — neutral
        self.assertEqual(reg.feud_state("Alder", "Brandt"), FeudState.NEUTRAL)
        # Insult → GRUDGE
        s = reg.escalate("Alder", "Brandt", 1)
        self.assertEqual(s, FeudState.GRUDGE)
        # Assault → FEUD
        s = reg.escalate("Alder", "Brandt", 2)
        self.assertEqual(s, FeudState.FEUD)
        # Murder → BLOOD
        s = reg.escalate("Alder", "Brandt", 3)
        self.assertEqual(s, FeudState.BLOOD)
        # Truce walks it down
        s = reg.truce("Alder", "Brandt")
        self.assertEqual(s, FeudState.FEUD)
        s = reg.truce("Alder", "Brandt")
        self.assertEqual(s, FeudState.GRUDGE)
        s = reg.truce("Alder", "Brandt")
        self.assertEqual(s, FeudState.TRUCE)
        s = reg.truce("Alder", "Brandt")
        self.assertEqual(s, FeudState.NEUTRAL)
        # Same family — no feud
        self.assertEqual(reg.feud_state("Alder", "Alder"), FeudState.NEUTRAL)
        self.assertEqual(reg.escalate("Alder", "Alder", 3), FeudState.NEUTRAL)

    def test_tombstone_lifecycle(self):
        reg = FamilyRegistry()
        reg.bury("n1", "Aldric", "Alder", 100, "old_age")
        t = reg.tombstone_by_npc["n1"]
        self.assertEqual(t.remembered_by, 0)
        reg.remember("n1")
        reg.remember("n1")
        self.assertEqual(reg.tombstone_by_npc["n1"].remembered_by, 2)
        reg.forget("n1")
        self.assertEqual(reg.tombstone_by_npc["n1"].remembered_by, 0)


if __name__ == "__main__":
    unittest.main()
