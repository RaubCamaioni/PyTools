# video, mute, remove audio, silent, strip sound

from pathlib import Path
from contextlib import ExitStack, closing
import av


def video_mute(video: Path) -> dict:
    """Remove the sound track from a video without re-encoding the picture (fast, no
    quality loss). MP4/MOV/MKV/WEBM in, same container out.
    """
    suffix = video.suffix.lower() if video.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm") else ".mp4"
    out = video.with_name(f"{video.stem}_muted{suffix}")
    with ExitStack() as stack:
        src = stack.enter_context(closing(av.open(str(video))))
        dst = stack.enter_context(closing(av.open(str(out), mode="w")))
        in_v = src.streams.video[0]
        out_v = dst.add_stream_from_template(in_v)
        audio_streams = len(src.streams.audio)
        packets = 0
        for packet in src.demux(in_v):
            if packet.dts is None:
                continue
            packet.stream = out_v
            dst.mux(packet)
            packets += 1
    return {"file": out, "video_packets": packets, "audio_streams_removed": audio_streams}
