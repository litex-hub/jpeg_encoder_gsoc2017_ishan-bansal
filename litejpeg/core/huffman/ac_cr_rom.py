from litex.gen import *
from litex.soc.interconnect.stream import *
from litejpeg.core.common import *

from litejpeg.core.huffman.tablebuilder import build_huffman_rom_tables


def ac_cr_rom(self,address1,address2,data_out_size,data_out_code):

    HUFFMAN_DIR = os.path.dirname(os.path.abspath(__file__))
    HUFFMAN_CSV = os.path.join(HUFFMAN_DIR, 'ac_cr_rom.csv')
    code, size = build_huffman_rom_tables(HUFFMAN_CSV)

    rom_code_size = len(code)
    for i in range(rom_code_size):
        code[i] = int(code[i],2)
    rom_code = Memory(16, rom_code_size, init=code)
    rom_code_port = rom_code.get_port(async_read=True)
    self.specials += rom_code, rom_code_port


    rom_depth = len(size)
    for i in range(rom_depth):
        size[i] = int(size[i])
    rom_size = Memory(5, rom_depth, init=size)
    rom_size_port = rom_size.get_port(async_read=True)
    self.specials += rom_size, rom_size_port

    address = Signal(len(address1)+len(address2))
    raddr = Signal(len(address1)+len(address2))

    self.sync += raddr.eq(address)

    self.comb += [
        address.eq(Cat(address1,address2)),
        rom_code_port.adr.eq(raddr),
        data_out_code.eq(rom_code_port.dat_r),
        rom_size_port.adr.eq(raddr),
        data_out_size.eq(rom_size_port.dat_r)
    ]
