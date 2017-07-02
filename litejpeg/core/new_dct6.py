# DCT
import math

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

'''
This module is for the purpose of the DCT transformation.

As the input given to this module is in the form of serial input of the value of approximately
64*12 bits. This will go into the DCTdatapath where DCT1d conversion should take place on the 
matrix formed after making 64 values of 12 bits each out of the serial input.
Then the transpose of the resltant matrix is obtained and dct1D is again applied on this matrix.
Finally the matrix which is been obtained is been converter into the serial output of 64*12 bits.
'''
datapath_latency = 8

@CEInserter()
class DCTDatapath(Module):
    """
    Providing the Datapath for the DCT module
    -----------------------------------------
    This will take the input as YCbCr matrix and than convert it into the DCT matrix. The matrix
    so formed is been passed through the zigzag or the quantization module so that the
    compression done will be maximum.

    Input:
    ------
    It takes the input in the form of 64 blocks of 8 bits each as unsigned int.

    Output:
    -------
    Gives 64 blocks of 8 bits with signed int.

    """

    def __init__(self, dw, dct_block):
        
        """
        Undergoing DCT2d conversion
        ===========================
        Will undergo the DCT conversion of the matrix taken as an input.

        Attributes
        ----------
        "vector"+str(i) for i in range(8) : 8 blocks with 8 bits each.
        Taking its values from the dct_dalayed passed as an input to the DCT1d module.

        vector_out : 64 blocks with 8 bits each
        Take the output from the DCT1d module for each of the above input.

        vector2_str(i) for i in range(8) : Each has 8 blocks with 8 bits.
        Transpose vector_out and take the values to pass as an input to the DCT1d module.

        vector2_out : 64 blocks with 8 bits in each.
        Contains the output from the DCT1d module from the above input.

        vector2_final : 64 blocks with 8 bits each.
        Transpose of the vector2_out matrix above.
        
        """
        
        # Record the input and the output of the Datapath.
        # input = Sink.
        # output = Source. 
        self.sink = sink = Record(dct_block_layout(dw,dct_block))
        self.source = source = Record(dct_block_layout(dw,dct_block))

         # # #

        dct_matrix_1d = Array(Array(Signal(dw) for a in range(8)) for b in range(8))

        # intialise the vectors for 8 blocks at a time that will undergo DCT processing
        # at a time.
        vector = Array(Array(Signal(dw) for a in range(8)) for b in range(8))

        vector_out = Array(Signal(dw) for a in range(64))
        vector2_out = Array(Signal(dw) for a in range(64))
        vector2final_out = Array(Signal(dw) for a in range(64))
        vector2final_outdivide = Array(Signal(dw) for a in range(64))
        
        # Since the output doesn't come in a single clock cycle. Hence there is a need of
        # providing delay in the output which is determined by datapath_latency of the
        # module and provided as below:
        dct_delayed = [sink]
        for i in range(datapath_latency):
            dct_n = Record(dct_block_layout(dw,dct_block))
            for k in range(dct_block):
                name = "dct_" + str(k)
                self.sync += getattr(dct_n, name).eq(getattr(dct_delayed[-1], name))
            dct_delayed.append(dct_n)
            

        # Assigning vectors 8 blocks for which the DCT conversion has to take place.
        for j in range(8):
            for y in range(8):
                name = "dct_"+str((8*y)+j)
                self.sync += vector[y][j].eq(getattr(dct_delayed[-1],name)-128)           

        # Assign DCT to every block to get the result.
        for w in range(8):
            self.dct1D(vector[w],dw,vector_out[8*w:(w+1)*8])

        # Now intialising the vectors for applying the DCT function on the transpose matrix.
        vector2 = Array(Array(Signal(dw) for a in range(8)) for b in range(8))

        # Assigning values for DCT on the transpose matrix.
        for a in range(8):
            for i in range(8):
                self.sync += vector2[i][a].eq(vector_out[8*a+i])

        for r in range(8):
            self.dct1D(vector2[r],dw,vector2_out[r*8:(r+1)*8])


        # Assigning the result to the final matrix.
        for p in range(8):
            for g in range(8):
                self.sync += vector2final_out[8*p+g].eq(vector2_out[p+(8*g)])

        # Dividing the resultant matrix by 8.
        for r in range(64):
            self.sync += vector2final_outdivide[r].eq(vector2final_out[r]>>3)
            for t in range(3):
                self.sync += vector2final_outdivide[r][9+t].eq(vector2final_outdivide[r][8])
            

        # Assigning the final matrix to the output.
        for m in range(64):
            name = "dct_"+str(m)
            self.sync += getattr(source, name).eq(vector2final_outdivide[m])
        
 

    def dct1D(self,vector1d,dw,vector1d_out):

        """
        This will do the DCT operation over a single row or column. This will get
        the DCT2D by providing DCT1d over each of the row and than take the 
        transpose and than do the DCT1d over each column.

        input : Get 8 blocks of 8 bits each with unsigned int.

        output : Give 8 blocks of 8 bits each with signed int.

        Parameters :
        ------------
        dw : int
             number of bits in each block.
        vector1d_out : Array of unsigned integers.
              The input to the DCT1d for the purspose of DCT operation.

        """

        #1st stage

        vector8 = Array(Signal(dw) for a in range(8))

        self.sync += vector8[3].eq(vector1d[3]+vector1d[4])
        self.sync += vector8[4].eq(vector1d[3]-vector1d[4])
        self.sync += vector8[2].eq(vector1d[2]+vector1d[5])
        self.sync += vector8[5].eq(vector1d[2]-vector1d[5])
        self.sync += vector8[1].eq(vector1d[1]+vector1d[6])
        self.sync += vector8[6].eq(vector1d[1]-vector1d[6])
        self.sync += vector8[0].eq(vector1d[0]+vector1d[7])
        self.sync += vector8[7].eq(vector1d[0]-vector1d[7])

        #2nd stage

        vector9 = Array(Signal(dw) for a in range(8))

        self.sync += vector9[0].eq(vector8[0]+vector8[3])
        self.sync += vector9[3].eq(vector8[0]-vector8[3])
        self.sync += vector9[1].eq(vector8[1]+vector8[2])
        self.sync += vector9[2].eq(vector8[1]-vector8[2])

        """
        This migen doesn't support floating values for signals. Hence the following
        method is used for the purpose.
        1. Multiply the floating value with the power of 2.
        2. Now multiply the number obtained to get the resultant signal.
        3. The resultant signal is than divided by the power of 2 to get
           the actual answer. ( division is done with the help of right 
           shifting. )

        Depending on which value is most suitable for each of them we get 
        different multiplication factor for each of the floating value as 
        follows :
        cospi6 : 1024
        cos3pi6 : 256
        cos6pi6 : 128
        sinpi6 : 128
        sin3pi6 : 1024
        sin6pi6 : 512

        """

        cospi6 = Signal(2*dw)
        self.sync += cospi6.eq(1004)    
        cos3pi6 = Signal(2*dw)
        self.sync += cos3pi6.eq(213)    
        cos6pi6 = Signal(2*dw)
        self.sync += cos6pi6.eq(49)     
        sinpi6 = Signal(2*dw)
        self.sync += sinpi6.eq(25)      
        sin3pi6 = Signal(2*dw)
        self.sync += sin3pi6.eq(569)    
        sin6pi6 = Signal(2*dw)
        self.sync += sin6pi6.eq(473)    

        # multiplication by cosine and sine
            
        vector8_4block = Signal(2*dw)
        # bit extension by deciding wheather the most significant bit is 1 or 0 
        vector8_4block_Maxbit = Signal(1)
        self.sync += vector8_4block_Maxbit.eq(vector8[4][11])
        for r in range(12):
            self.sync += vector8_4block[r+12].eq(vector8_4block_Maxbit)
        self.sync += vector8_4block[0:12].eq(vector8[4])
        # multiplication by cosine
        vector84Aftercos = Signal(2*dw)
        vector84Finalcos = Signal(dw)
        self.sync += vector84Aftercos.eq(cos3pi6*vector8_4block)
        self.sync += vector84Finalcos.eq(vector84Aftercos >> 8)
        # multiplication by sine.
        vector84Aftersin = Signal(2*dw)
        vector84Finalsin = Signal(dw)
        self.sync += vector84Aftersin.eq(sin3pi6*vector8_4block)
        self.sync += vector84Finalsin.eq(vector84Aftersin >> 10)

        vector8_7block = Signal(2*dw)
        vector8_7block_Maxbit = Signal(1)
        self.sync += vector8_7block_Maxbit.eq(vector8[7][11])
        for r in range(12):
            self.sync += vector8_7block[r+12].eq(vector8_7block_Maxbit)
        self.sync += vector8_7block[0:12].eq(vector8[7])
        vector87Aftercos = Signal(2*dw)
        vector87Finalcos = Signal(dw)
        self.sync += vector87Aftercos.eq(cos3pi6*vector8_7block)
        self.sync += vector87Finalcos.eq(vector87Aftercos >> 8)
        vector87Aftersin = Signal(2*dw)
        vector87Finalsin = Signal(dw)
        self.sync += vector87Aftersin.eq(sin3pi6*vector8_4block)
        self.sync += vector87Finalsin.eq(vector84Aftersin >> 10)

        vector8_5block = Signal(2*dw)
        vector8_5block_Maxbit = Signal(1)
        self.sync += vector8_5block_Maxbit.eq(vector8[5][11])
        for r in range(12):
            self.sync += vector8_5block[r+12].eq(vector8_5block_Maxbit)
        self.sync += vector8_5block[0:12].eq(vector8[5])
        vector85Aftercos = Signal(2*dw)
        vector85Finalcos = Signal(dw)
        self.sync += vector85Aftercos.eq(cospi6*vector8_5block)
        self.sync += vector85Finalcos.eq(vector85Aftercos >> 10)
        vector85Aftersin = Signal(2*dw)
        vector85Finalsin = Signal(dw)
        self.sync += vector85Aftersin.eq(sinpi6*vector8_5block)
        self.sync += vector85Finalsin.eq(vector85Aftersin >> 7)

        vector8_6block = Signal(2*dw)
        vector8_6block_Maxbit = Signal(1)
        self.sync += vector8_6block_Maxbit.eq(vector8[6][11])
        for r in range(12):
            self.sync += vector8_6block[r+12].eq(vector8_6block_Maxbit)
        self.sync += vector8_6block[0:12].eq(vector8[6])
        vector86Aftercos = Signal(2*dw)
        vector86Finalcos = Signal(dw)
        self.sync += vector86Aftercos.eq(cospi6*vector8_6block)
        self.sync += vector86Finalcos.eq(vector86Aftercos >> 10)
        vector86Aftersin = Signal(2*dw)
        vector86Finalsin = Signal(dw)
        self.sync += vector86Aftersin.eq(sinpi6*vector8_6block)
        self.sync += vector86Finalsin.eq(vector86Aftersin >> 7)


        self.sync += vector9[4].eq(vector84Finalcos+vector87Finalsin)
        self.sync += vector9[7].eq(vector87Finalcos-vector84Finalcos)
        self.sync += vector9[5].eq(vector85Finalcos+vector86Finalsin)
        self.sync += vector9[6].eq(vector86Finalcos-vector85Finalsin)

            

        #3rd stage

        vector10 = Array(Signal(dw) for a in range(8))

        self.sync += vector10[7].eq(vector9[7]+vector9[5])
        self.sync += vector10[5].eq(vector9[7]-vector9[5])
        self.sync += vector10[4].eq(vector9[4]+vector9[6])
        self.sync += vector10[6].eq(vector9[4]-vector9[6])
        self.sync += vector10[0].eq(vector9[0]+vector9[1])
        self.sync += vector10[1].eq(vector9[0]-vector9[1])

        vector9_2block = Signal(2*dw)
        vector9_2block_Maxbit = Signal(1)
        self.sync += vector9_2block_Maxbit.eq(vector9[2][11])
        for r in range(12):
            self.sync += vector9_2block[r+12].eq(vector9_2block_Maxbit)
        self.sync += vector9_2block[0:12].eq(vector9[2])
        vector92Aftercos = Signal(2*dw)
        vector92Finalcos = Signal(dw)
        self.sync += vector92Aftercos.eq(cos6pi6*vector9_2block)
        self.sync += vector92Finalcos.eq(vector92Aftercos >> 7)
        vector92Aftersin = Signal(2*dw)
        vector92Finalsin = Signal(dw)
        self.sync += vector92Aftersin.eq(sin6pi6*vector9_2block)
        self.sync += vector92Finalsin.eq(vector92Aftersin >> 9)

        vector9_3block = Signal(2*dw)
        vector9_3block_Maxbit = Signal(1)
        self.sync += vector9_3block_Maxbit.eq(vector9[3][11])
        for r in range(12):
            self.sync += vector9_3block[r+12].eq(vector9_3block_Maxbit)
        self.sync += vector9_3block[0:12].eq(vector9[3])
        vector93Aftercos = Signal(2*dw)
        vector93Finalcos = Signal(dw)
        self.sync += vector93Aftercos.eq(cos6pi6*vector9_3block)
        self.sync += vector93Finalcos.eq(vector93Aftercos >> 7)
        vector93Aftersin = Signal(2*dw)
        vector93Finalsin = Signal(dw)
        self.sync += vector93Aftersin.eq(sin6pi6*vector9_3block)
        self.sync += vector93Finalsin.eq(vector93Aftersin >> 9)

        Finaladd = Signal(dw)
        Finalsub = Signal(dw)
        self.sync += Finaladd.eq(vector92Finalcos+vector93Finalsin)
        self.sync += Finalsub.eq(vector93Finalcos-vector92Finalsin)

        vectoradd = Signal(2*dw)
        vectoradd2 = Signal(2*dw)
        sqrtadd = Signal(2*dw)
        # See whwather the number is negative or not.
        Maxbitadd = Signal(1)
        Maxbitadd2 = Signal(1)
        self.sync += Maxbitadd.eq(Finaladd[11])
        self.sync += Maxbitadd2.eq(Finalsub[11])
        for r in range(12):
            self.sync += vectoradd[r+12].eq(Maxbitadd)
            self.sync += vectoradd2[r+12].eq(Maxbitadd2)
        self.sync += vectoradd[0:12].eq(Finaladd)
        self.sync += vectoradd2[0:12].eq(Finalsub)
        self.sync += sqrtadd.eq(181)
        #Doing the Multiplication and dividing by 128
        vectoraddAfter = Signal(2*dw)
        vectoradd2After = Signal(2*dw)
        self.sync += vectoraddAfter.eq(sqrtadd*vectoradd)
        self.sync += vectoradd2After.eq(sqrtadd*vectoradd2)

        self.sync += vector10[2].eq(vectoraddAfter >> 7)
        self.sync += vector10[3].eq(vectoradd2After >> 7)

        #4th stage

        self.sync += vector1d_out[1].eq(vector10[7]+vector10[4])
        self.sync += vector1d_out[7].eq(vector10[7]-vector10[4])

            
        # Create signals for extending the negative numbers
        vector6 = Signal(2*dw)
        sqrt2 = Signal(2*dw)
        # See whwather the number is negative or not.
        TempMaxbit = Signal(1)
        self.sync += TempMaxbit.eq(vector10[6][11])
        for r in range(12):
            self.sync += vector6[r+12].eq(TempMaxbit)
        self.sync += vector6[0:12].eq(vector10[6])
        self.sync += sqrt2.eq(181)
        # Doing the Multiplication and dividing by 128
        vector6After = Signal(2*dw)
        vector6Final = Signal(dw)
        self.sync += vector6After.eq(sqrt2*vector6)
        self.sync += vector6Final.eq(vector6After >> 7)
            
        vector5 = Signal(2*dw)
        TempMaxbit7 = Signal(1)
        self.sync += TempMaxbit7.eq(vector10[5][11])
        for r in range(12):
            self.sync += vector5[r+12].eq(TempMaxbit7)
        self.sync += vector5[0:12].eq(vector10[5])
        vector5After = Signal(2*dw)
        vector5Final = Signal(dw)
        self.sync += vector5After.eq(sqrt2*vector5)
        self.sync += vector5Final.eq(vector5After >> 7)

        self.sync += vector1d_out[5].eq(vector6Final)
        self.sync += vector1d_out[3].eq(vector5Final)
        self.sync += vector1d_out[6].eq(vector10[3])
        self.sync += vector1d_out[2].eq(vector10[2])
        self.sync += vector1d_out[4].eq(vector10[1])
        self.sync += vector1d_out[0].eq(vector10[0])


