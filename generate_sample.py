"""
generate_sample.py — Synthetic Test Video Generator
Creates a 3-second color-gradient sample video (sample_input.mp4)
for automated testing without needing a real video file.
"""

import numpy as np
from moviepy import ImageClip, concatenate_videoclips


def make_color_frame(color_rgb: tuple, width: int = 640, height: int = 360) -> np.ndarray:
    """Create a solid-color numpy frame."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = color_rgb
    return frame


def generate_gradient_frame(t: float, width: int = 640, height: int = 360) -> np.ndarray:
    """Generate a frame with a sweeping color gradient based on time t."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Horizontal gradient that shifts color over time
    for x in range(width):
        ratio = x / width
        r = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * (ratio + t * 0.3))))
        g = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * (ratio + t * 0.3 + 0.33))))
        b = int(255 * (0.5 + 0.5 * np.sin(2 * np.pi * (ratio + t * 0.3 + 0.66))))
        frame[:, x] = [r, g, b]
    return frame


def main():
    print("🎨 Generating synthetic sample video...")

    duration = 3.0  # seconds
    fps = 24
    output_path = "sample_input.mp4"

    # Build 3 one-second solid-color clips
    colors = [
        (79, 70, 229),    # Indigo (accent color)
        (63, 185, 80),    # Green
        (88, 166, 255),   # Blue
    ]

    clips = []
    for i, color in enumerate(colors):
        frame = make_color_frame(color)
        clip = ImageClip(frame, duration=1.0).with_fps(fps)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="chain")
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        threads=4,
        logger=None,
    )

    for c in clips:
        c.close()
    final.close()

    from pathlib import Path
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"✅ Sample video created: {output_path}")
    print(f"   Duration : {duration}s")
    print(f"   FPS      : {fps}")
    print(f"   Resolution: 640×360")
    print(f"   File size : {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
