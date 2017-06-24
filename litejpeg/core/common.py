from litex.gen import *
from litex.soc.interconnect import stream

def saturate(i, o, minimum, maximum):
    return [
        If(i > maximum,
            o.eq(maximum)
        ).Elif(i < minimum,
            o.eq(minimum)
        ).Else(
            o.eq(i)
        )
    ]


def coef(value, cw=None):
    return int(value * 2**cw) if cw is not None else value


def rgb_layout(dw):
    return [("r", dw), ("g", dw), ("b", dw)]


def ycbcr444_layout(dw):
    return [("y", dw), ("cb", dw), ("cr", dw)]

def ycbcr422_layout(dw):
    return [("y", dw), ("cb_cr", dw)]

def dct_block_layout(dw,ds):
    return [("dct_"+str(i), dw) for i in range(ds)]


def block_layout(dw):
    return [("data", dw)]

pi      = 3.14159265358979323846
sqrt2   = 1.41421356237309504880
sqrt1_2 = 0.70710678118654752440
