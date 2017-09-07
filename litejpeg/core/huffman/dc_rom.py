from litex.gen import *
from litex.soc.interconnect.stream import *
from litejpeg.core.common import *

from litejpeg.core.huffman.tablebuilder import build_huffman_rom_tables

class dc_rom_core(Module):
    def __init__ (self):
        self.address = Signal(4)
        self.data_out_size = Signal(4)
        self.data_out_code = Signal(16)
        code, size = build_huffman_rom_tables(
        '/home/ishan/gsoc/environment/litejpeg-master/litejpeg/core/huffman/dc_rom.csv')

        rom_code_size = len(code)
        for i in range(rom_code_size):
            code[i] = int(code[i])
        rom_code = Memory(16, rom_code_size, init=code)
        rom_code_port = rom_code.get_port(async_read=True)
        self.specials += rom_code, rom_code_port

        rom_depth = len(size)
        for i in range(rom_depth):
            size[i] = int(size[i])
        rom_size = Memory(4, rom_depth, init=size)
        rom_size_port = rom_size.get_port(async_read=True)
        self.specials += rom_size, rom_size_port

        raddr = Signal(4)

        self.sync += raddr.eq(self.address)
        self.comb += [
        rom_code_port.adr.eq(raddr),
        self.data_out_code.eq(rom_code_port.dat_r),
        rom_size_port.adr.eq(raddr),
        self.data_out_size.eq(rom_size_port.dat_r)
        ]