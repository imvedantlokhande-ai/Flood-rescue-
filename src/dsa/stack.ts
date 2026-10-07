/**
 * Stack Data Structure (LIFO)
 * Built from scratch using linked nodes.
 *
 * Used for:
 * - Depth-First Search (DFS) connected component exploration
 * - Path backtracking and stack-based iterative cycle analysis
 */

export class StackNode<T> {
  public value: T;
  public next: StackNode<T> | null = null;

  constructor(value: T) {
    this.value = value;
  }
}

export class Stack<T> {
  private topNode: StackNode<T> | null = null;
  private length: number = 0;

  /**
   * Push value to top of stack - O(1)
   */
  public push(value: T): void {
    const node = new StackNode(value);
    node.next = this.topNode;
    this.topNode = node;
    this.length++;
  }

  /**
   * Pop top value from stack - O(1)
   */
  public pop(): T | undefined {
    if (!this.topNode) {
      return undefined;
    }
    const val = this.topNode.value;
    this.topNode = this.topNode.next;
    this.length--;
    return val;
  }

  /**
   * Peek top value without popping - O(1)
   */
  public peek(): T | undefined {
    return this.topNode ? this.topNode.value : undefined;
  }

  public isEmpty(): boolean {
    return this.length === 0;
  }

  public size(): number {
    return this.length;
  }

  public toArray(): T[] {
    const items: T[] = [];
    let curr = this.topNode;
    while (curr) {
      items.push(curr.value);
      curr = curr.next;
    }
    return items;
  }

  public clear(): void {
    this.topNode = null;
    this.length = 0;
  }
}
