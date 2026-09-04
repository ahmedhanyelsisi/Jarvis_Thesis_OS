import threading
import heapq
from typing import Optional
from .models import BuildTask

class BuildQueue:
    """Thread-safe priority queue prioritizing strict synchronization without execution loops."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._queue = []
        
    def enqueue(self, task: BuildTask) -> None:
        """Add an immutable task to the priority queue."""
        with self._lock:
            heapq.heappush(self._queue, task)
            
    def dequeue(self) -> Optional[BuildTask]:
        """Atomically pop the highest priority (or oldest) task."""
        with self._lock:
            if not self._queue:
                return None
            return heapq.heappop(self._queue)
            
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0
            
    def size(self) -> int:
        with self._lock:
            return len(self._queue)
