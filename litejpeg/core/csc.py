# Color Space Conversion

from litex.gen import *
from litex.soc.interconnect.stream import *

from litejpeg.core.common import *

""" Conversion of RGB2YCbCr Module
    ==============================

    This module takes the blocks in the form of serial input for 24 bits.
    Each of the 24 bits contains 8 bits for each of R,G and B.
    It undergo a number of mathematical operations on these bits to change them into
    YCbCr. 
    The reason behind this is because the new attributes that are Y,Cb and Cr they have a 
    special property in which the image is not much affected with the change of Cb and Cr
    as compared to in the previous case. Hence a number of different steps were been taken in 
    order that the compression must be maximum.
"""


def rgb2ycbcr_coefs(dw, cw=None):
    # return : The value of various constants required for the modules below.
    return {
        "ca" : coef(0.1819, cw),
        "cb" : coef(0.0618, cw),
        "cc" : coef(0.6495, cw),
        "cd" : coef(0.5512, cw),
        "yoffset" : 2**(dw-4),
        "coffset" : 2**(dw-1),
        "ymax" : 2**dw-1,
        "cmax" : 2**dw-1,
        "ymin" : 0,
        "cmin" : 0
    }


datapath_latency = 8


@CEInserter()
class RGB2YCbCrDatapath(Module):
    """
    Datapath of the RGB2YCbCr Module.
    ---------------------------------
    This module will provide the datapath required for the RGB2YCbcr module.
    Since a number of different multiplication and addition operations are required for the purpose of 
    the conversion of the rgb into ycbcr hence are to be taken in the form of several stages.

    Inputs:
    -------
    r : 8 bit number contains the red gradient of a particular pixel.
    g : 8 bit number contains the green gradient of a particular pixel.
    b : 8 bit number contains the blue gradient of a particular pixel.

    Return:
    -------
    y, cb and cr : each an 8 bit number formed from the r,g and b component obtained as input.

    """
    def __init__(self, rgb_w, ycbcr_w, coef_w):
        self.sink = sink = Record(rgb_layout(rgb_w))
        self.source = source = Record(ycbcr444_layout(ycbcr_w))

        # # #

        coefs = rgb2ycbcr_coefs(ycbcr_w, coef_w)

        # Since the output doesn't come in a single clock cycle. Hence there is a need of
        # providing delay in the output which is determined by datapath_latency of the
        # module and provided as below:
        rgb_delayed = [sink]
        for i in range(datapath_latency):
            rgb_n = Record(rgb_layout(rgb_w))
            for name in ["r", "g", "b"]:
                self.sync += getattr(rgb_n, name).eq(getattr(rgb_delayed[-1], name))
            rgb_delayed.append(rgb_n)

        # Hardware implementation:
        # (Equation from XAPP930)
        # y = ca*(r-g) + g + cb*(b-g) + yoffset
        # cb = cc*(r-y) + coffset
        # cr = cd*(b-y) + coffset

        # stage 1
        # (r-g) & (b-g)
        r_minus_g = Signal((rgb_w + 1, True))
        b_minus_g = Signal((rgb_w + 1, True))
        self.sync += [
            r_minus_g.eq(sink.r - sink.g),
            b_minus_g.eq(sink.b - sink.g)
        ]

        # stage 2
        # ca*(r-g) & cb*(b-g)
        ca_mult_rg = Signal((rgb_w + coef_w + 1, True))
        cb_mult_bg = Signal((rgb_w + coef_w + 1, True))
        self.sync += [
            ca_mult_rg.eq(r_minus_g * coefs["ca"]),
            cb_mult_bg.eq(b_minus_g * coefs["cb"])
        ]

        # stage 3
        # ca*(r-g) + cb*(b-g)
        carg_plus_cbbg = Signal((rgb_w + coef_w + 9, True)) # XXX
        self.sync += [
            carg_plus_cbbg.eq(ca_mult_rg + cb_mult_bg)
        ]

        # stage 4
        # yraw = ca*(r-g) + cb*(b-g) + g
        yraw = Signal((rgb_w + 3, True))
        self.sync += [
            yraw.eq(carg_plus_cbbg[coef_w:] + rgb_delayed[3].g)
        ]

        # stage 5
        # r - yraw
        # b - yraw
        b_minus_yraw = Signal((rgb_w + 4, True))
        r_minus_yraw = Signal((rgb_w + 4, True))
        yraw_r0 = Signal((rgb_w + 3, True))
        self.sync += [
            b_minus_yraw.eq(rgb_delayed[4].b - yraw),
            r_minus_yraw.eq(rgb_delayed[4].r - yraw),
            yraw_r0.eq(yraw)
        ]

        # stage 6
        # cc*yraw
        # cd*yraw
        cc_mult_ryraw = Signal((rgb_w + coef_w + 4, True))
        cd_mult_byraw = Signal((rgb_w + coef_w + 4, True))
        yraw_r1 = Signal((rgb_w + 3, True))
        self.sync += [
            cc_mult_ryraw.eq(b_minus_yraw * coefs["cc"]),
            cd_mult_byraw.eq(r_minus_yraw * coefs["cd"]),
            yraw_r1.eq(yraw_r0)
        ]

        # stage 7
        # y = (yraw + yoffset)
        # cb = (cc*(r - yraw) + coffset)
        # cr = (cd*(b - yraw) + coffset)
        y = Signal((rgb_w + 3, True))
        cb = Signal((rgb_w + 4, True))
        cr = Signal((rgb_w + 4, True))
        self.sync += [
            y.eq(yraw_r1 + coefs["yoffset"]),
            cb.eq(cc_mult_ryraw[coef_w:] + coefs["coffset"]),
            cr.eq(cd_mult_byraw[coef_w:] + coefs["coffset"])
        ]

        # stage 8
        # saturate
        self.sync += [
            saturate(y, source.y, coefs["ymin"], coefs["ymax"]),
            saturate(cb, source.cb, coefs["cmin"], coefs["cmax"]),
            saturate(cr, source.cr, coefs["cmin"], coefs["cmax"])
        ]


