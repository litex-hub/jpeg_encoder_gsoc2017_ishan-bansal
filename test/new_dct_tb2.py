from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litejpeg.core.common import *
from litejpeg.core.new_dct6 import *

from common import DCTData

# dw = size of the block in the metrix
# ds = number of blocks in the matrix
dw = 12
ds = 64
# table with 64 values of the form dct_1,dct_2,....,dct_63
omit_table = ["dct_" + str(i) for i in range(ds)]

class TB(Module):
    def __init__(self):

        #attaching input and output of the test bench with that of the DCT module.
        #add brackets to the Endpoint description
        self.submodules.streamer = PacketStreamer(EndpointDescription( [("data", dw)] ))
        self.submodules.DCT = DCT()
        self.submodules.logger = PacketLogger(EndpointDescription( [("data", dw)]))

        self.comb += [
            Record.connect(self.streamer.source, self.DCT.sink, omit=["data"]),
            Record.connect(self.DCT.source, self.logger.sink, omit=["data"]),
         ]

        for j in range(ds):
            name = "dct_" + str(j)
            self.comb += self.DCT.sink.data.eq(self.streamer.source.data[0:dw])
            self.comb += self.logger.sink.data[0:dw].eq(self.DCT.source.data)


def main_generator(dut):

    # DCT module input and output testing
    model =  DCTData(ds,dw)
    print("\n")
    print("Input data to the DCT Module")
    print(model.input_dct)
    print("\n")
    print("Reference output data")
    print(model.output_dct)
    print("\n")
    print("Output data by the DCT Module")
    print(model.output_dct_model) 

    for i in range(8):
        yield

    # Implementation on Hardware.
    model2 = DCTData(ds,dw)
    packet = Packet(model2.input_dct)
    for i in range(3):
        dut.streamer.send(packet)
        yield from dut.logger.receive()
    print("\n")
    print("Output of the DCT Module Implemented:")
    model2.setdata(dut.logger.packet)


if __name__ == "__main__":
    tb = TB()
    generators = {"sys": [main_generator(tb)]}
    generators = {
        "sys": [main_generator(tb),
                tb.streamer.generator(),
                tb.logger.generator()]
    }
    clocks = {"sys": 10}
    run_simulation(tb, generators, clocks, vcd_name="dct.vcd")
