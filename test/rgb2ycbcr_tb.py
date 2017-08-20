from litex.gen import *
from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.csc import rgb2ycbcr_coefs, RGB2YCbCr

from common import *

"""
This module is made for the testing of the RGB2YCbCr module. For this purpose
an image is taken and divided into 64*64 blocks extracting RGB for each pixel.
Than the RGB is than converted into YCbCr matrix and than the matrix again
converted into RGB matrix and than the image is again constructed and compared
with the original image to check the correctness for the module.

"""

class TB(Module):
    def __init__(self):
        # Making pipeline for getting RGB2YCbCr module.
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 24)]))
        self.submodules.rgb2ycbcr = RGB2YCbCr()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 24)]))

        # Combining test bench with the RGB2YCbCr module.
        self.comb += [
        	Record.connect(self.streamer.source, self.rgb2ycbcr.sink, omit=["data"]),
            self.rgb2ycbcr.sink.payload.r.eq(self.streamer.source.data[16:24]),
            self.rgb2ycbcr.sink.payload.g.eq(self.streamer.source.data[8:16]),
            self.rgb2ycbcr.sink.payload.b.eq(self.streamer.source.data[0:8]),

            Record.connect(self.rgb2ycbcr.source, self.logger.sink, omit=["y", "cb", "cr"]),
            self.logger.sink.data[16:24].eq(self.rgb2ycbcr.source.y),
            self.logger.sink.data[8:16].eq(self.rgb2ycbcr.source.cb),
            self.logger.sink.data[0:8].eq(self.rgb2ycbcr.source.cr)
        ]


def main_generator(dut):
    # convert image using rgb2ycbcr model
    raw_image = RAWImage(rgb2ycbcr_coefs(8), "lena.png", 64)
    raw_image.rgb2ycbcr_model()
    raw_image.ycbcr2rgb()
    raw_image.save("lena_rgb2ycbcr_reference.png")

    for i in range(16):
        yield

    # convert image using rgb2ycbcr implementation
    raw_image = RAWImage(rgb2ycbcr_coefs(8), "lena.png", 64)
    raw_image.pack_rgb()
    packet = Packet(raw_image.data)
    dut.streamer.send(packet)
    yield from dut.logger.receive()
    raw_image.set_data(dut.logger.packet)
    raw_image.unpack_ycbcr()
    raw_image.ycbcr2rgb()
    raw_image.save("lena_rgb2ycbcr.png")

if __name__ == "__main__":
    tb = TB()
    generators = {"sys" : [main_generator(tb)]}
    generators = {
        "sys" :   [main_generator(tb),
                   tb.streamer.generator(),
                   tb.logger.generator()]
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