class RGB2YCbCr(PipelinedActor, Module):
    """
    Providing the link of the module with that of the input and output.
    -------------------------------------------------------------------
    This will take the input in the form required for the RGB2YCbCr module and 
    recieve the output from the module and convert it in the required format.

    """
    def __init__(self, rgb_w=8, ycbcr_w=8, coef_w=8):

        # Providing the link between the module and input and output.
        self.sink = sink = stream.Endpoint(EndpointDescription(rgb_layout(rgb_w)))
        self.source = source = stream.Endpoint(EndpointDescription(ycbcr444_layout(ycbcr_w)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

    
        # Connecting the datapath with the input and output.
        self.submodules.datapath = RGB2YCbCrDatapath(rgb_w, ycbcr_w, coef_w)
        
        # Providing input and output to the datapath.
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["r", "g", "b"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        for name in ["y", "cb", "cr"]:
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, name))



def ycbcr2rgb_coefs(dw, cw=None):
    # returns the various cofficients required for the module below.
    ca = 0.1819
    cb = 0.0618
    cc = 0.6495
    cd = 0.5512
    xcoef_w = None if cw is None else cw-2
    return {
        "ca" : coef(ca, cw),
        "cb" : coef(cb, cw),
        "cc" : coef(cc, cw),
        "cd" : coef(cd, cw),
        "yoffset" : 2**(dw-4),
        "coffset" : 2**(dw-1),
        "ymax" : 2**dw-1,
        "cmax" : 2**dw-1,
        "ymin" : 0,
        "cmin" : 0,
        "acoef": coef(1/cd, xcoef_w),
        "bcoef": coef(-cb/(cc*(1-ca-cb)), xcoef_w),
        "ccoef": coef(-ca/(cd*(1-ca-cb)), xcoef_w),
        "dcoef": coef(1/cc, xcoef_w)
    }


@CEInserter()
class YCbCr2RGBDatapath(Module):
    """
    Datapath of the YCbCr2RGB Module.
    ---------------------------------
    This module will provide the datapath required for the YCbCr2RGB module.
    Since a number of different multiplication and addition operations are required for the purpose of 
    the conversion of the ycbcr into rgb hence are to be taken in the form of several stages.

    Inputs:
    -------
    y : 8 bit number contains the red gradient of a particular pixel.
    cb : 8 bit number contains the green gradient of a particular pixel.
    cr : 8 bit number contains the blue gradient of a particular pixel.

    Return:
    -------
    r, g and b : each an 8 bit number formed from the r,g and b component obtained as input.

    """
    def __init__(self, ycbcr_w, rgb_w, coef_w):
        self.sink = sink = Record(ycbcr444_layout(ycbcr_w))
        self.source = source = Record(rgb_layout(rgb_w))

        # # #

        coefs = ycbcr2rgb_coefs(rgb_w, coef_w)

        # Since the output doesn't come in a single clock cycle. Hence there is a need of
        # providing delay in the output which is determined by datapath_latency of the
        # module and provided as below:
        ycbcr_delayed = [sink]
        for i in range(datapath_latency):
            ycbcr_n = Record(ycbcr444_layout(ycbcr_w))
            for name in ["y", "cb", "cr"]:
                self.sync += getattr(ycbcr_n, name).eq(getattr(ycbcr_delayed[-1], name))
            ycbcr_delayed.append(ycbcr_n)

        # Hardware implementation:
        # (Equation from XAPP931)
        #  r = y - yoffset + (cr - coffset)*acoef
        #  b = y - yoffset + (cb - coffset)*bcoef + (cr - coffset)*ccoef
        #  g = y - yoffset + (cb - coffset)*dcoef

        # stage 1
        # (cr - coffset) & (cr - coffset)
        cb_minus_coffset = Signal((ycbcr_w + 1, True))
        cr_minus_coffset = Signal((ycbcr_w + 1, True))
        self.sync += [
            cb_minus_coffset.eq(sink.cb - coefs["coffset"]),
            cr_minus_coffset.eq(sink.cr - coefs["coffset"])
        ]

        # stage 2
        # (y - yoffset)
        # (cr - coffset)*acoef
        # (cb - coffset)*bcoef
        # (cr - coffset)*ccoef
        # (cb - coffset)*dcoef
        y_minus_yoffset = Signal((ycbcr_w + 1, True))
        cr_minus_coffset_mult_acoef = Signal((ycbcr_w + coef_w + 4, True))
        cb_minus_coffset_mult_bcoef = Signal((ycbcr_w + coef_w + 4, True))
        cr_minus_coffset_mult_ccoef = Signal((ycbcr_w + coef_w + 4, True))
        cb_minus_coffset_mult_dcoef = Signal((ycbcr_w + coef_w + 4, True))
        self.sync += [
            y_minus_yoffset.eq(ycbcr_delayed[1].y - coefs["yoffset"]),
            cr_minus_coffset_mult_acoef.eq(cr_minus_coffset * coefs["acoef"]),
            cb_minus_coffset_mult_bcoef.eq(cb_minus_coffset * coefs["bcoef"]),
            cr_minus_coffset_mult_ccoef.eq(cr_minus_coffset * coefs["ccoef"]),
            cb_minus_coffset_mult_dcoef.eq(cb_minus_coffset * coefs["dcoef"])
        ]

        # stage 3
        # line addition for all component
        r = Signal((ycbcr_w + 4, True))
        g = Signal((ycbcr_w + 4, True))
        b = Signal((ycbcr_w + 4, True))
        self.sync += [
            r.eq(y_minus_yoffset + cr_minus_coffset_mult_acoef[coef_w-2:]),
            g.eq(y_minus_yoffset + cb_minus_coffset_mult_bcoef[coef_w-2:] + cr_minus_coffset_mult_ccoef[coef_w-2:]),
            b.eq(y_minus_yoffset + cb_minus_coffset_mult_dcoef[coef_w-2:])
        ]

        # stage 4
        # saturate
        self.sync += [
            saturate(r, source.r, 0, 2**rgb_w-1),
            saturate(g, source.g, 0, 2**rgb_w-1),
            saturate(b, source.b, 0, 2**rgb_w-1)
        ]


class YCbCr2RGB(PipelinedActor, Module):
    """
    Providing the link of the module with that of the input and output.
    -------------------------------------------------------------------
    This will take the input in the form required for the YCbCr2RGB module and 
    recieve the output from the module and convert it in the required format.

    """
    def __init__(self, ycbcr_w=8, rgb_w=8, coef_w=8):
        
        # Providing the link between the module and input and output.
        self.sink = sink = stream.Endpoint(EndpointDescription(ycbcr444_layout(ycbcr_w)))
        self.source = source = stream.Endpoint(EndpointDescription(rgb_layout(rgb_w)))
        PipelinedActor.__init__(self, datapath_latency)
        self.latency = datapath_latency

        # # #

        # Connecting the datapath with the input and output.
        self.submodules.datapath = YCbCr2RGBDatapath(ycbcr_w, rgb_w, coef_w)

        # Providing input and output to the datapath.
        self.comb += self.datapath.ce.eq(self.pipe_ce)
        for name in ["y", "cb", "cr"]:
            self.comb += getattr(self.datapath.sink, name).eq(getattr(sink, name))
        for name in ["r", "g", "b"]:
            self.comb += getattr(source, name).eq(getattr(self.datapath.source, name))
