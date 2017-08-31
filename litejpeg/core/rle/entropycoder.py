"""
EntropyCoder Module:
----------------
This module is been made in order to calculate the number of bits to
store the amplitude used in the huffman encoding.
"""

# Importing libraries.
from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *


# To provide delay so in order to sink the data coming from the main
# module to that of the Datapath module.
datapath_latency = 3


@CEInserter()
class EntropyDatapath(Module):
    """
    EntropyDatapath :
    ------------------
    Calculate the bit value for the amplitude using EntropyCoder.

    Attributes:
    -----------
    sink   : Accepts the amplitude from RLEMain to calculate the number of bits
             required to store the amplitude.
    source : Give the output to the EntropyCoder depicting the number of bits
             required to store the amplitude.
    """
    def __init__(self):

        # Record the input and output of the Datapath.
        # sink = input
        # source = output
        self.sink = sink = Record(block_layout(12))
        self.source = source = Record(block_layout(4))

        # Getting the input.
        input_data = Signal(12)

        # The values for storing the temporary values for
        # calculating the size.
        get_data = Array(Signal(12) for i in range(12))

        # Store the output.
        size = Signal(4)

        # For calculating the size.

        # Storing the size in the input_data.
        self.sync += input_data.eq(sink.data)
        # Keep on interating over the input_data and see after shifting
        # how many bits the input_data value becomes zeros and that is the
        # number of bits required to store the input_data.
        for i in range(12):
            self.sync += get_data[i].eq(input_data >> i)
        for i in range(11,-1,-1):
            self.sync += [
             If(get_data[i] == 0,
                size.eq(i))
            ]

        # Connecting the source.data with the output.
        self.comb += source.data.eq(size)


class EntropyCoder(PipelinedActor, Module):
    """
    This module will connect the EntropyCoder datapath with the input
    and output either from other modules or from the Test Benches.
    The input is been taken from the sink and source and is been transferred to
    the EntropyCoder datapath by using read and write count.
    The EntrophyCoder will extract out the number of bits required to store
    the amplitude.

    Attributes :
    ------------
    sink   :  12 bits
              receives input from the RLEmain containing the amplitude.
    source :  4 bits
              transmit the number of bits required to store the amplitude.
    """

    def __init__(self):
        # Connecting the module to the input and the output.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(4)))

        # Adding PipelineActor to provide additional clock for the module.
        # This clock is useful to compensate the latency caused by the
        # datapath to process the first input.
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # Connecting EntropyCoder submodule.
        self.submodules.datapath = EntropyDatapath()
        self.comb += self.datapath.ce.eq(self.pipe_ce)

        # Intialising the variables.
        BLOCK_COUNT = 64
        # Check wheather to start write or not.
        write_sel = Signal()
        # To swap the write select.
        write_swap = Signal()
        # Check wheather to start read or not.
        read_sel = Signal(reset=1)
        # To swap the read_sel.
        read_swap = Signal()

        # read_swap and write_swap will keep on changing depending on the value
        # of the read and write select which further change the states of the FSM
        # to synchronize between reading and writing input.
        self.sync += [
            If(write_swap,
               write_sel.eq(~write_sel)),
            If(read_swap,
               read_sel.eq(~read_sel))
        ]

        # write path

        # To start the write_count back to 0.
        write_clear = Signal()
        # To increment the write_count.
        write_inc = Signal()
        # To keep track over which value of the matrix is under process.
        write_count = Signal(6)

        # For tracking the data adress.
        self.sync += \
            If(write_clear,
                write_count.eq(0)
            ).Elif(write_inc,
                write_count.eq(write_count + 1)
            )

        # To combine the datapath into the module
        self.comb += [
            self.datapath.sink.data.eq(sink.data + (-2*sink.data[11]*sink.data))
        ]

        """
        INIT

        Depending on the value of the read_sel and write_sel decide wheather
        the next state will be either read or write.
        Will clear the value of ``write_count`` to be 0.
        """
        self.submodules.write_fsm = write_fsm = FSM(reset_state="INIT")
        write_fsm.act("INIT",
                      write_clear.eq(1),
                      If(write_sel != read_sel,
                         NextState("WRITE_INPUT")))

        """
        WRITE_INPUT State

        Will increament the value of the write_count at every positive edge
        of the clock cycle till BLOCK_COUNT since we are getting a matrix of 64 blocks
        hence at write_count equal to BLOCK_COUNT it generate a signal saying this to be
        the last block of the matrix and write the data into the memory
        as per the data from the ``sink.data`` and when the value reaches BLOCK_COUNT
        the state again changes to that of the GET_RESET state.
        """
        write_fsm.act("WRITE_INPUT",
                      sink.ready.eq(1),
                      If(sink.valid,
                          If(write_count == BLOCK_COUNT-1,
                              write_swap.eq(1),
                              NextState("INIT")
                          ).Else(
                              write_inc.eq(1))
                      ))

        # read path

        # Intialising the values.
        read_clear = Signal()
        read_inc = Signal()
        read_count = Signal(6)

        # For keeping track of the adress by using the read_count.
        self.sync += \
            If(read_clear,
               read_count.eq(0)
            ).Elif(read_inc,
                read_count.eq(read_count + 1)
            )

        # Reading the input from the Datapath only when the output data is
        # valid.
        self.comb += [
            source.data.eq(self.datapath.source.data)
        ]

        # GET_RESET state
        self.submodules.read_fsm = read_fsm = FSM(reset_state="INIT")
        read_fsm.act("INIT",
                     read_clear.eq(1),
                     If(read_sel == write_sel,
                        read_swap.eq(1),
                        NextState("READ_OUTPUT")
                      ))

        """
        READ_INPUT state

        Will increament the value of the read_count at every positive edge
        of the clock cycle till BLOCK_COUNT and read the data from the memory, giving
        it to the ``source.data`` as input and when the value reaches BLOCK_COUNT the
        state again changes to that of the GET_RESET state.
        """
        read_fsm.act("READ_OUTPUT",
                     source.valid.eq(1),
                     source.last.eq(read_count == BLOCK_COUNT-1),
                     If(source.ready,
            	        read_inc.eq(1),
                        If(source.last,
                           NextState("INIT")
                        )
                      ))
