from contextlib import closing, ExitStack
from pathlib import Path
import av


def video_to_audio(video_file: Path) -> Path:
    output_path = video_file.with_suffix(".mp3")

    with ExitStack() as stack:
        context_a = closing(av.open(video_file))
        input_c = stack.enter_context(context_a)
        input_a = input_c.streams.audio[0]

        context_b = closing(av.open(output_path, mode="w"))
        output_c = stack.enter_context(context_b)
        output_a = output_c.add_stream("mp3", rate=input_a.rate)

        for packet in input_c.demux(input_a):
            for frame in packet.decode():
                for packet in output_a.encode(frame):
                    output_c.mux(packet)

    return output_path
