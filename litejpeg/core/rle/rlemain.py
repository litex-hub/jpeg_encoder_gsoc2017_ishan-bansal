"""
RLEMain:
---------
This module is responsible for dividing the input within the RLEcore and
the Entrophycoder module. The results are than combined and given
to the output.
"""

from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *

from litejpeg.core.rle.entropycoder import EntropyCoder
from litejpeg.core.rle.rlecore import RunLength


# To keep the output in sync with the input.
# Addition of a delay of 3 clock cycles.
datapath_latency = 3


class RLEMain(PipelinedActor, Module):
    """
    RLEMain :
    ---------
    This is responsible for combining the outputs of both the EntropyCoder and
    RLE core as the output will contain the amplitude in the last 12 bits along
    with the number of bits to store the amplitude as the next 4 bits and
    finally the RunLength for the next 4 bits.
    All these information is been synchronized once by the RLEmain and than
    given as an output to the next module.

    Attributes :
    ------------
    sink : 12 bits
           Receives the information from the previous module.
    source : 21 bits
             Transfer the information to the next module.
             12 bits : amplitude
             4 bits : size
             4 bits : runlength
             1 bit : data_valid
    """
    def __init__(self):
        self.sink = sink = stream.Endpoint(
                               EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(
                                   EndpointDescription(block_layout(21)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        self.submodules.rlecore = RunLength()
        self.submodules.entropycoder = EntropyCoder()

        self.comb += [
            # Connecting RLEcore with the test bench.

            # Transmitting data with the RLEcore.
            self.rlecore.sink.data.eq(self.sink.data),
            # Recieving data from the RLE core.
            self.source.data[0:12].eq(self.rlecore.source.data[0:12]),
            self.source.data[16:21].eq(self.rlecore.source.data[12:17]),
            # Synchronizing the Ready and Valid signals.
            self.rlecore.sink.valid.eq(self.sink.valid),
            self.rlecore.source.valid.eq(self.source.valid),
            self.rlecore.sink.ready.eq(self.sink.ready),
            self.rlecore.source.ready.eq(self.source.ready),

            # Transmitting data with the Entrohycoder.
            self.entropycoder.sink.data.eq(self.sink.data),
            # Recieve data from the Entrophycoder.
            self.source.data[12:16].eq(self.entropycoder.source.data[0:4]),
            # Synchronizing the Ready and Valid signals.
            self.entropycoder.sink.valid.eq(self.sink.valid),
            self.entropycoder.source.valid.eq(self.source.valid),
            self.entropycoder.sink.ready.eq(self.sink.ready),
            self.entropycoder.source.ready.eq(self.source.ready)
        ]
