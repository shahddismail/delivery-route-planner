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

Python 3.8+. No third-party packages -- only the standard library.

## How to run
1. Clone the repository (or download and unzip it if you received it as a
   ZIP file):
   ```bash
   git clone https://github.com/shahddismail/delivery-route-planner.git
   ```

2. Move into the project folder — every command below assumes you're
   standing inside it:
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
python main.py --input <filename>
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

There are 10 tests covering the core requirements (capacity never
exceeded, every delivery placed exactly once, same-area grouping) and
every edge case listed in the brief (empty input, oversized package,
tied priorities, a package that would push a trip over capacity).

---

## Reasoning

### 1. Solution approach, in my own words

Every delivery has to end up in exactly one trip, no trip can exceed
the weight limit, urgent deliveries should be handled first, and
deliveries to the same area should travel together when that's
practical. Two of those rules (priority order and area grouping) can
pull in different directions, so I treated **priority as the primary
ordering rule** and **area grouping as an opportunistic optimization**
applied on top of it, rather than the other way round — the brief
says urgent deliveries "should be handled first," which reads as the
harder constraint.

Concretely:

1. Deliveries heavier than the vehicle capacity are pulled out first
   — they can never be assigned to any trip, so they're reported
   separately instead of silently vanishing or crashing the program.
2. The rest are sorted by priority (ascending), with a **stable
   sort** so that deliveries sharing a priority keep their original
   order rather than being reordered arbitrarily.
3. I walk that list once. For each delivery, I look for an
   **already-open trip serving the same area with enough remaining
   capacity** and add it there; if none exists, I open a new trip.
4. Trips are finally ordered for dispatch by the most urgent priority
   they contain.

This is a greedy, single-pass algorithm — it never backtracks or
reshuffles a trip once created. I chose greedy over an optimal
bin-packing search deliberately (see Q3): it's easy to read, easy to
reason about, and its behavior in every edge case is predictable,
which matched what the brief said it was looking for.

### 2. What was the most difficult part of the assignment?

Deciding how to resolve the tension between "group by area" and
"handle urgent deliveries first" when they conflict — e.g. an urgent
delivery in an area with no open trip yet, arriving just before a
low-priority delivery to the same area that would have grouped
perfectly. There's no single "correct" answer here; I picked the
interpretation above and made sure it was documented and tested,
which felt more important than trying to guess the "intended" answer.

### 3. Situations where the algorithm may not produce the best possible grouping

Yes. Because it's a single greedy pass with no backtracking, it can
make locally reasonable choices that aren't globally optimal:

- If an early, low-capacity trip for an area gets "topped up" with a
  small delivery, a much better-fitting delivery to the same area
  arriving later may no longer fit, and ends up starting a second,
  under-utilized trip for that same area.
- The algorithm never merges two already-open trips serving the same
  area even if their combined weight would fit under capacity, and it
  never reorders deliveries within a priority tier to improve
  packing.

In other words, it solves a variant of bin packing, which is NP-hard
in general — an exact optimal solution would need to consider
reordering or repacking, which conflicts with keeping priority order
intact and would add real complexity for a marginal packing
improvement.

### 4. If the input contained 1,000,000 delivery requests...

- **The area-matching step** is the main risk: for each delivery, I
  scan the list of currently open trips to find one with a matching
  area and free capacity. In the worst case (many distinct areas, so
  many simultaneously open trips), that scan is `O(number of open
  trips)` per delivery, so the whole pass can degrade toward
  `O(n × number of areas)`. The fix is to index open trips by area
  (`dict[area] -> list of open trips with room`) so that lookup is
  `O(1)` instead of a linear scan — straightforward to add, just not
  necessary at this scale to keep the code readable.
- **Loading the whole file into memory as a list of `Delivery`
  objects** would also become significant at 1,000,000 rows (roughly
  hundreds of MB depending on the object overhead). Streaming/batching
  the CSV instead of materializing the full list up front would help
  if memory became a real constraint.
- Sorting a million items by priority is fine (`O(n log n)`, well
  within milliseconds in practice) — that part isn't a concern.

### 5. What I'd improve with another day

- Index open trips by area (as above) to make the algorithm scale
  cleanly to very large inputs.
- Add an optional "best-fit" mode: instead of taking the first open
  trip that fits, pick the one that leaves the least leftover
  capacity, which tends to reduce the total number of trips.
- Support JSON input as well as CSV (the loader already isolates
  file-reading from the algorithm, so this would be a small addition
  behind the same `Delivery` interface).
- Add a way to merge two under-full open trips for the same area at
  the end of the run, if their combined weight still fits — this
  would recover some of the packing quality lost to the single-pass
  greedy approach without abandoning it.

---

## My extension: trip summary report

On top of the required grouping, `main.py` builds a **trip summary
report**: for every trip it shows the suggested dispatch order (based
on the most urgent delivery it contains), which areas it covers,
which delivery IDs are on it, and its **capacity utilization** (how
full the vehicle is, as a percentage). It also prints an overall
average utilization across all trips, and lists any deliveries that
couldn't be assigned because they exceed the vehicle's capacity.

I picked this because it's the smallest addition that turns the raw
grouping into something a dispatcher could actually act on the same
morning — which trip to send out first, and whether trips are
generally being packed efficiently — rather than just a data
structure. It's also available as JSON (`-python main.py --input sample_deliveries.csv --json report.json`) so it
could be consumed by another system instead of only read by a human.
