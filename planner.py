"""Core algorithm: turns a list of Deliveries into a list of Trips.

Approach (see README for the full explanation):

1. Split off any delivery whose weight alone exceeds vehicle capacity --
   it can never fit in any trip, so it's reported separately instead of
   silently dropped or crashing the program.
2. Sort the remaining deliveries by priority (ascending = more urgent
   first). The sort is stable, so deliveries that share a priority
   keep their original relative order.
3. Walk the sorted list once. For each delivery, try to place it into
   an already-open trip that (a) serves the same area and (b) has
   enough remaining capacity. If no such trip exists, start a new
   trip for that area.

This keeps the primary ordering promise (urgent deliveries are placed
into trips first) while still grouping same-area deliveries together
whenever there's room -- exactly the two requirements the brief asks
for, in priority order.
"""

from typing import List, Tuple

from models import Delivery, Trip


def plan_trips(
    deliveries: List[Delivery], capacity_kg: float = 10.0
) -> Tuple[List[Trip], List[Delivery]]:
    """Group deliveries into capacity-respecting trips.

    Returns (trips, oversized_deliveries). `trips` are ordered by the
    most urgent priority they contain, so the first trip returned is
    the one that should be dispatched first.
    """
    if capacity_kg <= 0:
        raise ValueError("Vehicle capacity must be positive.")

    fits = [d for d in deliveries if d.weight_kg <= capacity_kg]
    oversized = [d for d in deliveries if d.weight_kg > capacity_kg]

    # Stable sort: ties keep their original (input) order.
    ordered = sorted(fits, key=lambda d: d.priority)

    open_trips: List[Trip] = []

    for delivery in ordered:
        target = next(
            (t for t in open_trips if t.area == delivery.area and t.can_fit(delivery)),
            None,
        )
        if target is None:
            target = Trip(capacity_kg=capacity_kg, area=delivery.area)
            open_trips.append(target)
        target.add(delivery)

    open_trips.sort(key=lambda t: t.min_priority)
    return open_trips, oversized
