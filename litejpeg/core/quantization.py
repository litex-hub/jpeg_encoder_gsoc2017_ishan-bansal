"""
Quantization Module
===================

In this quantization module, we are dividing our matrix with certain values as per the quantization table to increase the number of
zeros that is used in the compression in the next stages.
However instead of dividing which creates a problem because of non-storage of decimal values as such in a signal,
We are going to multiply the values with the inverse of the values within the matrix.
And give the output for the next stage.

"""

from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.csr import *

from litejpeg.core.common import *

# Building up the quantization table required for the quantization module.
# Must be specified previously.
quant_values=[16, 11, 10, 16, 24, 40, 51, 61,
              12, 12, 14, 19, 26, 58, 60, 55,
              14, 13, 16, 24, 40, 57, 69, 56,
              14, 17, 22, 29, 51, 87, 80, 62,
              18, 22, 37, 56, 68,109,103, 77,
              24, 35, 55, 64, 81,104,113, 92,
              49, 64, 78, 87,103,121,120,101,
              72, 92, 95, 98,112,100,103, 99]


class Quantization(PipelinedActor, Module):
    def __init__(self):

        # Connecting the data to the Test Bench to take the input/give the output.
        # sink = Take the data for the module.
        # source = Show the output specified by the module.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(12)))


        """
        Quantization ROM
        ================

        Storing values of the quantization tables.
        We are storing the inverse of the values in the qunatization table.
        However that lead to a floating point number which is not a migen value.
        Hence we are storing (2**16)/quantization value.
        This provide us appropriate precision for the process.
        
        """
        inverse = Memory(16,2**6)
        invese_write_port = inverse.get_port(write_capable=True)
        inverse_read_port = inverse.get_port(async_read=True)
        self.specials += inverse, inverse_read_port,invese_write_port

        for i in range(64):
            self.comb += inverse[i].eq(int((2**16)/quant_values[i]))



        #Collecting the input values from the previous module and store them in a memory.
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

        
        # Divider
        # Here is the code for the dividing the input values with the quantization values.

        # Intialising variables.
        data_temp_signed = Signal(12)
        data_temp_unsigned = Signal(12)
        mult_temp_unsigned = Signal(29)
        mult_temp_unsigned_original = Signal(12)
        mult_temp_signed_original = Signal(12)
        mult_temp_unsigned_round = Signal(12)
        sign = Signal(1)


        self.comb += [
            # Take an input and store it in data_temp_signed along with the sign.
            # Sign because we obtain floating point value after the division 
            # process, hence the sign will help in rounding off to the nearest 
            # neighbour.
            data_temp_signed.eq(data_mem[read_count]),

            # Getting wheather it is a positive or negative integer.
            # sign = 1 (for negative).
            # sign = 0 (for positive). 
            sign.eq(data_temp_signed[11]),

            # Making the Input unsigned from signed.
            # If positive :
            # than sign == 0 , data_temp_unsigned = data_temp_signed
            # Else if negative :
            # than sign == 1 , data_temp_unsigned = data_temp_singed*(-1) 
            data_temp_unsigned.eq(data_temp_signed + (-2*sign*data_temp_signed)),

            # Doing division with the quantization values.
            mult_temp_unsigned.eq(data_temp_unsigned*inverse[read_count]),

            # Dividing by (2**16) intially multiplied.
            mult_temp_unsigned_original.eq(mult_temp_unsigned[16:28]),

            # Rounding the value of the output get.
            mult_temp_unsigned_round.eq(mult_temp_unsigned_original+(mult_temp_unsigned[15])),

            # Putting the sign back.
            mult_temp_signed_original.eq(mult_temp_unsigned_round + (-2*sign*mult_temp_unsigned_round)),

            # Making it at the output.
            source.data.eq(mult_temp_signed_original)
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