# !/usr/bin/env python3
# This is the module for testing the Huffman Encoder.

from litex.gen import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.huffman.huffmancore import HuffmanEncoder

from common import *

"""
Testbench for the Huffman module.
This module takes a matrix containing 64 blocks of 12 bits each and verifies
the RLECore produces the same output as the reference data.
"""
class TB(Module):
    def __init__(self):
        """
        Making pipeline and the getting the Huffman module.

        Streamer : It will pass the input to the Huffman.
                   The data is a 20 bit number in the matrix.
                   Streamer[0:12] = amplitude
                   Streamer[12:16] = size of the amplitude
                   Streamer[16:20] = runlength

        Logger : It will get the output to the TestBench.
                 The output of the HuffmanEncoder is of 9 bits
                 after the serialization of the input data.
                 8 bits for the data.
                 1 bit to decide wheather the data is valid or not.
                 Logger[0:8] = Output of the HuffmanEncoder
                 Logger[9] = Valid bit

        """
        self.submodules.streamer = PacketStreamer(EndpointDescription([("data", 20)]))
        self.submodules.huffman = HuffmanEncoder()
        self.submodules.logger = PacketLogger(EndpointDescription([("data", 9)]))

        # Connecting TestBench with the Huffman Encoder module.
        self.comb += [
            self.streamer.source.connect(self.huffman.sink),
            self.huffman.source.connect(self.logger.sink)
        ]


def main_generator(dut):

    # Results from the implemented module.
    model2 = Huffman()

    print("Output of the reference module:")
    Reference_model = model2.reference_module(model2.runlength_test_y ,
                            model2.vli_size_test_y,
                            model2.vli_test_y)
    print(Reference_model)

    input_data = model2.concat_input(
                 model2.vli_test_y,
                 model2.vli_size_test_y,
                 model2.runlength_test_y)
    packet = Packet(input_data)
    print("Output of the Huffman Module:")
    for i in range(1):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
        model2.set_data(dut.logger.packet)

# Going through the main module
if __name__ == "__main__":
    tb = TB()
    generators = {"sys" : [main_generator(tb)]}
    generators = {
        "sys" : [
            main_generator(tb),
            tb.streamer.generator(),
            tb.logger.generator()
        ]
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
