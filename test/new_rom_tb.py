from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.huffman.dc_rom import dc_rom

from common import *

class TB(Module):
    def __init__(self):
        self.addr = Signal(4)
        self.data = Signal(16)
        self.data_size = Signal(4)
        self.submodules.dc_rom = dc_rom(self,self.addr,self.data,self.data_size)
        


def main_generator(dut):
    yield dut.addr.eq(4)


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
