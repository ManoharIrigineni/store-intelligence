import cv2
import numpy as np
import os

os.makedirs("/workspace/data", exist_ok=True)
output_path = "/workspace/data/floor_sample.mp4"

# Create a black video frame layout (1280x720 widescreen resolution)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, 30.0, (1280, 720))

print("Creating sample test video file...")
for i in range(90): # 90 frames at 30 fps = 3 seconds of footage
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Draw a simulated visual tracking target on the frame layout
    cv2.putText(frame, f"Simulated Shopper Frame {i}", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    out.write(frame)

out.release()
print(f"Successfully generated mock video file at: {output_path}")