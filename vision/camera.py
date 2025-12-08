"""
Camera selection and management module.
"""

import cv2
import threading
import time


def get_available_cameras(max_cameras=10):
    """Detect available cameras on the system."""
    available_cameras = []
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                # Try to get camera name/backend info
                backend = cap.getBackendName()
                available_cameras.append((i, backend))
            cap.release()
    return available_cameras


def select_camera():
    """Prompt user to select a camera from available options."""
    cameras = get_available_cameras()

    if not cameras:
        print("No cameras detected!")
        return None

    print("\nAvailable cameras:")
    for idx, backend in cameras:
        # Create a meaningful name
        if idx == 0:
            name = "Built-in/Default Camera"
        else:
            name = f"External Camera {idx}"
        print(f"  [{idx}] {name} ({backend})")

    camera_ids = [cam[0] for cam in cameras]

    while True:
        try:
            choice = input(f"\nSelect camera (0-{max(camera_ids)}): ").strip()
            camera_id = int(choice)
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                print(f"Camera {camera_id} could not be opened. Please choose another.")
                cap.release()
                continue
            return cap
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nCamera selection cancelled.")
            return None


class Camera:
    """Camera frame capture running in background thread."""

    def __init__(self, cap: cv2.VideoCapture):
        self.cap = cap
        self.latest_frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {cap}")

    def start(self):
        """Start capturing frames in background thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop capturing frames."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

    def get_frame(self):
        """Get the latest frame."""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.01)
