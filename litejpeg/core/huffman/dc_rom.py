from litex.gen import *
from litex.soc.interconnect.stream import *
from litejpeg.core.common import *

from litejpeg.core.huffman.tablebuilder import build_huffman_rom_tables

#@CEInserter()
def dc_rom(self,address,data_out_size,data_out_code):

    code, size = build_huffman_rom_tables(
    '/home/ishan/gsoc/environment/litejpeg-master/litejpeg/core/huffman/dc_rom.csv')

    rom_code_size = len(code)
    rom_code = [0 for i in range(rom_code_size)]
    rom_code = [int(code[0])]+[int(code[ii+1]) for ii in range(rom_code_size-1)]
    rom_code = tuple(rom_code)

    rom_depth = len(size)
    rom_size = [0 for _ in range(rom_depth)]
    rom_size = [int(size[0])] + [int(size[ii+1]) for ii in range(rom_depth-1)]
    rom_size = tuple(rom_size)

    raddr = Signal(4)

    self.sync += raddr.eq(address)

    data_out_code = rom_code[raddr]
    data_out_size = rom_code[raddr]
