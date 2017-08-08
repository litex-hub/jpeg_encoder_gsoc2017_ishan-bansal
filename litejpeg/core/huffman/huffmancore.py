"""
 HuffmanEncoder Module
 This contains the top module for the Huffman Encoder
 """

# Import libraries
from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *
from litejpeg.core.huffman.ac_rom import ac_rom_core
from litejpeg.core.huffman.dc_rom import dc_rom_core

"""
HuffmanEncoder Module :

The module takes an input in the form of matrix containing 64 blocks with
20 bits each and give an output of variable number each having a bit_length
of 8 bits.
The module is connected to the other modules containing Huffman Tables which
are required for the process of encoding the input data.
This module takes input from the RLE module containing three paramenters:
1. Amplitude : Non-zero input in the input matrix of the RLE.
2. Runlength : Number of zeros before the non-zero amplitude.
3. Size : Number of bits required to store Amplitude.
Each of the output is of 8 bits.
The main purpose of the module is to serialize the data and encode the data
using Huffman tables.

Input data format : 20 bits
input_data[0:12] = Amplitude
input_data[12:16] = Size
input_data[16:20] = Runlength

Output data format: 8 bits
output_data[0:8]
"""

# This is introduced to provide delay in the module for stablizing the
# input coming from the other modules.
# This provides a delay of 2 clock cycles.
datapath_latency = 2


