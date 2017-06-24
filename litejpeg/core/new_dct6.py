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

    def __init__(self, dw, dct_block):
        
        #Record the input and the output of the Datapath.
        # input = Sink.
        # output = Source. 
        self.sink = sink = Record(dct_block_layout(dw,dct_block))
        self.source = source = Record(dct_block_layout(dw,dct_block))

         # # #

        dct_matrix_1d = Array(Array(Signal(dw) for a in range(8)) for b in range(8))
        #dct_matrix_2d = Array(Array(Signal(dw) for a in range(8)) for b in range(8))

        #intialise the vectors for 8 blocks at a time that will undergo DCT processing
        #at a time.
        vector0 = Array(Signal(dw) for a in range(8))
        vector1 = Array(Signal(dw) for a in range(8))
        vector2 = Array(Signal(dw) for a in range(8))
        vector3 = Array(Signal(dw) for a in range(8))
        vector4 = Array(Signal(dw) for a in range(8))
        vector5 = Array(Signal(dw) for a in range(8))
        vector6 = Array(Signal(dw) for a in range(8))
        vector7 = Array(Signal(dw) for a in range(8))

        vector_out = Array(Signal(dw) for a in range(64))
        vector2_out = Array(Signal(dw) for a in range(64))
        vector2final_out = Array(Signal(dw) for a in range(64))
        vector2final_outdivide = Array(Signal(dw) for a in range(64))
        
        #providing delay within a Datapath.
        dct_delayed = [sink]
        for i in range(datapath_latency):
            dct_n = Record(dct_block_layout(dw,dct_block))
            for k in range(dct_block):
                name = "dct_" + str(k)
                self.sync += getattr(dct_n, name).eq(getattr(dct_delayed[-1], name))
            dct_delayed.append(dct_n)
            

            #assigning vectors 8 blocks for which the DCT conversion has to take place.
        for j in range(8):
            name="dct_"+str(j)
            self.sync += vector0[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(8+j)
            self.sync += vector1[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(16+j)
            self.sync += vector2[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(24+j)
            self.sync += vector3[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(32+j)
            self.sync += vector4[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(40+j)
            self.sync += vector5[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(48+j)
            self.sync += vector6[j].eq(getattr(dct_delayed[-1],name)-128)
            name="dct_"+str(54+j)
            self.sync += vector7[j].eq(getattr(dct_delayed[-1],name)-128)
                

            # assign DCT to every block to get the result.
        self.dct1D(vector0,dw,vector_out[0:8])
        self.dct1D(vector1,dw,vector_out[8:16])
        self.dct1D(vector2,dw,vector_out[16:24])
        self.dct1D(vector3,dw,vector_out[24:32])
        self.dct1D(vector4,dw,vector_out[32:40])
        self.dct1D(vector5,dw,vector_out[40:48])
        self.dct1D(vector6,dw,vector_out[48:56])
        self.dct1D(vector7,dw,vector_out[56:64])

            # Now intialising the vectors for applying the DCT function on the transpose matrix.
        vector2_0 = Array(Signal(dw) for a in range(8))
        vector2_1 = Array(Signal(dw) for a in range(8))
        vector2_2 = Array(Signal(dw) for a in range(8))
        vector2_3 = Array(Signal(dw) for a in range(8))
        vector2_4 = Array(Signal(dw) for a in range(8))
        vector2_5 = Array(Signal(dw) for a in range(8))
        vector2_6 = Array(Signal(dw) for a in range(8))
        vector2_7 = Array(Signal(dw) for a in range(8))

            # Assigning values for DCT on the transpose matrix.
        for a in range(8):
            self.sync += vector2_0[a].eq(vector_out[8*a])
            self.sync += vector2_1[a].eq(vector_out[(8*a)+1])
            self.sync += vector2_2[a].eq(vector_out[(8*a)+2])
            self.sync += vector2_3[a].eq(vector_out[(8*a)+3])
            self.sync += vector2_4[a].eq(vector_out[(8*a)+4])
            self.sync += vector2_5[a].eq(vector_out[(8*a)+5])
            self.sync += vector2_6[a].eq(vector_out[(8*a)+6])
            self.sync += vector2_7[a].eq(vector_out[(8*a)+7])

        self.dct1D(vector2_0,dw,vector2_out[0:8])
        self.dct1D(vector2_1,dw,vector2_out[8:16])
        self.dct1D(vector2_2,dw,vector2_out[16:24])
        self.dct1D(vector2_3,dw,vector2_out[24:32])
        self.dct1D(vector2_4,dw,vector2_out[32:40])
        self.dct1D(vector2_5,dw,vector2_out[40:48])
        self.dct1D(vector2_6,dw,vector2_out[48:56])
        self.dct1D(vector2_7,dw,vector2_out[56:64])

            # Assigning the result to the final matrix.
        for p in range(8):
            self.sync += vector2final_out[8*p].eq(vector2_out[p])
            self.sync += vector2final_out[8*p+1].eq(vector2_out[p+8])
            self.sync += vector2final_out[8*p+2].eq(vector2_out[p+16])
            self.sync += vector2final_out[8*p+3].eq(vector2_out[p+24])
            self.sync += vector2final_out[8*p+4].eq(vector2_out[p+32])
            self.sync += vector2final_out[8*p+5].eq(vector2_out[p+40])
            self.sync += vector2final_out[8*p+6].eq(vector2_out[p+48])
            self.sync += vector2final_out[8*p+7].eq(vector2_out[p+56])

            # Dividing the resultant matrix by 8.
        for r in range(64):
            self.sync += vector2final_outdivide[r].eq(vector2final_out[r]>>3)
            self.sync += vector2final_outdivide[r][9].eq(vector2final_outdivide[r][8])
            self.sync += vector2final_outdivide[r][10].eq(vector2final_outdivide[r][8])
            self.sync += vector2final_outdivide[r][11].eq(vector2final_outdivide[r][8])

            # Assigning the final matrix to the output.
        for m in range(64):
            name = "dct_"+str(m)
            self.sync += getattr(source, name).eq(vector2final_outdivide[m])
        
            

        #print(len(sink))
 

    def dct1D(self,vector1d,dw,vector1d_out):

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

            #Since Migen doesn't take negative values therefore in order to multiply
            #our outputs with sin and cosine we will first multiply the value of the 
            #cosine and sine with the power of 2 and get the output and do the product.
            #Then then divide the resultant by the power of 2 by right shifting.

        cospi6 = Signal(2*dw)
        self.sync += cospi6.eq(1004)    #1024
        cos3pi6 = Signal(2*dw)
        self.sync += cos3pi6.eq(213)    #256
        cos6pi6 = Signal(2*dw)
        self.sync += cos6pi6.eq(49)     #128
        sinpi6 = Signal(2*dw)
        self.sync += sinpi6.eq(25)      #128
        sin3pi6 = Signal(2*dw)
        self.sync += sin3pi6.eq(569)    #1024
        sin6pi6 = Signal(2*dw)
        self.sync += sin6pi6.eq(473)    #512

            #multiplication by cosine and sine
            
        Tempvector84 = Signal(2*dw)
            #bit extension by deciding wheather the most significant bit is 1 or 0 
        Tempbit1 = Signal(1)
        self.sync += Tempbit1.eq(vector8[4][11])
        for r in range(12):
            self.sync += Tempvector84[r+12].eq(Tempbit1)
        self.sync += Tempvector84[0:12].eq(vector8[4])
            #multiplication by cosine
        Tempvector84Aftercos = Signal(2*dw)
        Tempvector84Finalcos = Signal(dw)
        self.sync += Tempvector84Aftercos.eq(cos3pi6*Tempvector84)
        self.sync += Tempvector84Finalcos.eq(Tempvector84Aftercos >> 8)
            #multiplication by sine.
        Tempvector84Aftersin = Signal(2*dw)
        Tempvector84Finalsin = Signal(dw)
        self.sync += Tempvector84Aftersin.eq(sin3pi6*Tempvector84)
        self.sync += Tempvector84Finalsin.eq(Tempvector84Aftersin >> 10)

        Tempvector87 = Signal(2*dw)
        Tempbit2 = Signal(1)
        self.sync += Tempbit2.eq(vector8[7][11])
        for r in range(12):
            self.sync += Tempvector87[r+12].eq(Tempbit2)
        self.sync += Tempvector87[0:12].eq(vector8[7])
        Tempvector87Aftercos = Signal(2*dw)
        Tempvector87Finalcos = Signal(dw)
        self.sync += Tempvector87Aftercos.eq(cos3pi6*Tempvector87)
        self.sync += Tempvector87Finalcos.eq(Tempvector87Aftercos >> 8)
        Tempvector87Aftersin = Signal(2*dw)
        Tempvector87Finalsin = Signal(dw)
        self.sync += Tempvector87Aftersin.eq(sin3pi6*Tempvector84)
        self.sync += Tempvector87Finalsin.eq(Tempvector84Aftersin >> 10)

        Tempvector85 = Signal(2*dw)
        Tempbit3 = Signal(1)
        self.sync += Tempbit3.eq(vector8[5][11])
        for r in range(12):
            self.sync += Tempvector85[r+12].eq(Tempbit3)
        self.sync += Tempvector85[0:12].eq(vector8[5])
        Tempvector85Aftercos = Signal(2*dw)
        Tempvector85Finalcos = Signal(dw)
        self.sync += Tempvector85Aftercos.eq(cospi6*Tempvector85)
        self.sync += Tempvector85Finalcos.eq(Tempvector85Aftercos >> 10)
        Tempvector85Aftersin = Signal(2*dw)
        Tempvector85Finalsin = Signal(dw)
        self.sync += Tempvector85Aftersin.eq(sinpi6*Tempvector85)
        self.sync += Tempvector85Finalsin.eq(Tempvector85Aftersin >> 7)

        Tempvector86 = Signal(2*dw)
        Tempbit4 = Signal(1)
        self.sync += Tempbit4.eq(vector8[6][11])
        for r in range(12):
            self.sync += Tempvector86[r+12].eq(Tempbit4)
        self.sync += Tempvector86[0:12].eq(vector8[6])
        Tempvector86Aftercos = Signal(2*dw)
        Tempvector86Finalcos = Signal(dw)
        self.sync += Tempvector86Aftercos.eq(cospi6*Tempvector86)
        self.sync += Tempvector86Finalcos.eq(Tempvector86Aftercos >> 10)
        Tempvector86Aftersin = Signal(2*dw)
        Tempvector86Finalsin = Signal(dw)
        self.sync += Tempvector86Aftersin.eq(sinpi6*Tempvector86)
        self.sync += Tempvector86Finalsin.eq(Tempvector86Aftersin >> 7)


        self.sync += vector9[4].eq(Tempvector84Finalcos+Tempvector87Finalsin)
        self.sync += vector9[7].eq(Tempvector87Finalcos-Tempvector84Finalcos)
        self.sync += vector9[5].eq(Tempvector85Finalcos+Tempvector86Finalsin)
        self.sync += vector9[6].eq(Tempvector86Finalcos-Tempvector85Finalsin)

            

            #3rd stage

        vector10 = Array(Signal(dw) for a in range(8))

        self.sync += vector10[7].eq(vector9[7]+vector9[5])
        self.sync += vector10[5].eq(vector9[7]-vector9[5])
        self.sync += vector10[4].eq(vector9[4]+vector9[6])
        self.sync += vector10[6].eq(vector9[4]-vector9[6])
        self.sync += vector10[0].eq(vector9[0]+vector9[1])
        self.sync += vector10[1].eq(vector9[0]-vector9[1])

        Tempvector92 = Signal(2*dw)
        Tempbit5 = Signal(1)
        self.sync += Tempbit5.eq(vector9[2][11])
        for r in range(12):
            self.sync += Tempvector92[r+12].eq(Tempbit5)
        self.sync += Tempvector92[0:12].eq(vector9[2])
        Tempvector92Aftercos = Signal(2*dw)
        Tempvector92Finalcos = Signal(dw)
        self.sync += Tempvector92Aftercos.eq(cos6pi6*Tempvector92)
        self.sync += Tempvector92Finalcos.eq(Tempvector92Aftercos >> 7)
        Tempvector92Aftersin = Signal(2*dw)
        Tempvector92Finalsin = Signal(dw)
        self.sync += Tempvector92Aftersin.eq(sin6pi6*Tempvector92)
        self.sync += Tempvector92Finalsin.eq(Tempvector92Aftersin >> 9)

        Tempvector93 = Signal(2*dw)
        Tempbit6 = Signal(1)
        self.sync += Tempbit6.eq(vector9[3][11])
        for r in range(12):
            self.sync += Tempvector93[r+12].eq(Tempbit6)
        self.sync += Tempvector93[0:12].eq(vector9[3])
        Tempvector93Aftercos = Signal(2*dw)
        Tempvector93Finalcos = Signal(dw)
        self.sync += Tempvector93Aftercos.eq(cos6pi6*Tempvector93)
        self.sync += Tempvector93Finalcos.eq(Tempvector93Aftercos >> 7)
        Tempvector93Aftersin = Signal(2*dw)
        Tempvector93Finalsin = Signal(dw)
        self.sync += Tempvector93Aftersin.eq(sin6pi6*Tempvector93)
        self.sync += Tempvector93Finalsin.eq(Tempvector93Aftersin >> 9)

        Finaladd = Signal(dw)
        Finalsub = Signal(dw)
        self.sync += Finaladd.eq(Tempvector92Finalcos+Tempvector93Finalsin)
        self.sync += Finalsub.eq(Tempvector93Finalcos-Tempvector92Finalsin)

        Tempvectoradd = Signal(2*dw)
        Tempvectoradd2 = Signal(2*dw)
        Tempsqrtadd = Signal(2*dw)
            # See whwather the number is negative or not.
        TempMaxbitadd = Signal(1)
        TempMaxbitadd2 = Signal(1)
        self.sync += TempMaxbitadd.eq(Finaladd[11])
        self.sync += TempMaxbitadd2.eq(Finalsub[11])
        for r in range(12):
            self.sync += Tempvectoradd[r+12].eq(TempMaxbitadd)
            self.sync += Tempvectoradd2[r+12].eq(TempMaxbitadd2)
        self.sync += Tempvectoradd[0:12].eq(Finaladd)
        self.sync += Tempvectoradd2[0:12].eq(Finalsub)
        self.sync += Tempsqrtadd.eq(181)
            #Doing the Multiplication and dividing by 128
        TempvectoraddAfter = Signal(2*dw)
        Tempvectoradd2After = Signal(2*dw)
        self.sync += TempvectoraddAfter.eq(Tempsqrtadd*Tempvectoradd)
        self.sync += Tempvectoradd2After.eq(Tempsqrtadd*Tempvectoradd2)

        self.sync += vector10[2].eq(TempvectoraddAfter >> 7)
        self.sync += vector10[3].eq(Tempvectoradd2After >> 7)

            #4th stage

        #vector11 = Array(Signal(dw) for a in range(8))

        self.sync += vector1d_out[1].eq(vector10[7]+vector10[4])
        self.sync += vector1d_out[7].eq(vector10[7]-vector10[4])

            
            # Create signals for extending the negative numbers
        Tempvector6 = Signal(2*dw)
        Tempsqrt2 = Signal(2*dw)
            # See whwather the number is negative or not.
        TempMaxbit = Signal(1)
        self.sync += TempMaxbit.eq(vector10[6][11])
        for r in range(12):
            self.sync += Tempvector6[r+12].eq(TempMaxbit)
        self.sync += Tempvector6[0:12].eq(vector10[6])
        self.sync += Tempsqrt2.eq(181)
            #Doing the Multiplication and dividing by 128
        Tempvector6After = Signal(2*dw)
        Tempvector6Final = Signal(dw)
        self.sync += Tempvector6After.eq(Tempsqrt2*Tempvector6)
        self.sync += Tempvector6Final.eq(Tempvector6After >> 7)
            
        Tempvector5 = Signal(2*dw)
        TempMaxbit7 = Signal(1)
        self.sync += TempMaxbit7.eq(vector10[5][11])
        for r in range(12):
            self.sync += Tempvector5[r+12].eq(TempMaxbit7)
        self.sync += Tempvector5[0:12].eq(vector10[5])
        Tempvector5After = Signal(2*dw)
        Tempvector5Final = Signal(dw)
        self.sync += Tempvector5After.eq(Tempsqrt2*Tempvector5)
        self.sync += Tempvector5Final.eq(Tempvector5After >> 7)

        self.sync += vector1d_out[5].eq(Tempvector6Final)
        self.sync += vector1d_out[3].eq(Tempvector5Final)
        self.sync += vector1d_out[6].eq(vector10[3])
        self.sync += vector1d_out[2].eq(vector10[2])
        self.sync += vector1d_out[4].eq(vector10[1])
        self.sync += vector1d_out[0].eq(vector10[0])


class DCT(PipelinedActor,Module):

    def __init__(self,dw=12, dct_block=64):
        # dw = Determine the size of the blocks
        # dct_block = Determine the number of blocks coming from one frame.

        #Taking the input serial stream and convert it into 64 blocks.
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(12)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #


        #Setting the datapath which takes the YCbCr input and give DCT output both
        #in the form of 64 blocks
        
        self.submodules.datapath = DCTDatapath(dw,dct_block)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        

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

        #self.comb +=
        #Give the input to the datapath
        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += getattr(self.datapath.sink, name).eq(data_mem[i])

        #Give the output from the datapath
        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += data_mem2[i].eq(getattr(self.datapath.source, name))
