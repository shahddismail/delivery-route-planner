"""Data model for the Delivery Route Planner.

Kept deliberately small: a Delivery is just the four fields the
assignment describes, and a Trip is a bag of deliveries that knows
how much capacity it has left.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Delivery:
    """A single delivery request."""
    id: str
    area: str
    priority: int
    weight_kg: float


@dataclass
class Trip:
    """A single vehicle trip: a group of deliveries that together
    respect the vehicle's weight capacity.
    """
    capacity_kg: float
    area: str
    deliveries: list = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        return round(sum(d.weight_kg for d in self.deliveries), 3)

    @property
    def remaining_capacity(self) -> float:
        return round(self.capacity_kg - self.total_weight, 3)

    def can_fit(self, delivery: Delivery) -> bool:
        return delivery.weight_kg <= self.remaining_capacity + 1e-9

    def add(self, delivery: Delivery) -> None:
        if not self.can_fit(delivery):
            raise ValueError(
                f"Delivery {delivery.id} ({delivery.weight_kg}kg) does not "
                f"fit in trip with {self.remaining_capacity}kg remaining."
            )
        self.deliveries.append(delivery)

    @property
    def min_priority(self) -> int:
        """Lowest (= most urgent) priority number among this trip's
        deliveries. Used to order trips for dispatch."""
        return min(d.priority for d in self.deliveries)
