from agents import function_tool
from pydantic import BaseModel, Field
from typing import List
import cv2
import os


class FrameExtractionArgs(BaseModel):
    video_path: str = Field(description="Absolute or project-relative path to the video file")
    sample_rate_fps: int = Field(default=1, description="Frames per second to sample for analysis")
    output_dir: str = Field(description="Directory to save sampled frames")


# @function_tool
def extract_frames(args: FrameExtractionArgs) -> List[str]:
    """Sample frames from a video and save as images. Returns list of image paths."""
    video_path = args.video_path
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = max(int(fps // max(args.sample_rate_fps, 1)), 1)

    saved = []
    index = 0
    saved_index = 0
    while True:
        ret, frame = capture.read()
        if not ret:
            break
        if index % frame_interval == 0:
            out_path = os.path.join(output_dir, f"frame_{saved_index:06d}.jpg")
            cv2.imwrite(out_path, frame)
            saved.append(out_path)
            saved_index += 1
        index += 1
    capture.release()
    return saved


