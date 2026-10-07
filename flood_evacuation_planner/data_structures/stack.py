"""
Custom Stack Implementation using a Singly Linked List with Top Pointer.

Strict Rule Compliance:
Implemented completely from scratch without using Python's built-in stack
abstractions or list-wrapping convenience. Uses explicit Node pointers.
"""

from typing import Generic, TypeVar, Optional, List, Iterator

T = TypeVar("T")


class StackNode(Generic[T]):
    """Internal node for the custom linked list stack."""

    def __init__(self, value: T, next_node: Optional["StackNode[T]"] = None) -> None:
        self.value: T = value
        self.next: Optional["StackNode[T]"] = next_node


class CustomStack(Generic[T]):
    """
    Last-In-First-Out (LIFO) Stack data structure.

    Operations:
    - push(item): O(1) time
    - pop(): O(1) time
    - peek(): O(1) time
    - is_empty(): O(1) time
    - size(): O(1) time
    """

    def __init__(self) -> None:
        self._top: Optional[StackNode[T]] = None
        self._count: int = 0

    def push(self, item: T) -> None:
        """Push an element onto the top of the stack in O(1) time."""
        new_node = StackNode(item, next_node=self._top)
        self._top = new_node
        self._count += 1

    def pop(self) -> T:
        """
        Remove and return the element at the top in O(1) time.

        Raises:
            IndexError: If pop is called on an empty stack.
        """
        if self.is_empty():
            raise IndexError("pop from an empty stack")

        assert self._top is not None
        removed_value = self._top.value
        self._top = self._top.next
        self._count -= 1
        return removed_value

    def peek(self) -> T:
        """
        Return the top element without removing it in O(1) time.

        Raises:
            IndexError: If peek is called on an empty stack.
        """
        if self.is_empty():
            raise IndexError("peek from an empty stack")
        assert self._top is not None
        return self._top.value

    def is_empty(self) -> bool:
        """Check if stack has zero elements."""
        return self._count == 0

    def size(self) -> int:
        """Return the current count of elements on the stack."""
        return self._count

    def __len__(self) -> int:
        return self._count

    def to_list(self) -> List[T]:
        """Convert stack elements from top to bottom into a list."""
        result: List[T] = []
        curr = self._top
        while curr is not None:
            result.append(curr.value)
            curr = curr.next
        return result

    def __iter__(self) -> Iterator[T]:
        curr = self._top
        while curr is not None:
            yield curr.value
            curr = curr.next

    def __repr__(self) -> str:
        items_str = ", ".join(repr(x) for x in self.to_list())
        return f"CustomStack(top -> [{items_str}])"


if __name__ == "__main__":
    # Self-test demonstration
    s: CustomStack[str] = CustomStack()
    print("Testing CustomStack:")
    s.push("Downtown")
    s.push("Central Market")
    s.push("Riverside")
    print("Pushed 3 items (top to bottom):", s.to_list(), "size:", s.size())
    print("Peek top:", s.peek())
    print("Popped:", s.pop())
    print("Remaining items:", s.to_list(), "is_empty:", s.is_empty())