# Provide an additional clock in the module.
@CEInserter()
class HuffmanDatapath(Module):
    """ This gives the datapath for the serialization of the input data.
    The data coming to the module is been controlled by using
    ready_data_write and ready_data_read, as when the module is ready
    then the input ready_data_write will be 1 and when the data to the
    output is ready then ready_data_read is 1.

    Parameters:
    ----------
    Amplitude : 12 bits
                Non-zero amplitudes in the matrix.
    Size      : 4 bits
                Number of bits required to store the amplitude.
    Runlength : 4 bits
                Number of zeros before the non-zero amplitude.
    word_count: 6 bits
                Display the index of the matrix.
    source    : 8 bits
                Output of the serial data coming out.
    """
    def __init__(self):

        # Getting input from the HuffmanEncoder module.
        self.Amplitude = Amplitude = Signal(12)
        self.size = size = Signal(4)
        self.runlength = runlength = Signal(4)
        self.word_count = Signal(6)
        # Giving the output to the HuffmanEncoder module.
        self.source = source = Record(block_layout(9))

        # Getting ready the input and output data.

        # See wheather the input is ready to be process.
        self.ready_data_write = Signal(1)
        # See wheather the output is ready to process.
        self.ready_data_read = Signal(1)

        # Attaching the AC and DC ROM.
        self.submodules.dc_rom_got = dc_rom_core()
        self.submodules.ac_rom_got = ac_rom_core()

        # Maximum number of words in word_reg.
        # 16 from this cycle.
        # At Max 7 from the past cycle.
        width_word = 16+7
        # Stores data for giving the output when the bit_ptr reaches more than
        # 8 bits.
        word_reg = Array(Signal(1) for i in range(width_word))
        # For changing the state of the state machine.
        state = Signal(3)
        # Become high when the write_count = 1
        first_rle_word = Signal(1)
        # To provide delay in the IDLE state.
        delay = Signal(2)
        # Decide wheather IDLE state is ready to work.
        ready_one = Signal(1)

        # Keep track of the data to come out.
        bit_ptr = Signal(5)
        # Number of blocks to go as output.
        num_fifo_wrs = Signal(2)

        # High when the data is ready to go out.
        hfw_running = Signal(1)
        # Keep track of the block to come out.
        fifo_wrt_cnt = Signal(2)

        # To get the data out of the ROM.
        # vlc_dc, vlc_dc_size:
        #     Get the data and number of bits out to the DC ROM.
        # vlc_ac, vlc_ac_size :
        #     Get the data and number of bits out to the AC ROM.
        vlc_dc = Signal(16)
        vlc_dc_size = Signal(5)
        vlc_ac = Signal(16)
        vlc_ac_size = Signal(5)
        # Decide wheather the data_out is DC or AC
        # depending on the first_rle_word.
        vlc_d = Array(Signal() for i in range(16))
        vlc_size_d = Signal(5)

        # Get the output from the Amplitude and Number of bits required
        # to store the amplitude.
        # Providing delay to the output for providing synchronization.
        vli_ext = Array(Signal() for i in range(16))
        vli_ext_next = Array(Signal() for i in range(16))
        vli_ext_next_next = Array(Signal() for i in range(16))
        vli_ext_next_next_next = Array(Signal() for i in range(16))
        vli_ext_size = Signal(5)
        vli_ext_size_next = Signal(5)
        vli_ext_size_next_next = Signal(5)
        vli_ext_size_next_next_next = Signal(5)

        # For giving output to the Padding state.
        pad_byte = Signal(8)
        # For starting the PADDING state
        pad_reg = Signal(1)

        # For extracting the information out of the HuffmanEncoder Tables.
        self.comb += [

         self.dc_rom_got.address.eq(self.size),
         vlc_dc_size.eq(self.dc_rom_got.data_out_size),
         vlc_dc.eq(self.dc_rom_got.data_out_code),
         self.ac_rom_got.address1.eq(self.size),
         self.ac_rom_got.address2.eq(self.runlength),
         vlc_ac_size.eq(self.ac_rom_got.data_out_size),
         vlc_ac.eq(self.ac_rom_got.data_out_code)

        ]

        # For extracting the information for the Amplitude
        # and size of the amplitude.
        self.comb += [
         [If(j < vli_ext_size,
             vli_ext[j].eq(self.Amplitude[j]))
             for j in range(12)],
         vli_ext_size.eq(self.size)
        ]

        self.sync += [

         # MUX for selecting between AC and DC ROM.
         If(first_rle_word,
            [vlc_d[j].eq(vlc_dc[j]) for j in range(16)],
            vlc_size_d.eq(vlc_dc_size))
         .Else(
            [vlc_d[j].eq(vlc_ac[j]) for j in range(16)],
            vlc_size_d.eq(vlc_ac_size))

        ]

        # Calculating the number of blocks to go as output.
        self.comb += [
         num_fifo_wrs.eq(bit_ptr[3:5])
        ]

        # providing delay in order to synchronize the data.
        self.sync += [
          [vli_ext_next[i].eq(vli_ext[i]) for i in range(16)],
          [vli_ext_next_next[i].eq(vli_ext_next[i]) for i in range(16)],
          [vli_ext_next_next_next[i].eq(
           vli_ext_next_next[i]) for i in range(16)],
          vli_ext_size_next.eq(vli_ext_size),
          vli_ext_size_next_next.eq(vli_ext_size_next),
          vli_ext_size_next_next_next.eq(vli_ext_size_next_next),
        ]

        # Handling FIFO write.
        self.sync += [

         If(hfw_running,
            If(num_fifo_wrs == 0,
               self.ready_data_read.eq(0))
            .Else(
               If(fifo_wrt_cnt == num_fifo_wrs,
                  self.ready_data_read.eq(0))
               .Else(
                     fifo_wrt_cnt.eq(fifo_wrt_cnt+1),
                     self.ready_data_read.eq(1)
               )
             )),
         If(fifo_wrt_cnt == 0,
            [self.source.data[i].eq(
                    word_reg[width_word-8+i]) for i in range(8)])
         .Elif(fifo_wrt_cnt == 1,
               [self.source.data[i].eq(
                    word_reg[width_word-16+i]) for i in range(8)])
         .Else(
               self.source.data.eq(0)),

         If(pad_reg == 1,
            self.source.data.eq(pad_byte))

        ]

        # State Machine.
        self.sync += [

         # IDLE state
         If(state == 0,
            If(self.word_count == 0,
               first_rle_word.eq(1)),
            If(delay == 2,
               state.eq(1),
               self.ready_data_write.eq(1),
               ready_one.eq(1))
            .Else(
                  delay.eq(delay+1)))
         # VLC state
         .Elif(state == 1,
               If(ready_one,

                  [If(i < vlc_size_d,
                      word_reg[width_word-1-bit_ptr-i].eq(
                          vlc_d[vlc_size_d-1-i]))
                      for i in range(width_word)],
                  bit_ptr.eq(bit_ptr + vlc_size_d),
                  self.ready_data_write.eq(0),
                  hfw_running.eq(1),
                  ready_one.eq(0)

                  ).Elif(hfw_running & (
                         (num_fifo_wrs == 0) | (fifo_wrt_cnt == num_fifo_wrs)),

                         [If(i+(num_fifo_wrs*8) < width_word,
                             word_reg[width_word-1-i].eq(
                                 word_reg[width_word-1-(num_fifo_wrs*8)-i]))
                             for i in range(width_word)],

                         bit_ptr.eq(bit_ptr - (num_fifo_wrs*8)),
                         hfw_running.eq(0),
                         fifo_wrt_cnt.eq(0),
                         first_rle_word.eq(0),
                         state.eq(2),
                         ready_one.eq(1)))
         # VLI state
         .Elif(state == 2,

               If(hfw_running == 0,

                  [If(i < vli_ext_size_next_next_next,
                      word_reg[width_word-1-bit_ptr-i].eq(
                          vli_ext_next_next_next[
                              vli_ext_size_next_next_next-1-i]))
                      for i in range(width_word)],
                  bit_ptr.eq(bit_ptr + vli_ext_size_next_next_next),
                  hfw_running.eq(1)

                  ).Elif(hfw_running & (
                             (num_fifo_wrs == 0) | (
                                 fifo_wrt_cnt == num_fifo_wrs)),

                         [If(i+(num_fifo_wrs*8) < width_word,
                             word_reg[width_word-1-i].eq(
                             word_reg[width_word-1-(num_fifo_wrs*8)-i]))
                             for i in range(width_word)],
                         bit_ptr.eq(bit_ptr - (num_fifo_wrs*8)),
                         hfw_running.eq(0),
                         fifo_wrt_cnt.eq(0),

                         # Taking care of the last block.
                         If(self.word_count == 63,
                            If((bit_ptr - (num_fifo_wrs*8)) != 0,
                               state.eq(3))
                            .Else(
                                  state.eq(0))
                            ).Else(
                                   state.eq(1),
                                   self.ready_data_write.eq(1))))
         # Padding state
         .Else(
               If(hfw_running == 0,

                  [(If(i < bit_ptr,
                       pad_byte[7-i].eq(word_reg[width_word-1-i])
                       ).Else(
                              pad_byte[7-i].eq(1)
                     )) for i in range(8)],
                  pad_reg.eq(1),
                  bit_ptr.eq(8),
                  hfw_running.eq(1)
                  ).Elif(
                      hfw_running &
                      ((num_fifo_wrs == 0) | (fifo_wrt_cnt == num_fifo_wrs)),

                      bit_ptr.eq(0),
                      hfw_running.eq(0),
                      pad_reg.eq(0),
                      state.eq(0))
         )]


