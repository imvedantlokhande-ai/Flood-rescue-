# Test Suite: Unit and Integration Testing

This folder contains exhaustive unit tests and scenario edge case validations for all scratch-built data structures, search algorithms, and evacuation planning modules.

---

## 1. What This Test Suite Does

Verifies mathematical correctness and boundary handling for 21 test scenarios:
- **Queue**: FIFO ordering, capacity dynamics, boundary exceptions.
- **Stack**: LIFO ordering, top pointer tracking, boundary exceptions.
- **Min-Heap**: Minimum element extraction, heap property maintenance across random insertions, `decrease_key` operations.
- **Graph**: Adjacency construction, dynamic edge blocking and unblocking, neighbor filtering.
- **Flood Risk**: Rule-based scoring across LOW, MODERATE, HIGH, and SEVERE hydrological conditions.
- **Flood Marker**: Edge blocking thresholds and risk multipliers.
- **BFS**: Level traversal correctness, hop distance computation, fewest-turns path.
- **DFS**: Consistency between iterative stack traversal and recursive traversal.
- **Connected Components**: Detection of isolated subgraphs and cut-off / stranded population clusters.
- **Dijkstra**: True shortest path computation, avoidance of flooded edges, tie-breaking.
- **Edge Cases**:
  - Origin node is already a safe zone (returns 0 km, path with 1 node).
  - All outgoing roads flooded (reports stranded alert: "NO SAFE ROUTE - REQUEST RESCUE").
  - Benign weather (reports "No evacuation needed").

---

## 2. Why It Is Used in This Project (Flood-Specific Reason)

Evacuation software directly impacts human safety during flash floods. A single off-by-one error or heap priority inversion in Dijkstra's algorithm could route evacuees across a submerged 1.2-meter deep river crossing or direct them to a severed bridge. Unit tests systematically prove algorithm correctness across edge cases before deployment.

---

## 3. How It Works, Step by Step

1. Uses Python's standard `unittest` framework (requiring no external dependencies).
2. Sets up isolated mock graphs (`setUp`) representing canonical topologies:
   - Diamond networks
   - Island disconnects
   - Unweighted vs. weighted path contrasts
3. Runs each algorithm against predictable analytical ground truths.
4. Asserts conditions via `assertEqual`, `assertTrue`, `assertFalse`, and `assertRaises`.

---

## 4. Small Worked Example

```text
Diamond Graph Test:
  A -- (10 km) -- B -- (10 km) -- D     (2 hops, 20 km)
  A -- (1 km) -- C -- (1 km) -- D       (2 hops, 2 km)

Test Checks:
  - Dijkstra from A to D returns distance = 2.0 km and path = [A, C, D]
  - If C-D is blocked, Dijkstra automatically reroutes via A -> B -> D (20.0 km)
  - If both routes are blocked, Dijkstra returns float('inf') and flags area stranded.
```

---

## 5. Pseudocode

```text
CLASS TestAlgorithms(TestCase):
    FUNCTION test_dijkstra_skipping_flooded():
        g = Graph()
        g.add_edge(A, B, 2.0)
        g.add_edge(A, C, 5.0)
        g.block_edge(A, B)
        res = dijkstra(g, A)
        ASSERT_EQUAL(res.dist[B], INFINITY)
        ASSERT_EQUAL(res.dist[C], 5.0)
```

---

## 6. Time and Space Complexity

- **Execution Time**: $< 10$ milliseconds for the entire 21-test suite.
- **Memory Footprint**: Minimal transient memory allocated during test runs.

---

## 7. Input and Output Format

- **Input**: Unit test command `python3 -m unittest flood_evacuation_planner/tests/test_algorithms.py`
- **Output**: Terminal report: `Ran 21 tests in 0.004s OK`.

---

## 8. How to Run / Test Individually

```bash
# Run tests directly
python3 flood_evacuation_planner/tests/test_algorithms.py

# Or via unittest discovery:
python3 -m unittest discover -s flood_evacuation_planner/tests
```

---

## 9. Limitations and Possible Improvements

1. **Property-Based Testing**: Incorporate Hypothesis for fuzz testing random directed acyclic graphs and large random topologies ($> 100,000$ edges).
2. **Performance Benchmarking**: Add automated CPU cycle benchmarks comparing scratch-built Min-Heap against theoretical lower bounds.