class DCT(PipelinedActor,Module):
    """
    This will get the input into the DCT module in the form of 64 blocks with 8 bits each.
    The input is taken in the form of serial input. After obtaining all the
    64 inputs from the serial input they are than pass to the DCT module.
    Also after obtaining the 64 blocks from the DCT module, these are 
    transferred to the output in the form of serial data.

    """

    def __init__(self,dw=12, dct_block=64):
        # dw = Determine the size of the blocks
        # dct_block = Determine the number of blocks coming from one frame.

        # Taking the input serial stream and convert it into 64 blocks.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(12)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #


        # Setting the datapath which takes the YCbCr input and give DCT output both
        # in the form of 64 blocks.    
        self.submodules.datapath = DCTDatapath(dw,dct_block)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        

        """
        Stores the data obtained from the serial input into the memory and than put
        into the DCT module. These data than after processing will again obtained
        in the memory and than read from it to get the output.
        """
        data_mem = Memory(12, 64*2)
        data_write_port = data_mem.get_port(write_capable=True)
        self.specials += data_mem, data_write_port

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


        data_mem2 = Memory(12, 64*2)
        data_read_port2 = data_mem2.get_port(async_read=True)
        self.specials += data_mem2, data_read_port2

        

        # read path
        read_clr2 = Signal()
        read_inc2 = Signal()
        read_count2 = Signal(6)
        self.sync += \
            If(read_clr2,
                read_count2.eq(0)
            ).Elif(read_inc2,
                read_count2.eq(read_count2 + 1)
            )

        self.comb += [
            data_read_port2.adr.eq(read_count2), # XXX check latency
            data_read_port2.adr[-1].eq(read_sel),
            source.data.eq(data_read_port2.dat_r)
        ]

        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act("IDLE",
            read_clr2.eq(1),
            If(read_sel == write_sel,
                read_swap.eq(1),
                NextState("READ")
            )
        )
        read_fsm.act("READ",
            source.valid.eq(1),
            source.last.eq(read_count2 == 63),
            If(source.ready,
                read_inc2.eq(1),
                If(source.last,
                    NextState("IDLE")
                )
            )
        )

        #Give the input to the datapath
        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += getattr(self.datapath.sink, name).eq(data_mem[i])

        #Give the output from the datapath
        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += data_mem2[i].eq(getattr(self.datapath.source, name))
