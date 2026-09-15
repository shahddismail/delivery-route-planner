"""Reads delivery requests from a CSV file.

Expected format (header required):

    id,area,priority,weight_kg
    1,Nasr City,2,4.5

`priority` must be an integer (lower = more urgent).
`weight_kg` must be a positive number.
"""

import csv
from typing import List, Tuple

from models import Delivery


def load_deliveries(path: str) -> Tuple[List[Delivery], List[str]]:
    """Load deliveries from a CSV file.

    Returns (deliveries, warnings). Rows that are malformed (missing
    fields, non-numeric priority/weight, non-positive weight) are
    skipped and reported as warnings rather than crashing the whole
    program -- one bad row in a large file shouldn't take down the
    entire run.
    """
    deliveries: List[Delivery] = []
    warnings: List[str] = []

    try:
        # utf-8-sig transparently strips a leading byte-order-mark (BOM)
        # if one is present -- Windows tools like PowerShell's Out-File
        # commonly add one, which would otherwise corrupt the first
        # header name (e.g. "id" becoming "\ufeffid") and make the
        # column-check below fail even though the file looks correct.
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                warnings.append(f"Input file '{path}' is empty (no header row).")
                return deliveries, warnings

            required = {"id", "area", "priority", "weight_kg"}
            missing = required - set(h.strip() for h in reader.fieldnames)
            if missing:
                warnings.append(
                    f"Input file is missing required column(s): {sorted(missing)}"
                )
                return deliveries, warnings

            for line_num, row in enumerate(reader, start=2):  # header is line 1
                try:
                    delivery_id = row["id"].strip()
                    area = row["area"].strip()
                    priority = int(row["priority"].strip())
                    weight = float(row["weight_kg"].strip())

                    if not delivery_id:
                        raise ValueError("empty id")
                    if not area:
                        raise ValueError("empty area")
                    if weight <= 0:
                        raise ValueError(f"non-positive weight ({weight})")

                    deliveries.append(
                        Delivery(id=delivery_id, area=area, priority=priority, weight_kg=weight)
                    )
                except (KeyError, ValueError, AttributeError) as exc:
                    warnings.append(f"Skipping line {line_num}: {exc}")

    except FileNotFoundError:
        warnings.append(f"Input file not found: {path}")

    return deliveries, warnings
