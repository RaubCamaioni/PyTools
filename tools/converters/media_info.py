# video, audio, metadata, info, codec, inspect

from pathlib import Path
from contextlib import closing
import av


def media_info(media: Path) -> dict:
    """Show the container, duration, bit rate, codecs, resolution, frame rate, audio channels and metadata tags of a video or audio file."""
    with closing(av.open(str(media))) as c:
        duration = c.duration / av.time_base if c.duration else None
        info = {
            "file": media.name,
            "file_size_bytes": media.stat().st_size,
            "container": c.format.long_name,
            "duration_seconds": round(duration, 3) if duration else None,
            "duration": f"{int(duration // 3600):02d}:{int(duration % 3600 // 60):02d}:{duration % 60:06.3f}" if duration else None,
            "bit_rate_kbps": round(c.bit_rate / 1000) if c.bit_rate else None,
            "metadata": dict(c.metadata) or "none",
            "streams": [],
        }
        for s in c.streams:
            entry = {"index": s.index, "type": s.type, "codec": s.codec_context.name if s.codec_context else None}
            if s.type == "video":
                entry.update({
                    "width": s.codec_context.width,
                    "height": s.codec_context.height,
                    "frame_rate": float(s.average_rate) if s.average_rate else None,
                    "pixel_format": s.codec_context.pix_fmt,
                    "frames": s.frames or None,
                })
            elif s.type == "audio":
                entry.update({
                    "sample_rate_hz": s.codec_context.sample_rate,
                    "channels": s.codec_context.channels,
                    "layout": s.codec_context.layout.name if s.codec_context.layout else None,
                    "sample_format": s.codec_context.format.name if s.codec_context.format else None,
                })
            if s.metadata:
                entry["metadata"] = dict(s.metadata)
            info["streams"].append(entry)
    return info
