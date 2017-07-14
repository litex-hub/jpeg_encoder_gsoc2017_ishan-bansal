# RLE Core Module

# Importing libraries.
from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

"""
RLE Core Module:
----------------
This module is the core module for the Rle for calculating
the Amplitude and the Zero_count of the input data.

Parameter:
----------

Amplitude: It is the non-zero number present in the input matrix.

Runlength : It is the number of zeros before the non-zero Amplitude.
"""


# To provide delay so in order to sink the data coming from the main
# module to that of the Datapath module.
datapath_latency = 2


# CEInseter genenrates an additional instance named as self.ce
# This is used so that to provide an additional clock attached to the
# pipeline Actor in the main module.
@CEInserter()


class RLEDatapath(Module):
    
    def __init__(self):
        
        """
        RLEDatapath Module:
        -------------------
        This module is the datapath set for the steps required for
        the RLE module to take place.

        The input matrix contains two components,
        the first value of the matrix is called as the DC component and
        the rest of the values within the matrix are the AC component.

        The DC part is been encoded by subtracting the DC cofficient to that of
        the DC cofficient of the previous value of the DC matrix.

        The AC cofficients are been encoded by calculating the number of zeros
        before the non-zero AC cofficient called as the RUnlength.

        Parameters:
        -----------
        accumulator: Storing the non-zero AC or DC cofficient.

        runlength : for calculating the number of zeros before the non-zero AC
        cofficients.

        dovalid : indicate wheather the output data is valid or not.

        zero_count: Count the number of zeros.

        prev_dc_0 : Storing the previous value of DC component.

        sink : To take the input data to the Datapath module.

        source : To transfer the output data to the Datapath module.


        """

        """
        Intialising the variable for the Datapath module.
        """
        
        self.sink = sink = Record(block_layout(12))
        self.source = source = Record(block_layout(18))
        self.write_cnt = Signal(6)

        accumulator = Signal(12)
        accumulator_temp = Signal(12)
        runlength = Signal(12)
        self.dovalid = Signal(1)

        zero_count = Signal(6)
        prev_dc_0 = Signal(12)



        # For calculating the Runlength values.
        self.sync += [
        
        If(self.write_cnt==0,
            # If the write_cnt is zero than it is the starting of a new data hence the value
            # of the runlength will be zero directly.
            # Since the DC encoding is been done by subtracting the present value with the
            # previous value, hence the DC cofficient is been stored in the prev_dc_0.
            # After doing all making the dovalid equal to 1.
            accumulator.eq(sink.data - prev_dc_0),
            accumulator_temp.eq(accumulator),
            prev_dc_0.eq(sink.data),
            runlength.eq(0),
            accumulator_temp.eq(accumulator_temp + (-2)*accumulator_temp[11]*accumulator),
            self.dovalid.eq(1)
        ).Else(
              If(sink.data == 0,
                If(self.write_cnt == 63,
                    # If the data is zero and it is the end of the matrix than the output is
                    # generated to be with Amplitude = 0 and Runlength=0 this will automatically
                    # indicate the end of the matrix.
                    accumulator.eq(0),
                    runlength.eq(0),
                    self.dovalid.eq(1)
                    ).Else(
                    # Otherwise if zero is encountered in between than the only contribution is
                    # to increase the count of zero_count by 1.
                    zero_count.eq(zero_count+1),
                    self.dovalid.eq(0)
                    )
              ).Else(
              # Else if a non-zero AC cofficient is detected than the output is been generated with
              # the amplitude equal to that of the AC cofficient and the number of zeros are been 
              # indicated as the Runlength.
              # Making the dvalid to be 1.
              accumulator.eq(sink.data),
              runlength.eq(zero_count),
              zero_count.eq(0),
              accumulator_temp.eq(accumulator + (-2*accumulator[11]*accumulator)),
              self.dovalid.eq(1)
              )
        )
        ]

 
        self.sync += [

        # Connecting the Datapath module to the main module.
        self.source.data[0:12].eq(accumulator),
        self.source.data[12:18].eq(runlength)
        
        ]




class Runlength(PipelinedActor,Module):
    """
    This module will connect the Rle core datapath with the input and output either
    from other modules or from the Test Benches.
    The input is been taken from the sink and source and is been transferred to
    the RLE core datapath by using read and write count.
    """
    def __init__(self):

        # Connecting the module to the input and the output.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(18)))
        
        # Adding PipelineActor to provide additional clock for the module.
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # Connecting RLE submodule.
        self.submodules.datapath = RLEDatapath()
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
                write_sel.eq(~write_sel)
            ),
            If(read_swap,
                read_sel.eq(~read_sel)
            )
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
            self.datapath.write_cnt.eq(write_count),
            self.datapath.sink.data.eq(sink.data)
        ]

        

        """ 
        GET_RESET.

        Depending on the value of the read_sel and write_sel decide wheather the 
        next state will be either read or write.
        Will clear the value of ``write_count`` to be 0.
        """
        self.submodules.write_fsm = write_fsm = FSM(reset_state="GET_RESET")
        write_fsm.act("GET_RESET",
            write_clear.eq(1),
            If(write_sel != read_sel,
                NextState("WRITE_INPUT")
            )
        )
        
        """
        WRIYE_INPUT State

        Will increament the value of the write_count at every positive edge of the
        clock cycle till 63 and write the data into the memory as per the data 
        from the ``sink.data`` and when the value reaches 63 the state again changes to 
        that of the IDLE state.
        """
        write_fsm.act("WRITE_INPUT",
            sink.ready.eq(1),
            If(sink.valid,
                If(write_count == 63,
                    write_swap.eq(1),
                    NextState("GET_RESET")
                ).Else(
                    write_inc.eq(1)
                )
            )
        )

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

        # Reading the input from the Datapath only when the output data is valid.
        self.comb += [
            If(self.datapath.dovalid,
                source.data.eq(self.datapath.source.data)    
                )
        ]

        #GET_RESET state
        self.submodules.read_fsm = read_fsm = FSM(reset_state="GET_RESET")
        read_fsm.act("GET_RESET",
            read_clear.eq(1),
            If(read_sel == write_sel,
                read_swap.eq(1),
                NextState("READ_OUTPUT")
            )
        )

        """
        READ_INPUT state

        Will increament the value of the read_count at every positive edge of the
        clock cycle till 63 and read the data from the memory, giving it to the 
        ``source.data`` as input and when the value reaches 63 the state again changes to 
        that of the IDLE state.
        """
        read_fsm.act("READ_OUTPUT",
            source.valid.eq(1),
            source.last.eq(read_count == 63),
            If(source.ready,
            	read_inc.eq(1),
                If(source.last,
                    NextState("GET_RESET")
                )
            )
        )
