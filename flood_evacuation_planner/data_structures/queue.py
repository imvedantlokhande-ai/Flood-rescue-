"""
Custom Queue Implementation using a Singly Linked List with Head and Tail Pointers.

Strict Rule Compliance:
Implemented completely from scratch without using `collections.deque`,
`queue.Queue`, or any standard library queue data structures.
"""

from typing import Generic, TypeVar, Optional, List, Iterator

T = TypeVar("T")


class QueueNode(Generic[T]):
    """Internal node for the custom linked list queue."""

    def __init__(self, value: T, next_node: Optional["QueueNode[T]"] = None) -> None:
        self.value: T = value
        self.next: Optional["QueueNode[T]"] = next_node


class CustomQueue(Generic[T]):
    """
    First-In-First-Out (FIFO) Queue data structure.

    Operations:
    - enqueue(item): O(1) time
    - dequeue(): O(1) time
    - peek(): O(1) time
    - is_empty(): O(1) time
    - size(): O(1) time
    """

    def __init__(self) -> None:
        self._head: Optional[QueueNode[T]] = None
        self._tail: Optional[QueueNode[T]] = None
        self._count: int = 0

    def enqueue(self, item: T) -> None:
        """Add an element to the rear (tail) of the queue in O(1) time."""
        new_node = QueueNode(item)
        if self._tail is None:
            # Queue is currently empty
            self._head = new_node
            self._tail = new_node
        else:
            self._tail.next = new_node
            self._tail = new_node
        self._count += 1

    def dequeue(self) -> T:
        """
        Remove and return the element at the front (head) in O(1) time.

        Raises:
            IndexError: If dequeue is called on an empty queue.
        """
        if self.is_empty():
            raise IndexError("dequeue from an empty queue")

        assert self._head is not None
        removed_value = self._head.value
        self._head = self._head.next
        self._count -= 1

        if self._head is None:
            # Queue became empty
            self._tail = None

        return removed_value

    def peek(self) -> T:
        """
        Return the front element without removing it in O(1) time.

        Raises:
            IndexError: If peek is called on an empty queue.
        """
        if self.is_empty():
            raise IndexError("peek from an empty queue")
        assert self._head is not None
        return self._head.value

    def is_empty(self) -> bool:
        """Check if queue has zero elements."""
        return self._count == 0

    def size(self) -> int:
        """Return the current number of elements in the queue."""
        return self._count

    def __len__(self) -> int:
        return self._count

    def to_list(self) -> List[T]:
        """Convert queue elements from front to rear into a Python list."""
        result: List[T] = []
        curr = self._head
        while curr is not None:
            result.append(curr.value)
            curr = curr.next
        return result

    def __iter__(self) -> Iterator[T]:
        curr = self._head
        while curr is not None:
            yield curr.value
            curr = curr.next

    def __repr__(self) -> str:
        items_str = ", ".join(repr(x) for x in self.to_list())
        return f"CustomQueue([{items_str}])"


if __name__ == "__main__":
    # Self-test demonstration
    q: CustomQueue[str] = CustomQueue()
    print("Testing CustomQueue:")
    q.enqueue("Downtown")
    q.enqueue("West End")
    q.enqueue("North Hills")
    print("Enqueued 3 items:", q.to_list(), "size:", q.size())
    print("Peek front:", q.peek())
    print("Dequeued:", q.dequeue())
    print("Remaining items:", q.to_list(), "is_empty:", q.is_empty())
