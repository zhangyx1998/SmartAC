# Run YOLO over Webcam
from dataclasses import dataclass
from ultralytics import YOLO
import cv2

# Load a model
model = YOLO("yolov8n.pt")


def clamp(v, v0, v1):
    return max(v0, min(v, v1))


@dataclass
class Region:
    x: float
    y: float
    width: float
    height: float

    def __call__(self, w: int, h: int):
        x = clamp(self.x * w, 0.0, 1.0)
        y = clamp(self.y * h, 0.0, 1.0)
        width = clamp(self.width, 0.0, 1.0 - x)
        height = clamp(self.height, 0.0, 1.0 - y)
        return (
            int(round(x * w)),
            int(round(y * h)),
            int(round(width * w)),
            int(round(height * h)),
        )


L = Region(0.0, 0.0, 0.33, 1.0)  # Left
C = Region(0.33, 0.0, 0.33, 1.0)  # Center
R = Region(0.66, 0.0, 0.33, 1.0)  # Right

# Region colors (BGR format for OpenCV)
REGION_COLORS = {
    "L": (0, 0, 255),  # Red for Left
    "C": (0, 255, 0),  # Green for Center
    "R": (255, 0, 0),  # Blue for Right
}


def get_region(x_center, y_center, frame_width, frame_height):
    """Determine which region a detection belongs to based on its center point."""
    # Normalize coordinates
    x_norm = x_center / frame_width

    if x_norm < 0.33:
        return "L"
    elif x_norm < 0.66:
        return "C"
    else:
        return "R"


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
            if camera_id in camera_ids:
                return camera_id
            else:
                print(
                    f"Camera {camera_id} is not available. Please choose from: {camera_ids}"
                )
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nCamera selection cancelled.")
            return None


# Read frame from webcam and perform inference
camera_id = select_camera()
if camera_id is None:
    print("Exiting...")
    exit(0)

print(f"\nStarting video capture from camera {camera_id}...")
cap = cv2.VideoCapture(camera_id)


try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]

        # Perform inference
        results = model(frame)

        # Create a copy of the frame for manual annotation
        annotated_frame = frame.copy()

        # Draw region boundaries (optional, for visualization)
        cv2.line(
            annotated_frame, (int(w * 0.33), 0), (int(w * 0.33), h), (255, 255, 255), 1
        )
        cv2.line(
            annotated_frame, (int(w * 0.66), 0), (int(w * 0.66), h), (255, 255, 255), 1
        )

        # Initialize counters for each region
        region_counts = {"L": 0, "C": 0, "R": 0}

        # Filter and categorize detections
        if results[0].boxes is not None:
            for box in results[0].boxes:
                # Get class ID and name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]

                # Filter for "person" class (class ID 0 in COCO dataset)
                if class_name.lower() == "person":
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # Calculate center point
                    x_center = (x1 + x2) / 2
                    y_center = (y1 + y2) / 2

                    # Determine region
                    region = get_region(x_center, y_center, w, h)
                    color = REGION_COLORS[region]

                    # Increment region counter
                    region_counts[region] += 1

                    # Get confidence score
                    confidence = float(box.conf[0])

                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

                    # Draw label with region and confidence
                    label = f"Person [{region}] {confidence:.2f}"
                    label_size, _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                    )

                    # Draw label background
                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1 - label_size[1] - 10),
                        (x1 + label_size[0], y1),
                        color,
                        -1,
                    )

                    # Draw label text
                    cv2.putText(
                        annotated_frame,
                        label,
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

        # Draw large region count numbers at the top of each region
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 3
        thickness = 5

        # Left region count
        text = str(region_counts["L"])
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        x_pos = int(w * 0.165) - text_size[0] // 2  # Center of left region
        y_pos = 80
        cv2.putText(
            annotated_frame,
            text,
            (x_pos, y_pos),
            font,
            font_scale,
            REGION_COLORS["L"],
            thickness,
        )

        # Center region count
        text = str(region_counts["C"])
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        x_pos = int(w * 0.495) - text_size[0] // 2  # Center of center region
        cv2.putText(
            annotated_frame,
            text,
            (x_pos, y_pos),
            font,
            font_scale,
            REGION_COLORS["C"],
            thickness,
        )

        # Right region count
        text = str(region_counts["R"])
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        x_pos = int(w * 0.83) - text_size[0] // 2  # Center of right region
        cv2.putText(
            annotated_frame,
            text,
            (x_pos, y_pos),
            font,
            font_scale,
            REGION_COLORS["R"],
            thickness,
        )

        cv2.imshow("YOLOv8 Webcam - People Detection", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    pass
finally:
    cv2.destroyAllWindows()
    cap.release()