class HuffmanEncoder(PipelinedActor, Module):
    """
    This Module defines the main module for getting the input and output to the
    HuffmanDatapath from the other module.
    The input is been taken from the 'sink' with the Endstream of length
    20 bits and the output is been sent by using 'source' with 9 bits.
    The input and the output are been synchronized by using the ready_data_read
    and ready_data_write.
    """
    def __init__(self):

        # Connecting the module to the input and the output.
        self.sink = sink = stream.Endpoint(
            EndpointDescription(block_layout(20)))
        self.source = source = stream.Endpoint(
            EndpointDescription(block_layout(9)))

        # Adding PipelineActor to provide additional clock for the module.
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # For handling the inputs and outputs.
        self.ready_data_write = Signal()
        self.ready_data_read = Signal()

        # Connecting Huffman Datapath for passing inputs and outputs.
        self.submodules.datapath = HuffmanDatapath()
        self.comb += self.datapath.ce.eq(self.pipe_ce)

        # Intialising the variables.
        write_sel = Signal()
        write_swap = Signal()
        read_sel = Signal(reset=1)
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
            self.ready_data_write.eq(self.datapath.ready_data_write),
            self.datapath.Amplitude.eq(sink.data[0:12]),
            self.datapath.size.eq(sink.data[12:16]),
            self.datapath.runlength.eq(sink.data[16:20]),
            self.datapath.word_count.eq(write_count)
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
                      self.ready_data_write.eq(1),
                      If(write_sel != read_sel,
                         NextState("WRITE_INPUT")))

        """
        WRITE_INPUT State

        Will increament the value of the write_count at every positive edge of
        the clock cycle till 63 and write the data into the memory as per the
        data from the ``sink.data`` and when the value reaches 63 the state
        again changes to that of the IDLE state.
        """
        write_fsm.act("WRITE_INPUT",
                      If(self.ready_data_write,
                         sink.ready.eq(1),
                         If(sink.valid,
                            If(write_count == 63,
                               write_swap.eq(1),
                               NextState("GET_RESET"))
                            .Else(
                                  write_inc.eq(1)
                                  )))
                      .Else(
                            sink.ready.eq(0),
                            write_inc.eq(0)
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
                      read_count.eq(read_count + 1))

        # Reading the input from the Datapath only when the output data is
        # valid.
        self.comb += [
            self.ready_data_read.eq(self.datapath.ready_data_read),
            If(self.datapath.ready_data_read,
                source.data.eq(self.datapath.source.data),
                source.data[8].eq(self.datapath.ready_data_read))
        ]

        # GET_RESET state
        self.submodules.read_fsm = read_fsm = FSM(reset_state="GET_RESET")
        read_fsm.act("GET_RESET",
                     read_clear.eq(1),
                     self.ready_data_read.eq(1),
                     If(read_sel == write_sel,
                        read_swap.eq(1),
                        NextState("READ_OUTPUT")))
        """
        READ_INPUT state

        Will increament the value of the read_count at every positive edge of
        the clock cycle till 63 and read the data from the memory, giving it to
        the ``source.data`` as input and when the value reaches 63 the state
        again changes to that of the IDLE state.
        """
        read_fsm.act("READ_OUTPUT",
                     If(self.ready_data_read,
                        source.valid.eq(1),
                        source.last.eq(read_count == 63),
                        If(source.ready,
                           read_inc.eq(1),
                           If(source.last,
                              NextState("GET_RESET"))))
                     .Else(
                           source.valid.eq(0),
                           read_inc.eq(0)
                          )
                     )
