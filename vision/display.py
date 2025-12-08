"""
Display and rendering module for vision application.
Handles visualization of detections, domains, and regions.
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional


def get_color_from_colormap(
    index: int, total: int, colormap=cv2.COLORMAP_HSV
) -> Tuple[int, int, int]:
    """Generate a color from a colormap based on index."""
    if total <= 0:
        total = 1
    # Normalize index to 0-255 range
    value = int((index / max(total, 1)) * 255)
    # Apply colormap
    color_array = cv2.applyColorMap(np.array([[value]], dtype=np.uint8), colormap)
    # Extract BGR tuple
    return tuple(map(int, color_array[0, 0]))


def get_domain_colors(domain_names: list) -> Dict[str, Tuple[int, int, int]]:
    """Generate colors for domains using a colormap."""
    return {
        name: get_color_from_colormap(i, len(domain_names))
        for i, name in enumerate(domain_names)
    }


class Display:

    _last_frame_shape: Optional[Tuple[int, int]] = None

    def __init__(self, window_name: str = "YOLOv8 Webcam - People Detection"):
        self.window_name = window_name
        self.mouse_selection_active = False
        self.selection_start = None
        self.selection_current = None
        self.selection_callback = None
        self.pending_domain_name: Optional[str] = None

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self._mouse_handler)

    def _mouse_handler(self, event, x: int, y: int, flags, param):
        """Internal mouse handler for region selection."""
        # Forward to console first for domain selection
        from console import console

        console.handle_mouse_event(event, x, y, flags, param)

        # Track mouse position for pending domain preview
        if self.pending_domain_name:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.selection_start = (x, y)
                self.selection_current = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE:
                if self.selection_start:
                    self.selection_current = (x, y)
                else:
                    # Show preview even before mouse down
                    self.selection_current = (x, y)

        # Handle interactive region selection if active
        if self.mouse_selection_active:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.selection_start = (x, y)
                self.selection_current = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and self.selection_start:
                self.selection_current = (x, y)
            elif event == cv2.EVENT_LBUTTONUP and self.selection_start:
                self.selection_current = (x, y)
                if self.selection_callback:
                    # Calculate bounding box
                    x1 = min(self.selection_start[0], self.selection_current[0])
                    y1 = min(self.selection_start[1], self.selection_current[1])
                    x2 = max(self.selection_start[0], self.selection_current[0])
                    y2 = max(self.selection_start[1], self.selection_current[1])
                    self.selection_callback((x1, y1, x2, y2))
                self.selection_start = None
                self.selection_current = None

    def start_selection(self, callback):
        """Start interactive region selection mode."""
        self.mouse_selection_active = True
        self.selection_callback = callback
        self.selection_start = None
        self.selection_current = None

    def stop_selection(self):
        """Stop interactive region selection mode."""
        self.mouse_selection_active = False
        self.selection_callback = None
        self.selection_start = None
        self.selection_current = None

    def draw_domain_boundaries(
        self, frame, domains: Dict[str, Tuple[float, float, float, float]]
    ):
        """Draw domain boundaries."""
        h, w = frame.shape[:2]
        domain_colors = get_domain_colors(list(domains.keys()))
        for name, (x1_norm, y1_norm, x2_norm, y2_norm) in domains.items():
            color = domain_colors.get(name, (255, 255, 255))
            # Convert normalized to pixel coordinates
            x1 = int(x1_norm * w)
            x2 = int(x2_norm * w)
            # Draw vertical lines for domain boundaries
            cv2.line(frame, (x1, 0), (x1, h), color, 1)
            cv2.line(frame, (x2, 0), (x2, h), color, 1)

    def draw_detections(
        self, frame, detections, domain_colors: Dict[str, Tuple[int, int, int]]
    ):
        """Draw all detections as markers at center with confidence labels."""
        h, w = frame.shape[:2]
        for det in detections:
            # Get color based on domain
            if det.domain_name and det.domain_name in domain_colors:
                color = domain_colors[det.domain_name]
            else:
                color = (0, 255, 0)

            # Convert normalized coordinates to pixels
            x1 = int(det.x1 * w)
            y1 = int(det.y1 * h)
            x2 = int(det.x2 * w)
            y2 = int(det.y2 * h)

            # Calculate center of bounding box
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Draw marker at center
            marker_size = 15
            cv2.drawMarker(
                frame, (center_x, center_y), color, cv2.MARKER_CROSS, marker_size, 2
            )

            # Draw confidence label below marker
            label = f"{det.confidence:.2f}"
            font_scale = 0.5
            thickness = 1
            label_size, _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )

            # Position label below the marker
            label_x = center_x - label_size[0] // 2
            label_y = center_y + marker_size + label_size[1] + 5

            # Draw label background
            padding = 2
            cv2.rectangle(
                frame,
                (label_x - padding, label_y - label_size[1] - padding),
                (label_x + label_size[0] + padding, label_y + padding),
                color,
                -1,
            )

            # Draw label text
            cv2.putText(
                frame,
                label,
                (label_x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                thickness,
            )

    def draw_detection_box(
        self,
        frame,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        label: str,
        color: Tuple[int, int, int] = (0, 255, 0),
    ):
        """Draw a detection bounding box with label."""
        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Draw label
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

        # Draw label background
        cv2.rectangle(
            frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1
        )

        # Draw label text
        cv2.putText(
            frame,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )

    def draw_domain_boxes(
        self,
        frame,
        domains: Dict[str, Tuple[float, float, float, float]],
        domain_counts: Dict[str, int] = None,
        grayscale: bool = False,
    ):
        """Draw domain bounding boxes with labels including detection counts."""
        h, w = frame.shape[:2]
        # Get domain colors if not in grayscale mode
        domain_colors = get_domain_colors(list(domains.keys())) if not grayscale else {}

        for name, (x1_norm, y1_norm, x2_norm, y2_norm) in domains.copy().items():
            # Convert normalized to pixel coordinates
            x1 = int(x1_norm * w)
            y1 = int(y1_norm * h)
            x2 = int(x2_norm * w)
            y2 = int(y2_norm * h)

            # Use grayscale when user is selecting a new domain
            if grayscale:
                color = (128, 128, 128)  # Gray
                text_color = (180, 180, 180)  # Lighter gray for text
            else:
                # Use unique color for each domain from colormap
                color = domain_colors.get(name, (255, 255, 0))
                # Invert color for text (255 - each component)
                text_color = tuple(255 - c for c in color)

            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Create label with detection count if available
            if domain_counts and name in domain_counts:
                count = domain_counts[name]
                label = f"Domain {name} | {count} detections"
            else:
                label = f"Domain {name}"

            # Draw label inside the box at top left corner with larger font
            font_scale = 0.8
            thickness = 2
            label_size, _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )
            padding = 8

            # Draw label background (same color as box outline)
            cv2.rectangle(
                frame,
                (x1, y1),
                (x1 + label_size[0] + padding * 2, y1 + label_size[1] + padding * 2),
                color,
                -1,
            )

            # Draw label text (inverted color)
            cv2.putText(
                frame,
                label,
                (x1 + padding, y1 + label_size[1] + padding),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                text_color,
                thickness,
            )

    def draw_selection_preview(self, frame):
        """Draw current selection rectangle if in selection mode."""
        # Draw pending domain preview (two-click mode)
        if self.pending_domain_name and self.selection_current:
            if self.selection_start:
                # First anchor placed, show live preview to second point
                x1, y1 = self.selection_start
                x2, y2 = self.selection_current

                # Draw selection rectangle
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

                # Draw anchor point
                cv2.circle(frame, (x1, y1), 5, (0, 255, 255), -1)
                cv2.circle(frame, (x1, y1), 8, (0, 255, 255), 2)

                # Draw dimensions and domain name
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                label = f"{self.pending_domain_name}: {width}x{height}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

                # Draw label background
                min_x, min_y = min(x1, x2), min(y1, y2)
                cv2.rectangle(
                    frame,
                    (min_x, min_y - label_size[1] - 10),
                    (min_x + label_size[0], min_y),
                    (0, 255, 255),
                    -1,
                )

                # Draw label text
                cv2.putText(
                    frame,
                    label,
                    (min_x, min_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2,
                )

                # Draw instruction
                instruction = "Click to place second corner (Right-click to cancel)"
                cv2.putText(
                    frame,
                    instruction,
                    (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                )
            else:
                # Show crosshair at cursor position - waiting for first click
                x, y = self.selection_current
                cv2.drawMarker(frame, (x, y), (0, 255, 255), cv2.MARKER_CROSS, 20, 2)

                # Show domain name near cursor
                label = f"Click to place first corner of '{self.pending_domain_name}'"
                cv2.putText(
                    frame,
                    label,
                    (x + 10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    2,
                )

                # Draw instruction at bottom
                instruction = "Click to place first corner"
                cv2.putText(
                    frame,
                    instruction,
                    (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                )

        # Draw interactive selection preview
        elif (
            self.mouse_selection_active
            and self.selection_start
            and self.selection_current
        ):
            x1, y1 = self.selection_start
            x2, y2 = self.selection_current

            # Draw selection rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

            # Draw dimensions
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            label = f"{width}x{height}"
            cv2.putText(
                frame,
                label,
                (min(x1, x2), min(y1, y2) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                2,
            )

    def render_frame(
        self,
        frame,
        inference_result,
        domains: Dict[str, Tuple[float, float, float, float]],
    ):
        """Render a complete frame with inference results."""
        annotated_frame = frame.copy()

        # Store frame shape for coordinate normalization
        self._last_frame_shape = frame.shape[:2]

        # Check if user is selecting a new domain
        grayscale = self.pending_domain_name is not None

        if inference_result:
            # Get domain colors
            domain_colors = get_domain_colors(list(domains.keys()))

            # Draw detections
            self.draw_detections(
                annotated_frame, inference_result.detections, domain_colors
            )

            # Draw domains with their names and counts (grayscale if selecting)
            self.draw_domain_boxes(
                annotated_frame,
                domains,
                inference_result.domain_counts,
                grayscale=grayscale,
            )
        else:
            # No inference results yet, just draw domains (grayscale if selecting)
            self.draw_domain_boxes(annotated_frame, domains, grayscale=grayscale)

        # Draw selection preview if active
        self.draw_selection_preview(annotated_frame)

        return annotated_frame

    def show(self, frame):
        """Display the frame."""
        cv2.imshow(self.window_name, frame)

    def wait_key(self, delay: int = 1) -> int:
        """Wait for key press."""
        return cv2.waitKey(delay)

    def destroy(self):
        """Clean up the window."""
        cv2.destroyWindow(self.window_name)


# Global display instance
display = Display()
