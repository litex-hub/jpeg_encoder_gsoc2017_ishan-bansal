# ZigZag

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

"""
Rearranging the value of the YCbCr matrix
-----------------------------------------
This module will rearrange the values of the matrix in such a way that
the number of zeros obtained should be maximum.
This will help in the better compression at the time Run Length Encoder.

The order of arrangement is been provided within the zigzag_order as that
will decide which value is been replaced by which one.
"""

zigzag_order = [
 0,  1,  5,  6, 14, 15, 27, 28,
 2,  4,  7, 13, 16, 26, 29, 42,
 3,  8, 12, 17, 25, 30, 41, 43,
 9, 11, 18, 24, 31, 40, 44, 53,
 10, 19, 23, 32, 39, 45, 52, 54,
 20, 22, 33, 38, 46, 51, 55, 60,
 21, 34, 37, 47, 50, 56, 59, 61,
 35, 36, 48, 49, 57, 58, 62, 63]

# Marking the order in which the values are need to be arranged.
zigzag_rom = [0]*64
for i in range(64):
    for j in range(64):
        if zigzag_order[j] == i:
            zigzag_rom[i] = j


class ZigZag(Module):
    """
    This will take the values for the zigzag module.

    The values are been taken by in the form of serial input and stored in the
    memory named data_mem.
    Than another zigzag_mem is present which contains the order in which the
    values need to be rearranged.
    The data when read from the memory are than taken in order for zigzag_mem
    hence read in that form.

    """
    def __init__(self):
        self.sink = sink = stream.Endpoint(
            EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(
            EndpointDescription(block_layout(12)))

        # # #

        """
        zigzag_mem : 64 blocks
        Stores the data in the form in which the data needs to be rearranged.

        Attributes:
        -----------
        zigzag_read_port : Read the signal from the memory location as per
                           the address in the zigzag_mem.adr .

        """
        zigzag_mem = Memory(8, 64, init=zigzag_rom)
        zigzag_read_port = zigzag_mem.get_port(async_read=True)
        self.specials += zigzag_mem, zigzag_read_port

        """
        data_mem : 128 blocks
        Stores the data from the serial input and read the data
        from the memory when needed.

        Attributes:
        -----------
        data_write_port : Write whatever in the ``sink.data`` into the memory
                          with address stored in data_write_port.adr

        data_read_port :  Read the data from the memory as per the address
                          stored in data_mem.adr

        write_sel : Decide wheather the port have to read or write
                    through the memory.

        read_sel : Decide wheather the port have to read or write
                   through the memory.

        write_swap : Change the value of the ``write_sel``.

        read_swap : Change the value of the ``read_sel``.

        read_count : Determine the address when the data is to read in the
                     memory increment from 0 to 63 and than again turn to 0.

        write_count : Determine the address when the data is to written in the
                      memory increment from 0 to 63 and than again comes to 0.

        read_clr : Clears the ``read_count`` to 0.

        write_clr : Clears the ``write_count`` to 0.

        read_inc : Will increment the ``read_count`` on every positive
                   edge of the clock.

        write_inc : Will increment the ``write_count`` on every positive
                    edge of the clock.
        """

        # intialise the memory named as data_mem.
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
               write_sel.eq(~write_sel)),
            If(read_swap,
               read_sel.eq(~read_sel))
        ]

        # write path
        write_clr = Signal()
        write_inc = Signal()
        write_count = Signal(6)
        self.sync += \
            If(write_clr,
               write_count.eq(0)
               ).Elif(write_inc,
                      write_count.eq(write_count + 1))

        self.comb += [
            data_write_port.adr.eq(write_count),
            data_write_port.adr[-1].eq(write_sel),
            data_write_port.dat_w.eq(sink.data),
            data_write_port.we.eq(sink.valid & sink.ready)
        ]

        """
        IDLE State.

        Depending on the value of the read_sel and write_sel
        decide wheather the next state will be either read or write.
        Will clear the value of ``write_count`` to be 0.
        """
        self.submodules.write_fsm = write_fsm = FSM(reset_state="IDLE")
        write_fsm.act("IDLE",
                      write_clr.eq(1),
                      If(write_sel != read_sel,
                         NextState("WRITE")))
        """
        Write State

        Will increament the value of the write_count at every positive
        edge of the clock cycle till 63 and write the data into the memory
        as per the data from the ``sink.data`` and when the value
        reaches 63 the state again changes to that of the IDLE state.
        """
        write_fsm.act("WRITE",
                      sink.ready.eq(1),
                      If(sink.valid,
                         If(write_count == 63,
                            write_swap.eq(1),
                            NextState("IDLE")
                            ).Else(
                                   write_inc.eq(1))))

        # read path
        read_clr = Signal()
        read_inc = Signal()
        read_count = Signal(6)
        self.sync += \
            If(read_clr,
               read_count.eq(0)
               ).Elif(read_inc,
                      read_count.eq(read_count + 1))

        self.comb += [
            zigzag_read_port.adr.eq(read_count),
            data_read_port.adr.eq(zigzag_read_port.dat_r),
            data_read_port.adr[-1].eq(read_sel),
            source.data.eq(data_read_port.dat_r)
        ]

        # IDLE state
        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act("IDLE",
                     read_clr.eq(1),
                     If(read_sel == write_sel,
                        read_swap.eq(1),
                        NextState("READ")))
        """
        READ state

        Will increament the value of the read_count at every positive edge
        of the clock cycle till 63 and read the data from the memory,
        giving it to the ``source.data`` as input and when the value
        reaches 63 the state again changes to that of the IDLE state.
        """
        read_fsm.act("READ",
                     source.valid.eq(1),
                     source.last.eq(read_count == 63),
                     If(source.ready,
                        read_inc.eq(1),
                        If(source.last,
                           NextState("IDLE"))))
