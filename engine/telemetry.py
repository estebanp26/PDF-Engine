import time
from typing import Dict, Any

class SpeedProfiler:
    """High-resolution profiler for measuring engine execution times."""
    def __init__(self):
        self.start_time = time.perf_counter()
        self.timings: Dict[str, float] = {}
        self._current_lap = None

    def start_lap(self, name: str):
        self.timings[f"_start_{name}"] = time.perf_counter()

    def end_lap(self, name: str) -> float:
        start_key = f"_start_{name}"
        if start_key in self.timings:
            elapsed = time.perf_counter() - self.timings.pop(start_key)
            self.timings[name] = round(elapsed, 4)
            return elapsed
        return 0.0

    def total_elapsed(self) -> float:
        return round(time.perf_counter() - self.start_time, 4)

    def summary(self, total_pages: int = 0) -> Dict[str, Any]:
        total = self.total_elapsed()
        pages_per_sec = round(total_pages / total, 2) if total > 0 and total_pages > 0 else 0.0
        return {
            "total_seconds": total,
            "total_ms": round(total * 1000, 1),
            "pages_processed": total_pages,
            "pages_per_second": pages_per_sec,
            "breakdown": {k: v for k, v in self.timings.items() if not k.startswith("_")}
        }
