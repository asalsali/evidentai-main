from pathlib import Path
import os


def extract_audio_from_video(video_path: str, output_audio_path: str) -> None:
    parent = Path(output_audio_path).parent
    parent.mkdir(parents=True, exist_ok=True)
    # Lazy import with compatibility for MoviePy v2+ and v1.x
    try:
        from moviepy import VideoFileClip as _VideoFileClip  # type: ignore
    except Exception:  # pragma: no cover
        from moviepy.editor import VideoFileClip as _VideoFileClip  # type: ignore
    clip = _VideoFileClip(video_path)
    clip.audio.write_audiofile(output_audio_path, logger=None)
    clip.close()


