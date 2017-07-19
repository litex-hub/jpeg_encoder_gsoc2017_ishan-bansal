from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *

from litejpeg.core.rle.entropycoder import Entropycoder
from litejpeg.core.rle.rlecore import Runlength

datapath_latency = 3
class RLEmain(PipelinedActor,Module):
    def __init__(self):
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(21)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        self.submodules.rlecore = Runlength()
        self.submodules.entropycoder = Entropycoder()

        self.comb += [
        self.rlecore.sink.data.eq(self.sink.data),
        self.source.data[0:12].eq(self.rlecore.source.data[0:12]),
        self.source.data[16:21].eq(self.rlecore.source.data[12:17]),
        self.rlecore.sink.valid.eq(self.sink.valid),
        self.rlecore.source.valid.eq(self.source.valid),
        self.rlecore.sink.ready.eq(self.sink.ready),
        self.rlecore.source.ready.eq(self.source.ready),

        self.entropycoder.sink.data.eq(self.sink.data),
        self.source.data[12:16].eq(self.entropycoder.source.data[0:4]),
        self.entropycoder.sink.valid.eq(self.sink.valid),
        self.entropycoder.source.valid.eq(self.source.valid),
        self.entropycoder.sink.ready.eq(self.sink.ready),
        self.entropycoder.source.ready.eq(self.source.ready)
        ]
