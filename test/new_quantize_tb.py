# !/usr/bin/env python3
from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.quantization import Quantization

from common import *

# Testbanch for the Quantizer module.
class TB(Module): 
    def __init__(self):
        # Making pipeline and the getting the quantizer module.
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 12)]))
        self.submodules.quantizer = Quantization()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 12)]))

        # Connecting test bench with the quantizer module.
        self.comb += [
            self.streamer.source.connect(self.quantizer.sink),
            self.quantizer.source.connect(self.logger.sink) 
        ]


def main_generator(dut):
    
    # Results from the reference modules:
    model = Quantizer()
    print("The Input Module:")
    print(model.quantizer_input)
    print("\n")
    print("Expected output:")
    print(model.quantizer_output)
    print("\n")
    print("Output of the quatizer module taken:")
    print(model.quantize_output_ref)

    # Results from the implemented module.
    model2 = Quantizer()
    packet = Packet(model2.quantizer_input)
    for i in range(1):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        print("\n")
        print("Output of the quatizer module:")
        model2.setdata(dut.logger.packet)

# Going through the main module
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