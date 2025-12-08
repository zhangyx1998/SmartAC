"""
Inference module for running YOLO detection.
Runs in a separate thread to avoid blocking display.
"""

import threading
import time
from typing import Dict, Tuple, List, Optional
from ultralytics import YOLO
from dataclasses import dataclass


@dataclass
class Detection:
    """Represents a single detection with normalized coordinates (0.0-1.0)."""

    x1: float  # Normalized x1 coordinate (0.0-1.0)
    y1: float  # Normalized y1 coordinate (0.0-1.0)
    x2: float  # Normalized x2 coordinate (0.0-1.0)
    y2: float  # Normalized y2 coordinate (0.0-1.0)
    confidence: float
    class_name: str
    domain_name: Optional[str] = None


@dataclass
class InferenceResult:
    """Results from inference on a frame."""

    detections: List[Detection]
    domain_counts: Dict[str, int]
    timestamp: float


class InferenceEngine:
    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = YOLO(model_path)
        self.latest_frame = None
        self.latest_result = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.frame_lock = threading.Lock()

    def start(self):
        """Start the inference thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._inference_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the inference thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def update_frame(self, frame):
        """Update the frame to be processed."""
        with self.frame_lock:
            self.latest_frame = frame.copy()

    def get_result(self) -> Optional[InferenceResult]:
        """Get the latest inference result."""
        with self.lock:
            return self.latest_result

    def _inference_loop(self):
        """Main inference loop running in separate thread."""
        while self.running:
            # Get latest frame
            with self.frame_lock:
                frame = self.latest_frame

            if frame is None:
                time.sleep(0.01)
                continue

            # Get domains from console
            from console import console

            domains = dict(console.domains)

            # Run inference
            result = self._run_inference(frame, domains)

            # Store result
            with self.lock:
                self.latest_result = result

            # Small sleep to avoid hogging CPU
            time.sleep(0.01)

    def _run_inference(
        self, frame, domains: Dict[str, Tuple[float, float, float, float]]
    ) -> InferenceResult:
        """Run inference on frame with given domains (normalized coordinates 0.0-1.0)."""
        h, w = frame.shape[:2]
        detections = []
        domain_counts = {}

        if domains:
            # Process each domain independently
            for domain_name, (x1_norm, y1_norm, x2_norm, y2_norm) in domains.items():
                # Convert normalized coordinates to pixels
                x1 = int(x1_norm * w)
                y1 = int(y1_norm * h)
                x2 = int(x2_norm * w)
                y2 = int(y2_norm * h)

                # Ensure coordinates are within frame bounds
                x1_clip = max(0, min(x1, w))
                y1_clip = max(0, min(y1, h))
                x2_clip = max(0, min(x2, w))
                y2_clip = max(0, min(y2, h))

                # Skip if domain is invalid
                if x2_clip <= x1_clip or y2_clip <= y1_clip:
                    domain_counts[domain_name] = 0
                    continue

                # Slice the frame for this domain
                domain_frame = frame[y1_clip:y2_clip, x1_clip:x2_clip]

                # Run YOLO on the sliced frame
                domain_results = self.model(domain_frame, verbose=False)

                # Count people in this domain
                person_count = 0
                if domain_results[0].boxes is not None:
                    for box in domain_results[0].boxes:
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]

                        if class_name.lower() == "person":
                            person_count += 1

                            # Get bounding box coordinates (relative to domain)
                            dx1, dy1, dx2, dy2 = map(int, box.xyxy[0])

                            # Convert to absolute frame coordinates (pixels)
                            abs_x1 = x1_clip + dx1
                            abs_y1 = y1_clip + dy1
                            abs_x2 = x1_clip + dx2
                            abs_y2 = y1_clip + dy2

                            # Convert to normalized coordinates
                            norm_x1 = abs_x1 / w
                            norm_y1 = abs_y1 / h
                            norm_x2 = abs_x2 / w
                            norm_y2 = abs_y2 / h

                            # Get confidence score
                            confidence = float(box.conf[0])

                            detections.append(
                                Detection(
                                    x1=norm_x1,
                                    y1=norm_y1,
                                    x2=norm_x2,
                                    y2=norm_y2,
                                    confidence=confidence,
                                    class_name=class_name,
                                    domain_name=domain_name,
                                )
                            )

                domain_counts[domain_name] = person_count
        else:
            # Run detection on full frame
            results = self.model(frame, verbose=False)

            # Filter and categorize detections
            if results[0].boxes is not None:
                for box in results[0].boxes:
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]

                    if class_name.lower() == "person":
                        # Get bounding box coordinates (pixels)
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        # Convert to normalized coordinates
                        norm_x1 = x1 / w
                        norm_y1 = y1 / h
                        norm_x2 = x2 / w
                        norm_y2 = y2 / h

                        confidence = float(box.conf[0])

                        detections.append(
                            Detection(
                                x1=norm_x1,
                                y1=norm_y1,
                                x2=norm_x2,
                                y2=norm_y2,
                                confidence=confidence,
                                class_name=class_name,
                            )
                        )

        return InferenceResult(
            detections=detections, domain_counts=domain_counts, timestamp=time.time()
        )


# Global inference engine
inference_engine = InferenceEngine()
