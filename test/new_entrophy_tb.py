# This is the module for testing the Entrophycoder.

# !/usr/bin/env python3
from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.rle.entrophycoder import Entrophycoder

from common import *

class TB(Module):
    def __init__(self):
        # Making pipeline and the getting the Entrophycoder module.
        """
        Streamer : It will pass the input to the entrophycoder.
                   The data is a 12 bit number in the matrix.

        Logger : It will get the output to the TestBench.
                 Is a 4 bit number.
        """
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 12)]))
        self.submodules.entrophycoder = Entrophycoder()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 4)]))

        # Connecting TestBench with the Entrophycoder module.
        self.comb += [
            self.streamer.source.connect(self.entrophycoder.sink),
            self.entrophycoder.source.connect(self.logger.sink)
        ]


def main_generator(dut):

    # Results from the reference modules:
    model = RLE()
    print("The Input Module:")
    print(model.red_pixels_1)

    # Results from the implemented module.
    model2 = RLE()
    packet = Packet(model2.red_pixels_1)
    for i in range(1):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        print("\n")
        print("Output of the Entrophycoder module:")
        print(dut.logger.packet)

# Going through the main module
if __name__ == "__main__":
    tb = TB()
    generators = {"sys" : [main_generator(tb)]}
    generators = {
        "sys" :   [main_generator(tb),
                   tb.streamer.generator(),
                   tb.logger.generator()]
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
