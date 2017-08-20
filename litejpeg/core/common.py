from litex.gen import *
from litex.soc.interconnect import stream

""" 
Preferred formats for Input and Output
======================================


Parameters:
-----------
dw : int
    Indicates the number of blocks to be created for each of the name as per the module.

These modules contains the format for the input and output of different modules
from their respective Test Benches. This includes :

rgb_layout :
            This will create dw number of blocks for name ``r``, ``g`` and ``b`` used in the ``RGB2YCbCr`` module.

ycbcr444_layout:
            This will create dw number of blocks for name ``y``, ``cb`` and ``cr`` used in the ``RGB2YCbCr`` module.

ycbcr422_layout:
            This will create dw number of blocks for name ``y`` and ``cb_cr`` used in the ``YCbCr_Sampling`` module.

dct_block_layout:
            This will create dw number of blocks with name ``"dct_"+str(i)`` where i ranges from 0 to ds. 
            used in the ``DCT`` module.

block_layout:
            This will create ``dw`` with the name 'data' used in the ``DCT`` module.



Saturation of the values in the output of a module.
===================================================

Parameter:
----------
i : int
   Gives the number which comes as an output of the module.

minimum : int
   Gives the minimum value possible for the output.

maximum : int
   Gives the maximum value possible for the output.

o : int
   Gets the updated value of the output.

These modules are for preventing the output from being overflown. This includes:

saturate :
           This module takes the input as ``i`` and compare it with the ``minimum`` and ``maximum`` ouput that 
           ``i`` can take and than if the value of the ``i`` doesn't lie in the specified range hence this 
           function will saturate the value of ``i`` as either ``minimum`` or ``maximum`` depending on the ``i`` and 
           give the output as ``o``.



Returning the cofficients depending on the  Parameters:
=======================================================

Parameter:
----------

value : int
        Decide the value of the output.

cw : int
     Decide the value of the output.

return : int 
         This will return a value depending on the value of the parameters as ( value* 2**cw )

"""

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
