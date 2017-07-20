from litex.gen import *
from litex.soc.interconnect.stream import *
from litejpeg.core.common import *

from litejpeg.core.huffman.tablebuilder import build_huffman_rom_tables


def dc_rom(self,address,data_out_size,data_out_code):

    code, size = build_huffman_rom_tables(
    '/home/ishan/gsoc/environment/litejpeg-master/litejpeg/core/huffman/dc_rom.csv')

    rom_code_size = len(code)
    rom_code = Array(Signal(16) for i in range(rom_code_size))
    self.sync += [(rom_code[i].eq(code[i])) for i in range(rom_code_size)]

    rom_depth = len(size)
    rom_size = Array(Signal(4) for i in range(rom_depth))
    self.sync += [(rom_size[i].eq(size[i])) for i in range(rom_depth)]

    raddr = Signal(4)

    self.sync += raddr.eq(address)

    self.comb += [
    data_out_code.eq(rom_code[raddr]),
    data_out_size.eq(rom_code[raddr])
    ]
