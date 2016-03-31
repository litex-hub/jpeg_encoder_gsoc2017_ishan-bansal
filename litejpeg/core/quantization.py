# Quantization

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *


class Quantization(PipelinedActor, Module, AutoCSR):
    def __init__(self, init):
        self.sink = stream.Endpoint(block_layout(12))
        self.source = stream.Endpoint(block_layout(12))
        PipelinedActor.__init__(self, 3)

        self._we = CSR()
        self._addr = CSRStorage(6)
        self._data = CSRStorage(12)

        # # #

        mem = Memory(12, 2**6, init=init)
        write_port = mem.get_port(write_capable=True)
        read_port = mem.get_port(has_re=True)
        self.specials += mem, write_port, read_port

        self.comb += [
            write_port.adr.eq(self._addr.storage),
            write_port.dat_w.eq(self._data.storage),
            write_port.we.eq(self._we.re & self._we.r)
        ]

        self.comb += [
            read_port.adr.eq(sink.data[:dw_from//2]),
            read_port.re.eq(self.pipe_ce),
        ]
        data = Signal(24)
        self.sync += \
            If(self.pipe_ce,
                value.eq(sink.data * read_port.dat_r)
                source.data.eq(data[12:])
            )
        ]
