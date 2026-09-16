# Delivery Route Planner

A small program that groups delivery requests into vehicle trips,
respecting a maximum trip weight, grouping same-area deliveries
together where possible, and handling the most urgent deliveries
first.



## Project structure

```
delivery-route-planner/
├── main.py              # CLI entry point
├── planner.py            # core grouping algorithm
├── loader.py              # reads and validates the input CSV
├── models.py               # Delivery / Trip data classes
├── test_planner.py          # unit tests
├── sample_deliveries.csv     # sample input (the data from the brief)
└── README.md
```

## Requirements

Python 3.7+. No third-party packages -- only the standard library.

## How to run
1. Clone the repository (or download and unzip it if you received it as a
   ZIP file):
   ```bash
   git clone https://github.com/shahddismail/delivery-route-planner.git
   ```

2. Make sure to be in the project folder — if not:
   ```bash
   cd delivery-route-planner
   ```

3. Run the program on the included sample data:
   ```bash
   python main.py --input sample_deliveries.csv
   ```
   (On some systems the command is `python3` instead of `python`.)

Optional flags:

```bash
# use a different vehicle capacity (kg)
python main.py --input sample_deliveries.csv --capacity 12

# also write the same report as JSON
python main.py --input sample_deliveries.csv --json report.json
```

### Input format

CSV with a header row:

```
id,area,priority,weight_kg
1,Nasr City,2,4.5
```

- `id` — any non-empty string.
- `area` — delivery area (free text, e.g. a neighborhood name).
- `priority` — integer; **lower means more urgent**.
- `weight_kg` — positive number.

## Example inputs for each edge case

Beyond `sample_deliveries.csv`, four extra input files are included, one
per edge case named in the brief. Each can be run the same way:

```bash
 python main.py --input example_no_deliveries.csv
 python main.py --input example_oversized_package.csv
 python main.py --input example_same_priority.csv
 python main.py --input example_capacity_exceeded.csv
```

**`example_no_deliveries.csv`** — a file with a header row but no delivery
rows. Expected output:

```
No valid deliveries found. Nothing to plan.
```

**`example_oversized_package.csv`** — one delivery (12kg) exceeds the
vehicle's 10kg capacity, alongside one normal delivery. The 12kg delivery
is reported under "Unassignable deliveries" instead of being forced into
a trip, while the other delivery is planned normally.

**`example_same_priority.csv`** — three deliveries, all priority 1, in
three different areas. All three are handled (as three separate trips,
since they don't share an area to group into), each correctly shown at
the same dispatch priority.

**`example_capacity_exceeded.csv`** — two same-area deliveries (6kg and
5kg) that together would total 11kg. Even though they share an area and
would normally be grouped, the second one doesn't fit alongside the
first (only 4kg of capacity would be left), so it correctly starts a
second trip instead of pushing the first one over capacity.

## Running the tests

```bash
python -m unittest test_planner.py -v
```

There are 11 tests covering the core requirements (capacity never
exceeded, every delivery placed exactly once, same-area grouping) and
every edge case listed in the brief (empty input, oversized package,
tied priorities, a package that would push a trip over capacity).

---

## Reasoning

### 1. Solution approach, in my own words

I treated priority as the main rule and area grouping as a bonus on top of it — the brief says urgent deliveries "should be handled first," which reads as the stricter requirement.

Steps:
1. Pull out any delivery heavier than the vehicle capacity first — it can never go on any trip, so it's reported separately instead of crashing or vanishing.
2. Sort what's left by priority (stable sort, so ties keep their original order).
3. Go through that list once. For each delivery, try to add it to an already-open trip with the same area that still has room. If none fits, start a new trip.
4. Order the finished trips by their most urgent delivery, for dispatch.

It's a single-pass greedy algorithm — no backtracking. I picked greedy over a more optimal packing search because it's simple to read, easy to trace by hand, and behaves predictably in every edge case.

### 2. What was the most difficult part of the assignment?

Deciding what to do when "group by area" and "handle urgent ones first" conflict — like an urgent delivery arriving before a same-area delivery that would've grouped nicely. There's no single correct answer here, so I picked one interpretation, documented it, and tested it.

### 3. Situations where the algorithm may not produce the best possible grouping

Yes. Since it's a single pass with no backtracking, it can lock in a choice that isn't ideal:
- An early trip for an area might get topped up with a small delivery, so a better-fitting one for that same area arrives later and no longer fits — it starts a second, less full trip instead.
- It never merges two open trips for the same area even if they'd fit together combined, and never reorders deliveries within a priority tier to pack better.

This is really a version of bin packing, which is NP-hard in general, so an exact best answer would need reordering/repacking that conflicts with keeping priority order intact.

### 4. If the input contained 1,000,000 delivery requests...

- The area-lookup step is the main risk — for each delivery I scan the open trips list for a matching area. With many distinct areas, that's roughly O(n × areas). Indexing open trips by area (a dict) would make this O(1) instead — easy fix, just not needed at this scale.
- Holding all deliveries in memory as objects would also add up at a million rows. Streaming the file instead of loading it all at once would help if memory became tight.
- Sorting a million items by priority is fine — O(n log n) is not a real concern here.

### 5. What I'd improve with another day

- Index open trips by area, for the scaling reason above.
- A "best-fit" mode that picks the trip with the least leftover space instead of the first one that fits, to reduce total trip count.
- Support JSON input as well as CSV.
- Merge under-full same-area trips at the end of a run if their combined weight still fits.

---

## My extension: trip summary report

On top of the required grouping, `main.py` prints a summary for each trip: suggested dispatch order, which areas it covers, which delivery IDs are on it, and how full it is by weight (a percentage). It also shows an overall average utilization, and lists any deliveries that couldn't be assigned because they're too heavy.

I picked this because it turns the raw grouping into something a dispatcher could actually use that morning — which trip to send first, and whether trips are packed efficiently — instead of just a data structure. It's also available as JSON (`-python main.py --input sample_deliveries.csv --json report.json`) for another system to read.
