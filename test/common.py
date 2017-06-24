from PIL import Image

import random
from copy import deepcopy

from litex.gen import *
from litex.soc.interconnect.stream import *

from model.enc_frame import dct
from model.enc_frame import zigzag
from model.enc_frame import quantize

class RAWImage:
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
        self.data = []
        for i in range(self.length):
            data = (self.r[i] & 0xff) << 16
            data |= (self.g[i] & 0xff) << 8
            data |= (self.b[i] & 0xff) << 0
            self.data.append(data)
        return self.data


    def pack_ycbcr(self):
        self.data = []
        for i in range(self.length):
            data = (self.y[i] & 0xff) << 16
            data |= (self.cb[i] & 0xff) << 8
            data |= (self.cr[i] & 0xff) << 0
            self.data.append(data)
        return self.data


    def unpack_rgb(self):
        self.r = []
        self.g = []
        self.b = []
        for data in self.data:
            self.r.append((data >> 16) & 0xff)
            self.g.append((data >> 8) & 0xff)
            self.b.append((data >> 0) & 0xff)
        return self.r, self.g, self.b


    def unpack_ycbcr(self):
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
    def __init__(self,ds,dw):
        self.input_dct = [140, 144, 147, 140, 140, 155, 179, 175,
                          144, 152, 140, 147, 140, 148, 167, 179,
                          152, 155, 136, 167, 163, 162, 152, 172,
                          168, 145, 156, 160, 152, 155, 136, 160,
                          162, 148, 156, 148, 140, 136, 147, 162,
                          147, 167, 140, 155, 155, 140, 136, 162,
                          136, 156, 123, 167, 162, 144, 140, 147,
                          148, 155, 136, 155, 152, 147, 147, 136]
        self.output_dct = [186, -18,  15,  -9,   23,  -9, -14, 19,
                            21, -34,  26,  -9,  -11,  11,  14,  7,
                           -10, -24,  -2,   6,  -18,   3, -20, -1,
                            -8,  -5,  14, -15,   -8,  -3,  -3,  8,
                            -3,  10,   8,   1,  -11,  18,  18, 15,
                             4,  -2, -18,   8,    8,  -4,   1, -7,
                             9,   1,  -3,   4,   -1,  -7,  -1, -2,
                             0,  -8,  -2,   2,    1,   4,  -6,  0]
        self.output_dct_model = dct(self.input_dct)
        self.length = ds
        self.width = dw

    def pack_dct(self):
        self.data = []
        for i in range(self.length):
            data = (self.input_dct[i] & 0xff) << self.width*i
            self.data.append(data)
        return self.data[-1]

    def unpack_dct(self,output):
        self.out_data = []
        for i in range( len(output)/self.width ):
            data = (output >> self.width*i) & 2**self.width
            self.out_data.append( data )

    def pack_dct_new(self):
        self.data = 0
        for i in range(self.length):
            data = (self.input_dct[i] & ((2**(self.width))-1)) << self.width*i
            self.data = self.data + data
        return self.data


    def unpack_dct_new(self,output):
        self.out_data = []
        for i in range(self.length):
            data = (output >> self.width*i) & ((2**self.width)-1)
            self.out_data.append( data )
        print(self.out_data)

    def setdata(self,data):
        self.data = data[57:]
        for i in range(64):
            temp = (self.data[i]^4095)+1
            if(temp < self.data[i]):
                self.data[i] = -1*temp;
            #for j in range(12):
            #    self.data[i][j].eq(self.data[i][j]^self.data[i][11])
        print(self.data)

class ZZData:
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
    def __init__(self):
        self.quantizer_input = [-415, -33, -58,  35,  58, -51, -15, -12,
                                   5, -34,  49,  18,  27,  1 , -5 ,   3,
                                 -46,  14,  80, -35, -50,  19,   7, -18,
                                 -53,  21,  34, -20,   2,  34,  36,  12,
                                   9,  -2,   9,  -5, -32, -15,  45,  37,
                                  -8,  15, -16,   7,  -8,  11,   4,   7,
                                  19, -28,  -2, -26,  -2,   7, -44, -21,
                                  18,  25, -12, -44,  35,  48, -37,  -3]

        self.quantizer_table = [16, 11, 10, 16, 24, 40, 51, 61,
                                12, 12, 14, 19, 26, 58, 60, 55,
                                14, 13, 16, 24, 40, 57, 69, 56,
                                14, 17, 22, 29, 51, 87, 80, 62,
                                18, 22, 37, 56, 68,109,103, 77,
                                24, 35, 55, 64, 81,104,113, 92,
                                49, 64, 78, 87,103,121,120,101,
                                72, 92, 95, 98,112,100,103, 99]

        self.quantizer_cr = [17, 18, 24, 47, 99, 99, 99, 99,
                                 18, 21, 26, 66, 99, 99, 99, 99,
                                 24, 26, 56, 99, 99, 99, 99, 99,
                                 47, 66, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99,
                                 99, 99, 99, 99, 99, 99, 99, 99]

        self.quantize_output_ref = quantize(self.quantizer_input,self.quantizer_table)

        self.quantizer_output2_ref = quantize(self.quantizer_input,self.quantizer_cr) 

        self.quantizer_output = [ -26, -3, -6,  2,  2, -1, 0, 0,
                                    0, -3,  4,  1,  1,  0, 0, 0,
                                   -3,  1,  5, -1, -1,  0, 0, 0,
                                   -4,  1,  2, -1,  0,  0, 0, 0,
                                    1,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0,
                                    0,  0,  0,  0,  0,  0, 0, 0]

    def setdata(self,data):
        self.data = data
        for i in range(64):
            temp = (self.data[i]^4095)+1
            if(temp < self.data[i]):
                self.data[i] = -1*temp;
            #for j in range(12):
            #    self.data[i][j].eq(self.data[i][j]^self.data[i][11])
        print(self.data)

            