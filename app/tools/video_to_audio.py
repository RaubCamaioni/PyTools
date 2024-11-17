from contextlib import closing
from pathlib import Path
import av


def video_to_audio(video_file: Path) -> Path:
    with closing(av.open(video_file)) as src_c:
        for i, stream in enumerate(src_c.streams.audio):
            output_path = video_file.with_name(video_file.stem + f"_{i}.mp3")
            with closing(av.open(output_path, mode="w")) as dst_c:
                dst_s = dst_c.add_stream("mp3", rate=stream.rate)
                for packet in src_c.demux(stream):
                    for frame in packet.decode():
                        for packet in dst_s.encode(frame):
                            dst_c.mux(packet)

    return output_path
