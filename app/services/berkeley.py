import time
from dataclasses import dataclass
from typing import List


@dataclass
class BerkeleyClock:
    """Minimal Berkeley clock helper to keep an offset and compute corrections."""

    offset_ms: float = 0.0
    last_sync_ts: float = 0.0

    def now_ms(self) -> float:
        return (time.time() * 1000) + self.offset_ms

    def sync(self, client_times_ms: List[float]) -> float:
        """Given a list of client times (ms), compute average and update offset."""
        if not client_times_ms:
            self.last_sync_ts = time.time()
            return self.offset_ms

        server_time = time.time() * 1000
        samples = client_times_ms + [server_time]
        average_time = sum(samples) / len(samples)
        # Offset is average - server_time (what we should add to server to align)
        self.offset_ms = average_time - server_time
        self.last_sync_ts = time.time()
        return self.offset_ms
