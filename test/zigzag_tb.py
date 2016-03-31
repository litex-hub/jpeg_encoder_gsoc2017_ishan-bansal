#!/usr/bin/env python3
from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.zigzag import ZigZag, zigzag_order

from common import *

class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 24)]))
        self.submodules.zigzag = ZigZag()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 24)]))

        self.comb += [
            self.streamer.source.connect(self.zigzag.sink),
            self.zigzag.source.connect(self.logger.sink)
        ]


def main_generator(dut):
    packet = Packet(zigzag_order)
    for i in range(4):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        print(dut.logger.packet)

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
