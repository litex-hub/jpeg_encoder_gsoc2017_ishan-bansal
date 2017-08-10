# !/usr/bin/env python3
from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.zigzag import ZigZag, zigzag_order
from common import ZZData

from common import *

# Testbench for the zigzag module.
# Comparing the result of the implemented zigzag module with the
# one of the reference module to check the accuracy of the
# implemented module.


class TB(Module):
    def __init__(self):
        # Making Pipeline and getting the zigzag module.
        self.submodules.streamer = PacketStreamer(
                                       EndpointDescription([("data", 12)]))
        self.submodules.zigzag = ZigZag()
        self.submodules.logger = PacketLogger(
                                     EndpointDescription([("data", 12)]))

        # Connecting the zigzag module with the test bench.
        self.comb += [
            self.streamer.source.connect(self.zigzag.sink),
            self.zigzag.source.connect(self.logger.sink)
        ]


def main_generator(dut):
    # Result from the reference module.
    model = ZZData()
    print("The Input Module:")
    print(model.zigzag_input)
    print("\n")
    print("Output of the Reference Module taken:")
    print(model.zigzag_output)
    print("\n")

    # Result from the implemented module.
    packet = Packet(model.zigzag_input)
    for i in range(1):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        print("Output of the Zigzag Module Implemented:")
        print(dut.logger.packet)


# Getting into the main module.
if __name__ == "__main__":
    tb = TB()
    generators = {"sys": [main_generator(tb)]}
    generators = {
        "sys":   [main_generator(tb),
                  tb.streamer.generator(),
                  tb.logger.generator()]
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
