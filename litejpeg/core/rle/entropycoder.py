# Entropycoder Module

# Importing libraries.
from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

"""
Entropycoder Module:
----------------
This module is been made in order to calculate the number of bits to
store the Amplitude.

Parameters:
-----------
input_data :
    Contains the input data coming from the other modules or the Test Benches.
size :
    Contains the number of bits in the Amplitude.
"""


# To provide delay so in order to sink the data coming from the main
# module to that of the Datapath module.
datapath_latency = 3


@CEInserter()
class EntropyDatapath(Module):

    """
    EntropyDatapath :
    ------------------
    It contains the steps for the Entropycoder to calculate the bits for the
    Amplitude to store.

    Parameters:
    -----------
    sink : Get the input from the other modules.
           The input is the modulus of the input.
    source : Give the output to the other modules.
    input_data : modulus of input of the matrix.
    get_data : Contains the temporary data for calculating the size.
    size : The number of bits required for storing th amplitude.

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
        # Interating over different values from 1 to 12.
        for i in range(12):
            self.sync += get_data[i].eq(input_data >> i)
        for i in range(12):
            self.sync += [
             If(get_data[11-i] == 0,
                size.eq(11-i))
            ]

        # Connecting the source.data with the output.
        self.comb += source.data.eq(size)


class Entropycoder(PipelinedActor, Module):
    """
    This module will connect the Entropycoder datapath with the input
    and output either from other modules or from the Test Benches.
    The input is been taken from the sink and source and is been transferred to
    the Entropycoder datapath by using read and write count.
    """
    def __init__(self):

        # Connecting the module to the input and the output.
        self.sink = sink = stream.Endpoint(
                               EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(
                                   EndpointDescription(block_layout(4)))

        # Adding PipelineActor to provide additional clock for the module.
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # Connecting Entropycoder submodule.
        self.submodules.datapath = EntropyDatapath()
        self.comb += self.datapath.ce.eq(self.pipe_ce)

        # Intialising the variables.

        # Check wheather to start write or not.
        write_sel = Signal()
        # To swap the write select.
        write_swap = Signal()
        # Check wheather to start read or not.
        read_sel = Signal(reset=1)
        # To swap the read_sel.
        read_swap = Signal()

        # To swap the read and write select whenever required.
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
                      write_count.eq(write_count + 1))

        # To combine the datapath into the module
        self.comb += [
            self.datapath.sink.data.eq(sink.data + (-2*sink.data[11]*sink.data))
        ]

        """
        GET_RESET.

        Depending on the value of the read_sel and write_sel decide wheather
        the next state will be either read or write.
        Will clear the value of ``write_count`` to be 0.
        """
        self.submodules.write_fsm = write_fsm = FSM(reset_state="GET_RESET")
        write_fsm.act("GET_RESET",
                      write_clear.eq(1),
                      If(write_sel != read_sel,
                         NextState("WRITE_INPUT")))

        """
        WRITE_INPUT State

        Will increament the value of the write_count at every positive edge
        of the clock cycle till 63 and write the data into the memory
        as per the data from the ``sink.data`` and when the value reaches 63
        the state again changes to that of the GET_RESET state.
        """
        write_fsm.act("WRITE_INPUT",
                      sink.ready.eq(1),
                      If(sink.valid,
                         If(write_count == 63,
                            write_swap.eq(1),
                            NextState("GET_RESET")
                            ).Else(
                                   write_inc.eq(1))))

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
                      read_count.eq(read_count + 1))

        # Reading the input from the Datapath only when the output data is
        # valid.
        self.comb += [
            source.data.eq(self.datapath.source.data)
        ]

        # GET_RESET state
        self.submodules.read_fsm = read_fsm = FSM(reset_state="GET_RESET")
        read_fsm.act("GET_RESET",
                     read_clear.eq(1),
                     If(read_sel == write_sel,
                        read_swap.eq(1),
                        NextState("READ_OUTPUT")))

        """
        READ_INPUT state

        Will increament the value of the read_count at every positive edge
        of the clock cycle till 63 and read the data from the memory, giving
        it to the ``source.data`` as input and when the value reaches 63 the
        state again changes to that of the GET_RESET state.
        """
        read_fsm.act("READ_OUTPUT",
                     source.valid.eq(1),
                     source.last.eq(read_count == 63),
                     If(source.ready,
            	        read_inc.eq(1),
                        If(source.last,
                           NextState("GET_RESET"))))
