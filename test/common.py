from PIL import Image

import random
from copy import deepcopy

from litex.gen import *
from litex.soc.interconnect.stream import *

from model.enc_frame import dct
from model.enc_frame import zigzag
from model.enc_frame import quantize
from model.enc_frame import rle_code

class RAWImage:
    """
    This class particular used for the RGB2YCbCr module as for dividing the image into
    64*64 pixels and getting the values of R, G and B corressponding to each pixel.
    Than converting the RCG matrix into the YCbCr matrix which are further 
    used for the compression.
    Than again converting the YCbCr to RGB matrix to again convert the new image with
    the original image.

    """
    def __init__(self, coefs, filename=None, size=None):
        self.r = None
        self.g = None
        self.b = None

        self.y = None
        self.cb = None
        self.cr = None

        self.data = []

        self.coefs = coefs
        self.size = size
        self.length = None

        if filename is not None:
            self.open(filename)


    def open(self, filename):
        """
        Storing values in the r, g and b matrix.
        """
        img = Image.open(filename)
        if self.size is not None:
            img = img.resize((self.size, self.size), Image.ANTIALIAS)
        r, g, b = zip(*list(img.getdata()))
        self.set_rgb(r, g, b)


    def save(self, filename):
        img = Image.new("RGB" ,(self.size, self.size))
        img.putdata(list(zip(self.r, self.g, self.b)))
        img.save(filename)


    def set_rgb(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b
        self.length = len(r)


    def set_ycbcr(self, y, cb, cr):
        self.y = y
        self.cb = cb
        self.cr = cr
        self.length = len(y)


    def set_data(self, data):
        self.data = data


    def pack_rgb(self):
        """
        Converting the RGB into the data for the transfer into the 
        RGB2YCbCr module.
        """
        self.data = []
        for i in range(self.length):
            data = (self.r[i] & 0xff) << 16
            data |= (self.g[i] & 0xff) << 8
            data |= (self.b[i] & 0xff) << 0
            self.data.append(data)
        return self.data


    def pack_ycbcr(self):
        """
        Converting the YCbCr into the data for the transfer into the
        YCbCr2RGB module.
        """
        self.data = []
        for i in range(self.length):
            data = (self.y[i] & 0xff) << 16
            data |= (self.cb[i] & 0xff) << 8
            data |= (self.cr[i] & 0xff) << 0
            self.data.append(data)
        return self.data


    def unpack_rgb(self):
        """
        Converting the data into the RGB matrix.
        """
        self.r = []
        self.g = []
        self.b = []
        for data in self.data:
            self.r.append((data >> 16) & 0xff)
            self.g.append((data >> 8) & 0xff)
            self.b.append((data >> 0) & 0xff)
        return self.r, self.g, self.b


    def unpack_ycbcr(self):
        """ Converting the data into the YCbCr matrix"""
        self.y = []
        self.cb = []
        self.cr = []
        for data in self.data:
            self.y.append((data >> 16) & 0xff)
            self.cb.append((data >> 8) & 0xff)
            self.cr.append((data >> 0) & 0xff)
        return self.y, self.cb, self.cr


    # Model for our implementation
    def rgb2ycbcr_model(self):
        self.y  = []
        self.cb = []
        self.cr = []
        for r, g, b in zip(self.r, self.g, self.b):
            yraw = self.coefs["ca"]*(r-g) + self.coefs["cb"]*(b-g) + g
            self.y.append(int(yraw + self.coefs["yoffset"]))
            self.cb.append(int(self.coefs["cc"]*(b-yraw) + self.coefs["coffset"]))
            self.cr.append(int(self.coefs["cd"]*(r-yraw) + self.coefs["coffset"]))
        return self.y, self.cb, self.cr


    # Wikipedia implementation used as reference
    def rgb2ycbcr(self):
        self.y = []
        self.cb = []
        self.cr = []
        for r, g, b in zip(self.r, self.g, self.b):
            self.y.append(int(0.299*r + 0.587*g + 0.114*b))
            self.cb.append(int(-0.1687*r - 0.3313*g + 0.5*b + 128))
            self.cr.append(int(0.5*r - 0.4187*g - 0.0813*b + 128))
        return self.y, self.cb, self.cr


    # Model for our implementation
    def ycbcr2rgb_model(self):
        self.r = []
        self.g = []
        self.b = []
        for y, cb, cr in zip(self.y, self.cb, self.cr):
            self.r.append(int(y - self.coefs["yoffset"] + (cr - self.coefs["coffset"])*self.coefs["acoef"]))
            self.g.append(int(y - self.coefs["yoffset"] + (cb - self.coefs["coffset"])*self.coefs["bcoef"] + (cr - self.coefs["coffset"])*self.coefs["ccoef"]))
            self.b.append(int(y - self.coefs["yoffset"] + (cb - self.coefs["coffset"])*self.coefs["dcoef"]))
        return self.r, self.g, self.b


    # Wikipedia implementation used as reference
    def ycbcr2rgb(self):
        self.r = []
        self.g = []
        self.b = []
        for y, cb, cr in zip(self.y, self.cb, self.cr):
            self.r.append(int(y + (cr - 128) *  1.402))
            self.g.append(int(y + (cb - 128) * -0.34414 + (cr - 128) * -0.71414))
            self.b.append(int(y + (cb - 128) *  1.772))
        return self.r, self.g, self.b

class DCTData:
    """
    This class is been made for the testing of the DCT module. As for this 
    purpose the input and expected output of the DCT matrix are been taken from 
    the reference as follows:
    "http://www.iosrjournals.org/iosr-jece/papers/Vol5-Issue4/H0545156.pdf?id=4310"
    and the same input is given to the reference and the implemented module and
    the output is compared with that of the expected output for checking the accuracy
    of the implemented module.

    Parameters:
    -----------
    ds : int
    Determine the number of blocks in the matrix.

    dw : int
    Determine the number of bits required to store individual value.

    """
    def __init__(self,ds,dw):

        # Reference input
        self.input_dct = [140, 144, 147, 140, 140, 155, 179, 175,
                          144, 152, 140, 147, 140, 148, 167, 179,
                          152, 155, 136, 167, 163, 162, 152, 172,
                          168, 145, 156, 160, 152, 155, 136, 160,
                          162, 148, 156, 148, 140, 136, 147, 162,
                          147, 167, 140, 155, 155, 140, 136, 162,
                          136, 156, 123, 167, 162, 144, 140, 147,
                          148, 155, 136, 155, 152, 147, 147, 136]
        
        # Expected output
        self.output_dct = [186, -18,  15,  -9,   23,  -9, -14, 19,
                            21, -34,  26,  -9,  -11,  11,  14,  7,
                           -10, -24,  -2,   6,  -18,   3, -20, -1,
                            -8,  -5,  14, -15,   -8,  -3,  -3,  8,
                            -3,  10,   8,   1,  -11,  18,  18, 15,
                             4,  -2, -18,   8,    8,  -4,   1, -7,
                             9,   1,  -3,   4,   -1,  -7,  -1, -2,
                             0,  -8,  -2,   2,    1,   4,  -6,  0]
        
        # Output after passing the input to the reference module.
        self.output_dct_model = dct(self.input_dct)
        
        self.length = ds
        self.width = dw

    # Converting DCT matrix into the serial data for providing input to
    # the DCT module.
    def pack_dct(self):
        self.data = []
        for i in range(self.length):
            data = (self.input_dct[i] & 0xff) << self.width*i
            self.data.append(data)
        return self.data[-1]

    # Taking input from the output of the DCT module and convert it into
    # the DCT matrix.
    def unpack_dct(self,output):
        self.out_data = []
        for i in range( len(output)/self.width ):
            data = (output >> self.width*i) & 2**self.width
            self.out_data.append( data )

    # Converting DCT matrix into the serial data for providing input to
    # the DCT module.
    def pack_dct_new(self):
        self.data = 0
        for i in range(self.length):
            data = (self.input_dct[i] & ((2**(self.width))-1)) << self.width*i
            self.data = self.data + data
        return self.data


    # Taking input from the output of the DCT module and convert it into
    # the DCT matrix.
    def unpack_dct_new(self,output):
        self.out_data = []
        for i in range(self.length):
            data = (output >> self.width*i) & ((2**self.width)-1)
            self.out_data.append( data )
        print(self.out_data)

    # Set the data in the required format for the printing.
    def setdata(self,data):
        self.data = data[57:]
        for i in range(64):
            temp = (self.data[i]^4095)+1
            if(temp < self.data[i]):
                self.data[i] = -1*temp;
        print(self.data)

class ZZData:
    """
    In order for the testing purpose ``zigzag_input`` input is been taken
    to check the functionality of the implemented module by comparing the 
    results which we get from both the reference and the implemented
    module.
    """
    def __init__(self):
        self.zigzag_input=[140, 144, 147, 140, 140, 155, 179, 175,
                     144, 152, 140, 147, 140, 148, 167, 179,
                     152, 155, 136, 167, 163, 162, 152, 172,
                     168, 145, 156, 160, 152, 155, 136, 160,
                     162, 148, 156, 148, 140, 136, 147, 162,
                     147, 167, 140, 155, 155, 140, 136, 162,
                     136, 156, 123, 167, 162, 144, 140, 147,
                     148, 155, 136, 155, 152, 147, 147, 136]

        self.zigzag_output = zigzag(self.zigzag_input)

class Quantizer:
    """
    The Quantization table for this purpose are taken from the reference as follows:
    "https://www.dfrws.org/sites/default/files/session-files/
    paper-using_jpeg_quantization_tables_to_identify_imagery_processed_by_software.pdf"
    which includes the one for the luminance and other for the chrominium, since the
    eye are less sensible for the chrominium part, hence contains large values in the 
    case of chrominium table which generate more number of zeros in the chrominium part
    for the purpose of maximum compression without much effect in the quality of the 
    image.

    ``quantizer_input`` is taken as a reference for testing the implemented module from
    ``wikipedia`` along with the expected output i.e. ``qunatizer_output`` for comparing
    with the result we get from the reference and implemented modules.

    """
    def __init__(self):
        # Input to the quantization table.
        self.quantizer_input = [-415, -33, -58,  35,  58, -51, -15, -12,
                                   5, -34,  49,  18,  27,  1 , -5 ,   3,
                                 -46,  14,  80, -35, -50,  19,   7, -18,
                                 -53,  21,  34, -20,   2,  34,  36,  12,
                                   9,  -2,   9,  -5, -32, -15,  45,  37,
                                  -8,  15, -16,   7,  -8,  11,   4,   7,
                                  19, -28,  -2, -26,  -2,   7, -44, -21,
                                  18,  25, -12, -44,  35,  48, -37,  -3]

        # Luminance quantization table.
        self.quantizer_table = [16, 11, 10, 16, 24, 40, 51, 61,
                                12, 12, 14, 19, 26, 58, 60, 55,
                                14, 13, 16, 24, 40, 57, 69, 56,
                                14, 17, 22, 29, 51, 87, 80, 62,
                                18, 22, 37, 56, 68,109,103, 77,
                                24, 35, 55, 64, 81,104,113, 92,
                                49, 64, 78, 87,103,121,120,101,
                                72, 92, 95, 98,112,100,103, 99]

        # Chrominium quantization table.
        self.quantizer_cr = [17, 18, 24, 47, 99, 99, 99, 99,
                                 18, 21, 26, 66, 99, 99, 99, 99,
                                 24, 26, 56, 99, 99, 99, 99, 99,
                                 47, 66, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99]

        # Output getting after the quantization module.
        self.quantize_output_ref = quantize(self.quantizer_input,self.quantizer_table)

        self.quantizer_output2_ref = quantize(self.quantizer_input,self.quantizer_cr) 

        # Expected output.
        self.quantizer_output = [ -26, -3, -6,  2,  2, -1, 0, 0,
                                    0, -3,  4,  1,  1,  0, 0, 0,
                                   -3,  1,  5, -1, -1,  0, 0, 0,
                                   -4,  1,  2, -1,  0,  0, 0, 0,
                                    1,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0]

    def setdata(self,data):
        # Converting the data from the Quantization module into the prescibed
        # format.
        self.data = data
        for i in range(64):
            temp = (self.data[i]^4095)+1
            if(temp < self.data[i]):
                self.data[i] = -1*temp;
        print(self.data)


class RLE:
    """
    These class is been created in order to store the value or the matrix which
    are been used to test the RLE module.
    The matrix are from github repositories for the purpose of input for
    testing.
    """
    def __init__(self):
        self.red_pixels_1 = [
                        1, 12, 0,  0, 0, 0, 0, 0,
                        0,  0, 0,  0, 0, 0, 0, 0,
                        0,  0, 0, 10, 2, 3, 4, 0, 
                        0,  0, 0,  0, 0, 0, 0, 0,
                        0,  0, 0,  0, 0, 0, 0, 0, 
                        0,  0, 0,  0, 0, 0, 0, 0,
                        0,  0, 0,  0, 0, 0, 0, 0,
                        0,  0, 0,  0, 1, 0, 0, 0
                       ]
 

        red_pixels_2 = [
                        0, 12, 20,  0,  0,   2,   3,  4,
                        0, 0,  2,  3,  4,   5,   1,  0,
                        0,  0,  0,  0,  0,   0,  90,  0, 
                        0,  0,  0, 10,  0,   0,   0,  9,
                        1,  1,  1,  1,  2,   3,   4,  5, 
                        1,  2,  3,  4,  1,   2,   0,  0,
                        0,  0,  0,  0,  0,   0,   0,  0,
                        0,  0,  0,  0,  0,   0,   0,  0
                       ] 

        green_pixels_1 = [
                          11, 12, 0,  0, 0, 0, 0, 0,
                           0,  0, 0,  0, 0, 0, 0, 0,
                           0,  0, 0, 10, 2, 3, 4, 0, 
                           0,  0, 0,  0, 1, 0, 0, 0,
                           0,  0, 1,  1, 2, 3, 4, 5, 
                           1,  2, 3,  4, 1, 2, 0, 0,
                           0,  0, 0,  0, 0, 0, 0, 0,
                           0,  0, 0,  0, 1, 0, 0, 0
                         ] 

        green_pixels_2 = [
                          13, 12, 20,  0,  0,   0,   0,  0,
                           0,  0,  0,  0,  0,   0,   0,  0,
                           0,  0,  0,  0,  0,   0,   0,  0, 
                           0,  0,  0,  0,  0,   0,   0,  0,
                           0,  0,  0,  0,  0,   0,   0,  0, 
                           0,  0,  0,  0,  0,   0,   0,  0,
                           0,  0,  0,  0,  0,   0,   0,  1,
                           1,  0,  0,  0,  1,  32,   4,  2
                          ]

        blue_pixels_1 = [
                         11, 12, 0,  0, 0, 0, 0, 0,
                          0,  0, 0,  0, 0, 0, 0, 0,
                          0,  0, 0,  0, 0, 0, 0, 0, 
                          0,  0, 0,  0, 0, 0, 0, 0,
                          0,  0, 0,  1, 2, 3, 4, 5, 
                          1,  2, 3,  4, 1, 2, 0, 0,
                          0,  0, 0,  0, 0, 0, 0, 0,
                          0,  0, 0,  0, 0, 0, 0, 1
                        ] 

        blue_pixels_2 = [
                         16, 12, 20,  0,  0,   2,   3,  4,
                          0,  0,  2,  3,  4,   5,   1,  0,
                          0,  0,  0,  0,  0,   0,  90,  0, 
                          0,  0,  0, 10,  0,   0,   0,  9,
                          1,  1,  1,  1,  2,   3,   4,  5, 
                          1,  2,  3,  4,  1,   2,   0,  1,
                          1,  0,  0,  0,  0,   0,   0,  1,
                          1,  0,  0,  0,  1,  32,   4,  2
                        ]
        # Get the output from the reference module.
        self.output_red_pixels_1 = rle_code(self.red_pixels_1);                

    def setdata(self,data):
        self.data = data
        for i in range(64):
            temp=self.data[i]
            Amplitude = temp%4096
            runlength = temp >> 12
            print("%s,%s"%(Amplitude,runlength))



            