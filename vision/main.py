# Run YOLO over Webcam
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description="YOLO Webcam People Detection")
parser.add_argument("--camera", type=int, help="Camera index (skips camera selection)")
parser.add_argument("--domains", type=str, help="Path to domains file (JSON or YAML)")
parser.add_argument("--server", type=str, help="Server URL")
args = parser.parse_args()

import cv2
from console import console, log
from camera import select_camera, Camera
from display import display
from inference import inference_engine
from reporter import reporter

# Set server URL if provided
if args.server:
    console.server_url = args.server
    print(f"Server URL set to: {args.server}")

# Load domains if provided
if args.domains:
    console._domain_load(args.domains)

# Read frame from webcam and perform inference
if args.camera is not None:
    # Use specified camera index
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Error: Could not open camera {args.camera}")
        exit(1)
    print(f"Using camera {args.camera}")
else:
    # Interactive camera selection
    cap = select_camera()
    if cap is None:
        print("Exiting...")
        exit(0)

print(f"\nStarting video capture from camera {cap}...")
camera = Camera(cap)
camera.start()

# Start console thread
console.start()

# Start inference engine
inference_engine.start()

# Start reporter thread
reporter.start()


try:
    while True:
        # Get latest frame from camera
        frame = camera.get_frame()
        if frame is None:
            continue

        # Send frame to inference engine
        inference_engine.update_frame(frame)

        # Get latest inference result
        inference_result = inference_engine.get_result()

        # Update reporter with domain counts if available
        if inference_result:
            reporter.update_counts(inference_result.domain_counts)

        # Render frame with inference results
        annotated_frame = display.render_frame(frame, inference_result, console.domains)

        # Show frame
        display.show(annotated_frame)

        if display.wait_key(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    pass
finally:
    console.stop()
    inference_engine.stop()
    reporter.stop()
    camera.stop()
    display.destroy()
