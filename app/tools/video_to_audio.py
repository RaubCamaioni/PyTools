from contextlib import closing, ExitStack
from pathlib import Path
import av


def video_to_audio(file: Path):
    output_path = file.with_suffix(".mp3")

    with ExitStack() as stack:
        context = closing(av.open(file))
        input_c = stack.enter_context(context)
        input_a = input_c.streams.audio[0]

        context = closing(av.open(output_path, mode="w"))
        output_c = stack.enter_context(context)
        output_a = output_c.add_stream("mp3", rate=input_a.rate)

        for packet in input_c.demux(input_a):
            for frame in packet.decode():
                for packet in output_a.encode(frame):
                    output_c.mux(packet)

    return output_path
