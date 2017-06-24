# ZigZag

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

zigzag_order = [
 0,  1,  5,  6, 14, 15, 27, 28,
 2,  4,  7, 13, 16, 26, 29, 42,
 3,  8, 12, 17, 25, 30, 41, 43,
 9, 11, 18, 24, 31, 40, 44, 53,
10, 19, 23, 32, 39, 45, 52, 54,
20, 22, 33, 38, 46, 51, 55, 60,
21, 34, 37, 47, 50, 56, 59, 61,
35, 36, 48, 49, 57, 58, 62, 63]


zigzag_rom = [0]*64
for i in range(64):
    for j in range(64):
        if zigzag_order[j] == i:
            zigzag_rom[i] = j


class ZigZag(Module):
    def __init__(self):
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(12)))

        # # #

        zigzag_mem = Memory(8, 64, init=zigzag_rom)
        zigzag_read_port = zigzag_mem.get_port(async_read=True)
        self.specials += zigzag_mem, zigzag_read_port

        data_mem = Memory(12, 64*2)
        data_write_port = data_mem.get_port(write_capable=True)
        data_read_port = data_mem.get_port(async_read=True)
        self.specials += data_mem, data_write_port, data_read_port

        write_sel = Signal()
        write_swap = Signal()
        read_sel = Signal(reset=1)
        read_swap = Signal()
        self.sync += [
            If(write_swap,
                write_sel.eq(~write_sel)
            ),
            If(read_swap,
                read_sel.eq(~read_sel)
            )
        ]

        # write path
        write_clr = Signal()
        write_inc = Signal()
        write_count = Signal(6)
        self.sync += \
            If(write_clr,
                write_count.eq(0)
            ).Elif(write_inc,
                write_count.eq(write_count + 1)
            )

        self.comb += [
            data_write_port.adr.eq(write_count),
            data_write_port.adr[-1].eq(write_sel),
            data_write_port.dat_w.eq(sink.data),
            data_write_port.we.eq(sink.valid & sink.ready)
        ]

        self.submodules.write_fsm = write_fsm = FSM(reset_state="IDLE")
        write_fsm.act("IDLE",
            write_clr.eq(1),
            If(write_sel != read_sel,
                NextState("WRITE")
            )
        )
        write_fsm.act("WRITE",
            sink.ready.eq(1),
            If(sink.valid,
                If(write_count == 63,
                    write_swap.eq(1),
                    NextState("IDLE")
                ).Else(
                    write_inc.eq(1)
                )
            )
        )

        # read path
        read_clr = Signal()
        read_inc = Signal()
        read_count = Signal(6)
        self.sync += \
            If(read_clr,
                read_count.eq(0)
            ).Elif(read_inc,
                read_count.eq(read_count + 1)
            )

        self.comb += [
            zigzag_read_port.adr.eq(read_count),
            data_read_port.adr.eq(zigzag_read_port.dat_r), # XXX check latency
            data_read_port.adr[-1].eq(read_sel),
            source.data.eq(data_read_port.dat_r)
        ]

        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act("IDLE",
            read_clr.eq(1),
            If(read_sel == write_sel,
                read_swap.eq(1),
                NextState("READ")
            )
        )
        read_fsm.act("READ",
            source.valid.eq(1),
            source.last.eq(read_count == 63),
            If(source.ready,
            	read_inc.eq(1),
                If(source.last,
                    NextState("IDLE")
                )
            )
        )
