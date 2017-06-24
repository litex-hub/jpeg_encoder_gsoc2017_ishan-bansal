# DCT
import math

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

class DCTRotation(Module):
    def __init__(self, i0, i1, o0, o1, k, n):
        cos = int(math.cos((n*pi)/16))
        sin = int(math.sin((n*pi)/16))
        # XXX check & optimize
        self.sync += [
            o0.eq(k*(i0*cos + i1*sin)),
            o1.eq(k*(i1*cos - i0*sin))
        ]

class DCTButterfly(Module):
    def __init__(self, i0, i1, o0, o1):
         # XXX check & optimize
        self.sync += [
            o0.eq(i0 + i1),
            o1.eq(i0 - i1)
        ]

class DCT1D(Module):
    def __init__(self, vector, result):

        # stage 1
        s1_vector = Array([Signal(12) for i in range(8)])
        self.submodules += [
            DCTButterfly(vector[3], vector[4], s1_vector[3], s1_vector[4]),
            DCTButterfly(vector[2], vector[5], s1_vector[2], s1_vector[5]),
            DCTButterfly(vector[1], vector[6], s1_vector[1], s1_vector[6]),
            DCTButterfly(vector[0], vector[7], s1_vector[0], s1_vector[7]),
        ]

        # stage 2
        s2_vector = Array([Signal(12) for i in range(8)])
        self.submodules += [
            DCTButterfly(s1_vector[0], s1_vector[3], s2_vector[0], s2_vector[3]),
            DCTButterfly(s1_vector[1], s1_vector[2], s2_vector[1], s2_vector[2]),
            DCTRotation(s1_vector[4], s1_vector[7], s2_vector[4], s2_vector[7], 1, 3),
            DCTRotation(s1_vector[5], s1_vector[6], s2_vector[5], s2_vector[6], 1, 1),
        ]

        # stage 3
        s3_vector = Array([Signal(12) for i in range(8)])
        self.submodules += [
            DCTButterfly(s2_vector[7], s2_vector[5], s3_vector[7], s3_vector[5]),
            DCTButterfly(s2_vector[4], s2_vector[6], s3_vector[4], s3_vector[6]),
            DCTButterfly(s2_vector[0], s2_vector[1], s3_vector[0], s3_vector[1]),
            DCTRotation(s2_vector[2], s2_vector[3], s3_vector[2], s3_vector[3], sqrt2, 6), # XXX sqrt2
        ]

        # stage 4
        self.submodules += [
            DCTButterfly(s3_vector[7], s3_vector[4], result[1], result[7])
        ]
        self.sync += [
            result[5].eq(sqrt2 * s3_vector[6]),  # XXX sqrt2
            result[3].eq(sqrt2 * s3_vector[5]),  # XXX sqrt2
            result[6].eq(s3_vector[3]),
            result[2].eq(s3_vector[2]),
            result[4].eq(s3_vector[1]),
            result[0].eq(s3_vector[0])
        ]
datapath_latency = 4

@CEInserter()
class DCTDatapath(Module):
    def __init__(self, dw, dct_block):
        self.sink = sink = Record(dct_block_layout(dw,dct_block))
        self.source = source = Record(dct_block_layout(dw,dct_block))

         # # #

        dct_matrix_1d = Array(Array(Signal(dw) for a in range(8)) for b in range(8))
        dct_matrix_2d = Array(Array(Signal(dw) for a in range(8)) for b in range(8))
        dct_delayed = [sink]
        for i in range(datapath_latency):
            dct_n = Record(dct_block_layout(dw,dct_block))
            for i in range(dct_block):
                name = "dct_" + str(i)
                self.sync += getattr(dct_n, name).eq(getattr(dct_delayed[-1], name))
            dct_delayed.append(dct_n)




class DCT(PipelinedActor,Module):
    def __init__(self,dw=12, dct_block=64):
        self.sink = sink = stream.Endpoint(EndpointDescription(dct_block_layout(dw,dct_block)))
        self.source = source = stream.Endpoint(EndpointDescription(dct_block_layout(dw,dct_block)))
        PipelinedActor.__init__(self, datapath_latency)

        # # #


        self.submodules.datapath = DCTDatapath(dw,dct_block)
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        #self.comb +=

        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))

        for i in range(dct_block):
            name = "dct_" + str(i)
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, name))
