# video

from pathlib import Path
from typing import Literal
import moviepy.editor as mp


def video_to_video(
    input: Path,
    output: Literal["mp4", "avi", "mov", "mkv", ".webm", ".ovg", ".wmv", ".gif"],
):
    output_file = input.with_suffix("." + output)
    clip = mp.VideoFileClip(input)
    clip.write_videofile(output_file)
    return Path(output_file)
