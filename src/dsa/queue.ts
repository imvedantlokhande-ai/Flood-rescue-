/**
 * Queue Data Structure (FIFO)
 * Built from scratch with doubly-linked nodes.
 *
 * Used for:
 * - Breadth-First Search (BFS) graph reachability analysis
 * - Measuring unweighted hop distance from start location to safe shelters
 */

export class QueueNode<T> {
  public value: T;
  public next: QueueNode<T> | null = null;
  public prev: QueueNode<T> | null = null;

  constructor(value: T) {
    this.value = value;
  }
}

export class Queue<T> {
  private head: QueueNode<T> | null = null;
  private tail: QueueNode<T> | null = null;
  private length: number = 0;

  /**
   * Enqueue item at tail - O(1) time
   */
  public enqueue(value: T): void {
    const node = new QueueNode(value);
    if (!this.tail) {
      this.head = node;
      this.tail = node;
    } else {
      this.tail.next = node;
      node.prev = this.tail;
      this.tail = node;
    }
    this.length++;
  }

  /**
   * Dequeue item from head - O(1) time
   */
  public dequeue(): T | undefined {
    if (!this.head) {
      return undefined;
    }
    const val = this.head.value;
    this.head = this.head.next;
    if (this.head) {
      this.head.prev = null;
    } else {
      this.tail = null;
    }
    this.length--;
    return val;
  }

  /**
   * Peek front element without removing - O(1) time
   */
  public peek(): T | undefined {
    return this.head ? this.head.value : undefined;
  }

  public isEmpty(): boolean {
    return this.length === 0;
  }

  public size(): number {
    return this.length;
  }

  public toArray(): T[] {
    const items: T[] = [];
    let curr = this.head;
    while (curr) {
      items.push(curr.value);
      curr = curr.next;
    }
    return items;
  }

  public clear(): void {
    this.head = null;
    this.tail = null;
    this.length = 0;
  }
}
