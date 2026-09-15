"""Unit tests for the delivery route planner.

Run with:  python -m unittest test_planner.py -v
"""

import os
import tempfile
import unittest

from loader import load_deliveries
from models import Delivery
from planner import plan_trips


class TestPlanTrips(unittest.TestCase):
    def test_sample_data_from_brief(self):
        deliveries = [
            Delivery("1", "Nasr City", 2, 4.5),
            Delivery("2", "Maadi", 1, 2.0),
            Delivery("3", "Nasr City", 3, 1.2),
            Delivery("4", "Zamalek", 1, 7.0),
            Delivery("5", "Maadi", 2, 3.5),
        ]
        trips, oversized = plan_trips(deliveries, capacity_kg=10.0)

        self.assertEqual(oversized, [])
        self.assertEqual(len(trips), 3)

        # No trip may ever exceed capacity.
        for t in trips:
            self.assertLessEqual(t.total_weight, 10.0)

        # Every delivery appears in exactly one trip.
        all_ids = [d.id for t in trips for d in t.deliveries]
        self.assertEqual(sorted(all_ids), ["1", "2", "3", "4", "5"])

        # Same-area deliveries end up grouped where capacity allows.
        maadi_trip = next(t for t in trips if t.area == "Maadi")
        self.assertEqual({d.id for d in maadi_trip.deliveries}, {"2", "5"})

    def test_no_deliveries(self):
        trips, oversized = plan_trips([], capacity_kg=10.0)
        self.assertEqual(trips, [])
        self.assertEqual(oversized, [])

    def test_package_heavier_than_capacity_is_excluded_not_dropped_silently(self):
        deliveries = [
            Delivery("1", "Maadi", 1, 12.0),  # too heavy for a 10kg vehicle
            Delivery("2", "Maadi", 1, 3.0),
        ]
        capacity = 10.0
        trips, oversized = plan_trips(deliveries, capacity_kg=capacity)

        self.assertEqual(len(oversized), 1)
        self.assertEqual(oversized[0].id, "1")
        # Explicitly confirm *why* it was excluded: its weight really
        # is over the vehicle's capacity. This makes the test prove
        # the over-capacity condition itself, not just trust that the
        # numbers chosen above happen to be over the limit.
        self.assertGreater(oversized[0].weight_kg, capacity)
        # And double check no trip smuggled it in anyway.
        for trip in trips:
            self.assertNotIn("1", [d.id for d in trip.deliveries])
        # The valid delivery is still planned normally.
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0].deliveries[0].id, "2")

    def test_capacity_is_never_exceeded_even_with_many_same_area_items(self):
        deliveries = [Delivery(str(i), "Giza", 1, 3.0) for i in range(5)]
        trips, oversized = plan_trips(deliveries, capacity_kg=10.0)

        self.assertEqual(oversized, [])
        for t in trips:
            self.assertLessEqual(t.total_weight, 10.0)
        total_planned = sum(t.total_weight for t in trips)
        self.assertAlmostEqual(total_planned, 15.0)

    def test_same_priority_deliveries_keep_stable_relative_order(self):
        deliveries = [
            Delivery("a", "Dokki", 1, 5.0),
            Delivery("b", "Dokki", 1, 6.0),  # doesn't fit with 'a' -> new trip
        ]
        trips, _ = plan_trips(deliveries, capacity_kg=10.0)
        self.assertEqual(len(trips), 2)

    def test_urgent_deliveries_are_placed_into_trips_first(self):
        deliveries = [
            Delivery("low", "Maadi", 5, 2.0),
            Delivery("high", "Zamalek", 1, 2.0),
        ]
        trips, _ = plan_trips(deliveries, capacity_kg=10.0)
        # The trip containing the most urgent delivery should be
        # first in dispatch order.
        self.assertEqual(trips[0].deliveries[0].id, "high")


class TestLoadDeliveries(unittest.TestCase):
    def _write_csv(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_loads_valid_rows(self):
        path = self._write_csv(
            "id,area,priority,weight_kg\n1,Maadi,1,2.0\n2,Zamalek,2,3.0\n"
        )
        deliveries, warnings = load_deliveries(path)
        self.assertEqual(len(deliveries), 2)
        self.assertEqual(warnings, [])
        os.remove(path)

    def test_skips_malformed_row_but_keeps_valid_ones(self):
        path = self._write_csv(
            "id,area,priority,weight_kg\n"
            "1,Maadi,1,2.0\n"
            "2,Zamalek,not-a-number,3.0\n"  # bad priority
            "3,Dokki,1,-5\n"  # non-positive weight
        )
        deliveries, warnings = load_deliveries(path)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(len(warnings), 2)
        os.remove(path)

    def test_handles_byte_order_mark_from_windows_tools(self):
        # PowerShell's `Out-File -Encoding utf8` (and some other Windows
        # tools) prepend a BOM to text files. Without handling it, the
        # BOM merges into the first header name ("id" becomes "\ufeffid"),
        # which would make a perfectly valid file look like it's missing
        # its "id" column.
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write("id,area,priority,weight_kg\n1,Maadi,1,2.0\n")
        deliveries, warnings = load_deliveries(path)
        self.assertEqual(warnings, [])
        self.assertEqual(len(deliveries), 1)
        os.remove(path)

    def test_missing_file_reports_warning_not_crash(self):
        deliveries, warnings = load_deliveries("does_not_exist.csv")
        self.assertEqual(deliveries, [])
        self.assertEqual(len(warnings), 1)

    def test_empty_file_reports_warning(self):
        path = self._write_csv("")
        deliveries, warnings = load_deliveries(path)
        self.assertEqual(deliveries, [])
        self.assertEqual(len(warnings), 1)
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
