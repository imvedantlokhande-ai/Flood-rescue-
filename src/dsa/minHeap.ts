/**
 * Binary Min-Heap Priority Queue
 * Implemented from scratch using a flat 0-indexed array with explicit siftUp and siftDown operations.
 *
 * Strict Compliance:
 * - NO libraries, NO built-in heaps, NO external utilities.
 * - Used for:
 *   1. Dijkstra's shortest path algorithm: minimum distance node extraction in O(log V)
 *   2. Priority dispatching: prioritises stranded rescue regions by -(risk_score * population)
 */

export interface HeapElement<T> {
  key: number; // Priority key (lowest numerical value pops first)
  value: T;    // Payload data (e.g. node_id, location record)
}

export class MinHeap<T> {
  private heap: HeapElement<T>[] = [];

  constructor() {
    this.heap = [];
  }

  /**
   * Insert element with numerical key - O(log N)
   */
  public push(key: number, value: T): void {
    const element: HeapElement<T> = { key, value };
    this.heap.push(element);
    this.siftUp(this.heap.length - 1);
  }

  /**
   * Extract element with lowest key - O(log N)
   */
  public pop(): HeapElement<T> | undefined {
    if (this.heap.length === 0) {
      return undefined;
    }
    if (this.heap.length === 1) {
      return this.heap.pop();
    }

    const min = this.heap[0];
    this.heap[0] = this.heap.pop()!;
    this.siftDown(0);
    return min;
  }

  /**
   * View lowest element without removing - O(1)
   */
  public peek(): HeapElement<T> | undefined {
    return this.heap.length > 0 ? this.heap[0] : undefined;
  }

  public size(): number {
    return this.heap.length;
  }

  public isEmpty(): boolean {
    return this.heap.length === 0;
  }

  public clear(): void {
    this.heap = [];
  }

  public toArray(): HeapElement<T>[] {
    return [...this.heap];
  }

  private siftUp(index: number): void {
    let curr = index;
    while (curr > 0) {
      const parent = Math.floor((curr - 1) / 2);
      if (this.heap[curr].key < this.heap[parent].key) {
        // Swap
        const temp = this.heap[curr];
        this.heap[curr] = this.heap[parent];
        this.heap[parent] = temp;
        curr = parent;
      } else {
        break;
      }
    }
  }

  private siftDown(index: number): void {
    let curr = index;
    const length = this.heap.length;

    while (true) {
      const left = 2 * curr + 1;
      const right = 2 * curr + 2;
      let smallest = curr;

      if (left < length && this.heap[left].key < this.heap[smallest].key) {
        smallest = left;
      }
      if (right < length && this.heap[right].key < this.heap[smallest].key) {
        smallest = right;
      }

      if (smallest !== curr) {
        const temp = this.heap[curr];
        this.heap[curr] = this.heap[smallest];
        this.heap[smallest] = temp;
        curr = smallest;
      } else {
        break;
      }
    }
  }
}
