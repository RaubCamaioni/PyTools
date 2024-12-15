from typing import Literal
from pathlib import Path
from contextlib import closing, ExitStack
import av
import av.stream


def audio_to_audio(input: Path, output: Literal["wav", "aac", "mp3", "mp2"]):
    output_file = input.with_suffix("." + output)
    output = "pcm_s16le" if output == "wav" else output

    with ExitStack() as stack:
        src_c = stack.enter_context(closing(av.open(input)))
        dst_c = stack.enter_context(av.open(output_file, mode="w"))

        for src_s in src_c.streams.audio:
            dst_s = dst_c.add_stream(output, rate=src_s.rate)
            for packet in src_c.demux(src_s):
                for frame in packet.decode():
                    for packet in dst_s.encode(frame):
                        dst_c.mux(packet)

    return output_file
