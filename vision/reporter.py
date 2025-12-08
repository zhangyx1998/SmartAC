"""
Reporter module for sending detection statistics to server.
Collects detections over time windows and reports maximum counts per domain.
"""

import threading
import time
import requests
from typing import Dict, Optional
from collections import defaultdict, deque


class Reporter:
    def __init__(self, server_url: str = "", window_seconds: float = 1.0):
        self.server_url = server_url
        self.window_seconds = window_seconds
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Store domain counts with timestamps: [(timestamp, domain_counts_dict), ...]
        self.count_history = deque()
        
    def start(self):
        """Start the reporter thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._reporter_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the reporter thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
    
    def update_counts(self, domain_counts: Dict[str, int]):
        """Add new domain counts observation."""
        with self.lock:
            current_time = time.time()
            self.count_history.append((current_time, domain_counts.copy()))
            
            # Remove old entries outside the time window
            cutoff_time = current_time - self.window_seconds
            while self.count_history and self.count_history[0][0] < cutoff_time:
                self.count_history.popleft()
    
    def _get_max_counts(self) -> Dict[str, int]:
        """Compute maximum counts for each domain in the current time window."""
        with self.lock:
            if not self.count_history:
                return {}
            
            # Track maximum count for each domain
            max_counts = defaultdict(int)
            
            for timestamp, domain_counts in self.count_history:
                for domain_name, count in domain_counts.items():
                    max_counts[domain_name] = max(max_counts[domain_name], count)
            
            return dict(max_counts)
    
    def _reporter_loop(self):
        """Main reporter loop running in separate thread."""
        while self.running:
            # Wait for the window duration
            time.sleep(self.window_seconds)
            
            # Get console server URL
            from console import console
            server_url = console.server_url
            
            if not server_url:
                # No server URL configured, skip reporting
                continue
            
            # Get max counts for the window
            max_counts = self._get_max_counts()
            
            if not max_counts:
                # No data to report
                continue
            
            # Send POST request
            try:
                # Payload is just domain name -> max count key-value pairs
                payload = max_counts
                
                response = requests.post(
                    server_url,
                    json=payload,
                    timeout=2.0
                )
                
                if response.status_code != 200:
                    print(f"Reporter: Server responded with status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Reporter: Failed to send data to server: {e}")
            except Exception as e:
                print(f"Reporter: Error: {e}")


# Global reporter instance
reporter = Reporter()
