# !/usr/bin/env python3
# This is the module for testing the RLEcore.

from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.rle.rlecore import RunLength

from common import *

# Testbanch for the RLEcore module.

"""
This module takes a matrix containing 64 blocks of 12 bits each and verifies
the RLECore produces the same output as the reference data
"""
class TB(Module):
    def __init__(self):
        # Making pipeline and the getting the RLEcore module.
        """
        Streamer : It will pass the input to the RLE core.
                   The data is a 12 bit number in the matrix.

        Logger : It will get the output to the TestBench.
                 Is a 18 bit number.
                 logger[0:12] : Amplitude
                 logger[12:16] : Runlength
        """
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 12)]))
        self.submodules.runlength = RunLength()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 17)]))

        # Connecting TestBench with the RLEcore module.
        self.comb += [
            self.streamer.source.connect(self.runlength.sink),
            self.runlength.source.connect(self.logger.sink)
        ]


def main_generator(dut):

    # Results from the reference modules:
    model = RLE()
    print("The Input Module:")
    print(model.red_pixels_1)
    print("\n")
    print("Expected output:")
    print(model.output_red_pixels_1)

    # Results from the implemented module.
    model2 = RLE()
    packet = Packet(model2.red_pixels_1)
    for i in range(1):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        print("\n")
        print("Output of the RLE module:")
        model2.setdata(dut.logger.packet)

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
