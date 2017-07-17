from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *

from litejpeg.core.rle.entrophycoder import Entrophycoder
from litejpeg.core.rle.rlecore import Runlength

datapath_latency = 3
class RLEmain(PipelinedActor,Module):
    def __init__(self):
        self.sink = sink = stream.Endpoint(EndpointDescription(block_layout(12)))
        self.source = source = stream.Endpoint(EndpointDescription(block_layout(22)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        self.submodules.rlecore = Runlength()
        self.submodules.entrophycoder = Entrophycoder()

        self.comb += [
        self.rlecore.sink.data.eq(self.sink.data),
        self.source.data[0:18].eq(self.rlecore.source.data[0:18]),
        self.rlecore.sink.valid.eq(self.sink.valid),
        self.rlecore.source.valid.eq(self.source.valid),
        self.rlecore.sink.ready.eq(self.sink.ready),
        self.rlecore.source.ready.eq(self.source.ready),

        self.entrophycoder.sink.data.eq(self.sink.data),
        self.source.data[18:22].eq(self.entrophycoder.source.data[0:4]),
        self.entrophycoder.sink.valid.eq(self.sink.valid),
        self.entrophycoder.source.valid.eq(self.source.valid),
        self.entrophycoder.sink.ready.eq(self.sink.ready),
        self.entrophycoder.source.ready.eq(self.source.ready)
        ]
