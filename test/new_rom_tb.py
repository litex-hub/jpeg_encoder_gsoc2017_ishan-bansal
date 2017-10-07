from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *
from litejpeg.core.common import *
from litejpeg.core.huffman.ac_cr_rom import ac_cr_rom
from common import *

class TB(Module):
    def __init__(self):
        self.addr1 = Signal(4)
        self.addr2 = Signal(4)
        self.data = Signal(16)
        self.data_size = Signal(5)
        ac_cr_rom(self,self.addr1,self.addr2,self.data_size,self.data)

def main_generator(dut):
    yield dut.addr2.eq(0)
    yield dut.addr1.eq(0)
    yield
    for i in range(12):
        yield dut.addr2.eq(0)
        yield dut.addr1.eq(i+1)
        yield
        print((yield dut.data),"  ",(yield dut.data_size))
    yield
    print((yield dut.data),"  ",(yield dut.data_size))

if __name__ == "__main__":
    dut = TB()
    clocks = {"sys":10}
    run_simulation(dut, main_generator(dut), clocks, vcd_name="sim.vcd")
