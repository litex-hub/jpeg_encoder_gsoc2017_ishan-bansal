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


    def gen_simulation(self, selfp):
        packet = Packet(zigzag_order)
        for i in range(4):
            self.streamer.send(packet)
            yield from self.logger.receive()
            print(self.logger.packet)

if __name__ == "__main__":
    from litex.gen.sim.generic import run_simulation
    run_simulation(TB(), ncycles=8192, vcd_name="my.vcd", keep_files=True)
