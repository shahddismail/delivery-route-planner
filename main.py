"""Delivery Route Planner -- CLI entry point.

Usage:
    python main.py --input sample_deliveries.csv
    python main.py --input sample_deliveries.csv --capacity 10 --json out.json
"""

import argparse
import json
import sys

from loader import load_deliveries
from planner import plan_trips


def build_report(trips, oversized, capacity_kg):
    """Extension feature: a trip summary report.

    For each trip this shows the dispatch order, the area(s) served,
    which deliveries are on it, and how full the vehicle is (capacity
    utilization). It also gives an overall summary. This is the kind
    of thing a dispatcher would actually look at each morning to
    decide which trip goes out first and whether trips are being
    packed efficiently -- so it turns the raw grouping into something
    directly usable, not just a data structure.
    """
    trip_rows = []
    for idx, trip in enumerate(trips, start=1):
        areas = sorted({d.area for d in trip.deliveries})
        utilization = round((trip.total_weight / trip.capacity_kg) * 100, 1)
        trip_rows.append(
            {
                "trip_number": idx,
                "dispatch_priority": trip.min_priority,
                "areas": areas,
                "delivery_ids": [d.id for d in trip.deliveries],
                "total_weight_kg": trip.total_weight,
                "capacity_kg": trip.capacity_kg,
                "utilization_pct": utilization,
            }
        )

    avg_utilization = (
        round(sum(r["utilization_pct"] for r in trip_rows) / len(trip_rows), 1)
        if trip_rows
        else 0.0
    )

    return {
        "vehicle_capacity_kg": capacity_kg,
        "trip_count": len(trip_rows),
        "average_utilization_pct": avg_utilization,
        "trips": trip_rows,
        "unassignable_deliveries": [
            {"id": d.id, "area": d.area, "weight_kg": d.weight_kg}
            for d in oversized
        ],
    }


def print_report(report):
    if report["trip_count"] == 0:
        print("No trips were created (no valid deliveries to plan).")
    else:
        print(f"Vehicle capacity: {report['vehicle_capacity_kg']} kg")
        print(f"Trips planned: {report['trip_count']}")
        print(f"Average capacity utilization: {report['average_utilization_pct']}%\n")

        for t in report["trips"]:
            print(
                f"Trip {t['trip_number']} "
                f"(dispatch priority {t['dispatch_priority']}) "
                f"- areas: {', '.join(t['areas'])}"
            )
            print(f"  deliveries: {', '.join(t['delivery_ids'])}")
            print(
                f"  weight: {t['total_weight_kg']}kg / {t['capacity_kg']}kg "
                f"({t['utilization_pct']}% full)"
            )
            print()

    if report["unassignable_deliveries"]:
        print("Unassignable deliveries (package exceeds vehicle capacity):")
        for d in report["unassignable_deliveries"]:
            print(f"  id={d['id']} area={d['area']} weight={d['weight_kg']}kg")


def main():
    parser = argparse.ArgumentParser(description="Delivery Route Planner")
    parser.add_argument(
        "--input", default="sample_deliveries.csv", help="Path to the input CSV file."
    )
    parser.add_argument(
        "--capacity", type=float, default=10.0, help="Vehicle capacity in kg."
    )
    parser.add_argument(
        "--json", metavar="PATH", help="Optional path to also write the report as JSON."
    )
    args = parser.parse_args()

    deliveries, warnings = load_deliveries(args.input)

    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    if not deliveries:
        print("No valid deliveries found. Nothing to plan.")
        report = build_report([], [], args.capacity)
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        return

    trips, oversized = plan_trips(deliveries, capacity_kg=args.capacity)
    report = build_report(trips, oversized, args.capacity)
    print_report(report)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report written to {args.json}")


if __name__ == "__main__":
    main()
