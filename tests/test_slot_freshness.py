"""
Unit tests for SlotInfo freshness verification & mid-bake currency logic.
"""

import datetime
import unittest
from greedbot.models import SlotInfo


class TestSlotFreshness(unittest.TestCase):

    def setUp(self):
        self.valid_payload = {
            "slot": {
                "year": 2026,
                "refresh_n": 139,
                "interval": "day",
                "quote_type": "equity",
                "effective_at": "2026-07-24T00:00:00Z",
                "effective_until": "2026-07-25T00:00:00Z",
            }
        }

    def test_slot_parsing_and_in_window(self):
        slot = SlotInfo.from_payload(self.valid_payload)
        self.assertIsNotNone(slot)
        self.assertEqual(slot.year, 2026)
        self.assertEqual(slot.refresh_n, 139)
        self.assertEqual(slot.interval, "day")

        # Inside window
        dt_inside = datetime.datetime.fromisoformat("2026-07-24T12:00:00+00:00")
        self.assertTrue(slot.is_effective_at(dt_inside))

        # Start instant is inclusive
        dt_start = datetime.datetime.fromisoformat("2026-07-24T00:00:00+00:00")
        self.assertTrue(slot.is_effective_at(dt_start))

        # End instant is EXCLUSIVE (belongs to next slot)
        dt_end = datetime.datetime.fromisoformat("2026-07-25T00:00:00+00:00")
        self.assertFalse(slot.is_effective_at(dt_end))

        # Before window
        dt_before = datetime.datetime.fromisoformat("2026-07-23T23:59:59+00:00")
        self.assertFalse(slot.is_effective_at(dt_before))

    def test_mid_bake_superseded_slot_is_stale(self):
        # Yesterday's slot served during today's bake
        yesterday_payload = {
            "slot": {
                "year": 2026,
                "refresh_n": 138,
                "interval": "day",
                "quote_type": "equity",
                "effective_at": "2026-07-23T00:00:00Z",
                "effective_until": "2026-07-24T00:00:00Z",
            }
        }
        slot = SlotInfo.from_payload(yesterday_payload)
        self.assertIsNotNone(slot)

        # 30 seconds into next day's bake (00:00:30 UTC)
        bake_time = datetime.datetime.fromisoformat("2026-07-24T00:00:30+00:00")
        self.assertFalse(slot.is_effective_at(bake_time))

    def test_friday_slot_spans_weekend(self):
        friday_payload = {
            "slot": {
                "year": 2026,
                "refresh_n": 140,
                "interval": "day",
                "quote_type": "equity",
                "effective_at": "2026-07-25T00:00:00Z",
                "effective_until": "2026-07-28T00:00:00Z",
            }
        }
        slot = SlotInfo.from_payload(friday_payload)
        self.assertIsNotNone(slot)

        # Sunday during closed market
        sunday = datetime.datetime.fromisoformat("2026-07-26T18:00:00+00:00")
        self.assertTrue(slot.is_effective_at(sunday))

        # Tuesday when next bake occurs
        tuesday = datetime.datetime.fromisoformat("2026-07-28T00:00:00+00:00")
        self.assertFalse(slot.is_effective_at(tuesday))

    def test_invalid_slot_payloads(self):
        self.assertIsNone(SlotInfo.from_payload({}))
        self.assertIsNone(SlotInfo.from_payload({"slot": None}))
        self.assertIsNone(SlotInfo.from_payload({"slot": {"year": "bad"}}))

        # Malformed timestamps fail toward not effective
        broken = SlotInfo.from_payload({
            "slot": {
                "year": 2026,
                "refresh_n": 1,
                "interval": "day",
                "quote_type": "equity",
                "effective_at": "not-a-date",
                "effective_until": "not-a-date",
            }
        })
        self.assertIsNotNone(broken)
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse(broken.is_effective_at(now))


if __name__ == "__main__":
    unittest.main()
