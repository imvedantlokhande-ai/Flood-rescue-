"""
Custom Min-Heap / Priority Queue Implementation from Scratch.

Strict Rule Compliance:
Implemented manually without `heapq`, `queue.PriorityQueue`, or external libraries.
Supports O(log N) push, O(log N) pop, O(1) peek, and O(log N) decrease_key
using an index position map for fast key lookup.
"""

from typing import Generic, TypeVar, Optional, List, Tuple, Dict, Any

T = TypeVar("T")


class MinHeap(Generic[T]):
    """
    Binary Min-Heap / Priority Queue storing (priority: float, item: T).

    Invariants:
    - For any node at index i:
        * Left child index: 2 * i + 1
        * Right child index: 2 * i + 2
        * Parent index: (i - 1) // 2
    - Heap property: heap[parent].priority <= heap[child].priority

    Time Complexities:
    - push(priority, item): O(log N)
    - pop(): O(log N)
    - peek(): O(1)
    - decrease_key(item, new_priority): O(log N)
    - is_empty(): O(1)
    - size(): O(1)
    """

    def __init__(self) -> None:
        # Array of tuples: [(priority, item), ...]
        self._heap: List[Tuple[float, T]] = []
        # Maps item -> index in self._heap for O(1) lookup during decrease_key
        self._pos_map: Dict[T, int] = {}

    def push(self, priority: float, item: T) -> None:
        """
        Insert an item with given priority into the min-heap.
        If the item already exists and new priority is smaller, update it (decrease_key).
        """
        if item in self._pos_map:
            # If item is already in heap, conditionally decrease key
            curr_idx = self._pos_map[item]
            if priority < self._heap[curr_idx][0]:
                self.decrease_key(item, priority)
            return

        # Add to the end of array and bubble up
        new_idx = len(self._heap)
        self._heap.append((priority, item))
        self._pos_map[item] = new_idx
        self._sift_up(new_idx)

    def pop(self) -> Tuple[float, T]:
        """
        Remove and return the minimum element (lowest priority value).

        Raises:
            IndexError: If pop is called on an empty heap.
        """
        if self.is_empty():
            raise IndexError("pop from an empty MinHeap")

        # Root element holds min priority
        min_elem = self._heap[0]
        last_elem = self._heap.pop()
        del self._pos_map[min_elem[1]]

        if self._heap:
            # Move the last element to the root position and bubble down
            self._heap[0] = last_elem
            self._pos_map[last_elem[1]] = 0
            self._sift_down(0)

        return min_elem

    def peek(self) -> Tuple[float, T]:
        """
        Return the element with minimum priority without removing it.

        Raises:
            IndexError: If peek is called on an empty heap.
        """
        if self.is_empty():
            raise IndexError("peek from an empty MinHeap")
        return self._heap[0]

    def decrease_key(self, item: T, new_priority: float) -> None:
        """
        Decrease the priority value of an existing item in O(log N) time.

        Raises:
            KeyError: If item is not in the heap.
            ValueError: If new_priority is greater than current priority.
        """
        if item not in self._pos_map:
            raise KeyError(f"Item {item} not found in MinHeap")

        idx = self._pos_map[item]
        current_priority = self._heap[idx][0]

        if new_priority > current_priority:
            raise ValueError(
                f"New priority {new_priority} cannot be greater than current priority {current_priority}"
            )

        self._heap[idx] = (new_priority, item)
        self._sift_up(idx)

    def contains(self, item: T) -> bool:
        """Check if an item is currently present in the heap."""
        return item in self._pos_map

    def get_priority(self, item: T) -> Optional[float]:
        """Return the current priority of an item in the heap, or None."""
        if item in self._pos_map:
            return self._heap[self._pos_map[item]][0]
        return None

    def is_empty(self) -> bool:
        """Check if heap contains zero elements."""
        return len(self._heap) == 0

    def size(self) -> int:
        """Return total number of items currently in the heap."""
        return len(self._heap)

    def __len__(self) -> int:
        return len(self._heap)

    def _swap(self, i: int, j: int) -> None:
        """Swap elements at indices i and j and update their position map entries."""
        elem_i = self._heap[i]
        elem_j = self._heap[j]

        self._heap[i] = elem_j
        self._heap[j] = elem_i

        self._pos_map[elem_j[1]] = i
        self._pos_map[elem_i[1]] = j

    def _sift_up(self, idx: int) -> None:
        """Bubble up element at index idx until heap invariant is restored."""
        while idx > 0:
            parent_idx = (idx - 1) // 2
            if self._heap[idx][0] < self._heap[parent_idx][0]:
                self._swap(idx, parent_idx)
                idx = parent_idx
            else:
                break

    def _sift_down(self, idx: int) -> None:
        """Bubble down element at index idx until heap invariant is restored."""
        n = len(self._heap)
        while True:
            smallest = idx
            left_child = 2 * idx + 1
            right_child = 2 * idx + 2

            if left_child < n and self._heap[left_child][0] < self._heap[smallest][0]:
                smallest = left_child

            if right_child < n and self._heap[right_child][0] < self._heap[smallest][0]:
                smallest = right_child

            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break

    def snapshot(self) -> List[Tuple[float, T]]:
        """Return a shallow copy of the internal heap elements for inspection/explain mode."""
        return list(self._heap)

    def __repr__(self) -> str:
        items = [(p, item) for p, item in self._heap]
        return f"MinHeap({items})"


if __name__ == "__main__":
    # Self-test demonstration
    h: MinHeap[str] = MinHeap()
    print("Testing MinHeap:")
    h.push(5.2, "Route A")
    h.push(1.8, "Route B")
    h.push(3.4, "Route C")
    h.push(0.9, "Route D")
    print("Heap contents:", h.snapshot())
    print("Peek min:", h.peek())
    print("Pop min:", h.pop())
    print("Decrease key of Route A to 0.5:")
    h.decrease_key("Route A", 0.5)
    print("Peek after decrease_key:", h.peek())
    print("Popping remaining items in order:")
    while not h.is_empty():
        print(" ->", h.pop())
