from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

class HuffmanDatapath(Module):
    def __init__(self):

        self.sink = sink = Record(block_layout(20))
        self.source = source = Record(black_layout(64*20))

        self.comb += [
        Amplitude.eq(sink[0:12]),
        size.eq(sink[12:16]),
        runlength.eq(sink[16:20])
        ]

        width_word = 16+7
        state = Signal(3)
        first_rle_word = Signal(1)

        word_reg = Signal(word_word)
        bit_ptr = Signal(5)
        num_fifo_wrs = Signal(2)

        ready_hfw = Signal(1)
        fifo_wrt_cnt = Signal(2)
        last_block = Signal(1)

        img_area = Signal(16)

        vlc_dc = Signal(16)
        vlc_dc_size = Signal(5)
        vlc_ac = Signal(16)
        vlc_ac_size = Signal(5)
        vlc_d = Signal(16)
        vlc_size_d = Signal(5)

        vli_ext = Signal(16)
        vli_ext_size = Signal(5)

        pad_byte = Signal(8)
        pad_reg = Signal(1)

        self.sync += [
        # Selecting the encrypted data bits along with the size to store them.
        dc_rom(self,size,vlc_dc_size,vlc_dc),
        ac_rom(self,runlength,size,vlc_ac_size,vlc_ac)
        ]

        self.sync += [

        # Selecting the AC and DC ROM.
        If(first_rle_word,
           vlc_d.eq(vlc_dc),
           vlc_size_d.eq(vlc_dc_size)
        ).Else(
           vlc_d.size(vlc_ac),
           vlc_size_d.eq(vlc_ac_size)
        )

        ]

        self.sync += [

        If(state_temp,
            read_enable_temp.eq(True and ~rle_fifo_empty)
          ),

        If(hfw_running and ~ready_hfw,
             If(num_fifo_wrs==0,
                  ready_hfw.eq(True),
                  If(state == 2,
                       read_enable_temp.eq(True and not rle_fifo_empty)
                   )
             ).Else(
                  fifo_wrt_cnt.eq(fifo_wrt_cnt+1),
                  # dfifo.write.next = True
                  If((fifo_wrt_cnt +1)==num_fifo_wrs,
                        ready_hfw.eq(1),
                        If(state == 2,
                              read_enable_temp.eq(True and not rle_fifo_empty)
                        ),
                        fifo_wrt_cnt.eq(0)
                    )
               )
           ),

          If(fifo_wrt_cnt == 0,
               #dfifo.write_data.next = word_reg[(width_word):(width_word-8)]
          ).Elseif(fifo_wrt_cnt == 1,
               #dfifo.write_data.next = word_reg[(width_word-8):(width_word-16)]
          ).Else(
               #dfifo.write_data.next = 0
          ),

          If(pad_reg == 1,
              #dfifo.write_data.next = pad_byte)
          )

        ]

        self.sync += [
        # State Machine

        # IDLE state
        If(state == 0,

            If(huffman.start,

            first_rle_word.eq(1),
            state.eq(1)
            )

        # VLC state
        ).Elseif(state ==1,

           [word_reg[width_word-1-bit_ptr-i].eq(vlc[vlc_size -i-1]) for i in range(vlc_size)],
           bit_ptr.eq(bit_ptr + vlc_size),
           hfw_running.eq(1),

                If(hfw_running and ((num_fifo_wrs==0) or (fifo_wrt_cnt+1 == num_fifo_wrs)),

                word_reg.eq(word_reg << (num_fifo_wrs)*8),
                bit_ptr.eq(bit_ptr + vlc_size),
                hfw_running.eq(0),
                first_rle_word.eq(0),
                state.eq(2)
           )
        # VLI state
        ).Elseif(state==2,

           If(hfw_running==0,

                [(word_reg[width_word-1-btr_ptr-i].eq(vli_ext[vli_ext_size-1-i]))for i in range(vli_ext_size)],
                bit_ptr.eq(bit_ptr + vli_ext_size),
                hfw_running.eq(1)

           ).Elseif(hfw_running and ((num_fifo_wrs==0) or (fifo_wrt_cnt+1 == num_fifo_wrs)),

                word_reg.eq(word_reg << (num_fifo_wrs*8)),
                bit_ptr.eq(bit_ptr - (num_fifo_wrs*8)),
                hfw_running.eq(0),

                If(rle_fifo_empty,

                    If((bit_ptr - (num_fifo_wrs * 8))!=0 and last_block,

                      state = 3
                    ).Else(
                    # huffmancntrl.ready.next = True
                    state = 0
                    )
                ).Else(

                state = 1
                )
           )

        # Padding state
        ).Else(

           If(hfw_running !=0,

                [(If(i<bit_ptr,
                      pad_byte[7-i].eq(word_reg[width_word-1-i])
                     ).Else(
                     pad_byte[7-i].eq(1)
                     )) for i in range(7)],
                pad_reg.eq(1),
                bit_ptr.eq(8),
                hfw_running.eq(1)
            ).Elseif(hfw_running and (num_fifo_wrs == 0 or (fifo_wrt_cnt+1)==num_fifo_wrs),

                bit_ptr.eq(0),
                hfw_running.eq(0),
                pad_reg.eq(0),
                # huffmancntrl.ready = T
                state.eq(0)
            )
        )
        ]

class Huffman(PipelinedActor,Module):
    
    def __init__(self):

        # Connecting the module to the input and the output.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(20)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(64*20)))

        # Adding PipelineActor to provide additional clock for the module.
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # Connecting RLE submodule.
        self.submodules.datapath = HuffmanDatapath()
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
            If(self.datapath.dovalid_next_next,
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
