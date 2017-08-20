from PIL import Image
import numpy as np
from itertools import groupby,chain
import math

def readRgbImageBlocks(name):
    arr = np.array(Image.open(name))
    r = arr[...,0]
    g = arr[...,1]
    b = arr[...,2]
    img_width  = len(r[0])
    img_height = len(r)
    block_size = int(img_width / 8) * int(img_height / 8)
    r_blocks = [[] for x in range(block_size)]
    g_blocks = [[] for x in range(block_size)]
    b_blocks = [[] for x in range(block_size)]

    for i in range(img_height):
        for j in range(img_width):
            block_number = int(i/8)*int(img_width/8)+int(j/8)
            r_blocks[block_number].append(r[i,j])
            g_blocks[block_number].append(g[i, j])
            b_blocks[block_number].append(b[i, j])
    return (r_blocks,g_blocks,b_blocks)


def rgb2ycbcr(r_block, g_block, b_block):
    y_block  = [0]*64
    cb_block = [0]*64
    cr_block = [0]*64
    for i, (r, g, b) in enumerate(zip(r_block, g_block, b_block)):
        y_block[i]  = int(0.299*r + 0.587*g + 0.114*b)
        cb_block[i] = int(-0.1687*r - 0.3313*g + 0.5*b + 128)
        cr_block[i] = int(0.5*r - 0.4187*g - 0.0813*b + 128)
    return y_block, cb_block, cr_block


pi      = 3.14159265358979323846
sqrt2   = 1.41421356237309504880
sqrt1_2 = 0.70710678118654752440

def dct_rotation(i0, i1, k, n):
    cos = math.cos((n*pi)/16)
    sin = math.sin((n*pi)/16)
    out0 = k*(i0*cos + i1*sin)
    out1 = k*(i1*cos - i0*sin)
    return out0, out1

def dct_butterfly(i0, i1):
    out0 = i0 + i1
    out1 = i0 - i1
    return out0, out1

def dct_1d(vector):
    r = [0]*8

    # stage 1
    vector[3], vector[4] = dct_butterfly(vector[3], vector[4])
    vector[2], vector[5] = dct_butterfly(vector[2], vector[5])
    vector[1], vector[6] = dct_butterfly(vector[1], vector[6])
    vector[0], vector[7] = dct_butterfly(vector[0], vector[7])

    # stage 2
    vector[0], vector[3] = dct_butterfly(vector[0], vector[3])
    vector[1], vector[2] = dct_butterfly(vector[1], vector[2])
    vector[4], vector[7] = dct_rotation(vector[4], vector[7], 1, 3)
    vector[5], vector[6] = dct_rotation(vector[5], vector[6], 1, 1)

    # stage 3
    vector[7], vector[5] = dct_butterfly(vector[7], vector[5])
    vector[4], vector[6] = dct_butterfly(vector[4], vector[6])
    vector[0], vector[1] = dct_butterfly(vector[0], vector[1])
    vector[2], vector[3] = dct_rotation(vector[2], vector[3], sqrt2, 6)

    # stage 4
    r[1], r[7] = dct_butterfly(vector[7], vector[4])
    r[5] = sqrt2 * vector[6]
    r[3] = sqrt2 * vector[5]
    r[6] = vector[3]
    r[2] = vector[2]
    r[4] = vector[1]
    r[0] = vector[0]

    return r

def dct(block):
    vector = [0]*8
    matrix = [0]*64
    dct_block = [0]*64

    # apply dct_1d on the matrix's lines
    for x in range(8):
        for y in range(8):
            vector[y] = block[x*8 + y] - 128
        #print("Start\n")
        #print(vector)
        #rint("end\n")
        vector = dct_1d(vector)
        for y in range(8):
            matrix[x*8 + y] = vector[y]

    # apply dct_1d on its transposition's lines
    for y in range(8):
        for x in range(8):
            vector[x] = matrix[x*8 + y]
        vector = dct_1d(vector)
        for x in range(8):
            dct_block[x*8 + y] = int(vector[x]/8)
    return dct_block

def quantize(block, table):
    r  = [0]*64
    for i, (value, divider) in enumerate(zip(block, table)):
        r[i] = (value/divider)
        temp = value/divider
        if(value >= 0):
            temp = temp - math.ceil(temp)+1
            if(temp >= 0.5):
                r[i]=math.ceil(r[i])
            else:
                r[i]=math.ceil(r[i])-1
        else:
            temp = math.ceil(temp) - temp
            if(temp >= 0.5):
                r[i]=math.ceil(r[i])-1
            else:
                r[i]=math.ceil(r[i])

    return r

zig_zag_order = [
 0,  1,  5,  6, 14, 15, 27, 28,
 2,  4,  7, 13, 16, 26, 29, 42,
 3,  8, 12, 17, 25, 30, 41, 43,
 9, 11, 18, 24, 31, 40, 44, 53,
10, 19, 23, 32, 39, 45, 52, 54,
20, 22, 33, 38, 46, 51, 55, 60,
21, 34, 37, 47, 50, 56, 59, 61,
35, 36, 48, 49, 57, 58, 62, 63]

y_quant_table = [
0x05, 0x03, 0x03, 0x05, 0x07, 0x0c, 0x0f, 0x12,
0x04, 0x04, 0x04, 0x06, 0x08, 0x11, 0x12, 0x11,
0x04, 0x04, 0x05, 0x07, 0x0c, 0x11, 0x15, 0x11,
0x04, 0x05, 0x07, 0x09, 0x0f, 0x1a, 0x18, 0x13,
0x05, 0x07, 0x0b, 0x11, 0x14, 0x21, 0x1f, 0x17,
0x07, 0x0b, 0x11, 0x13, 0x18, 0x1f, 0x22, 0x1c,
0x0f, 0x13, 0x17, 0x1a, 0x1f, 0x24, 0x24, 0x1e,
0x16, 0x1c, 0x1d, 0x1d, 0x22, 0x1e, 0x1f, 0x1e]

cbcr_quant_table = [
0x05, 0x05, 0x07, 0x0e, 0x1e, 0x1e, 0x1e, 0x1e,
0x05, 0x06, 0x08, 0x14, 0x1e, 0x1e, 0x1e, 0x1e,
0x07, 0x08, 0x11, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x0e, 0x14, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e]

def zigzag(block):
    r = [0]*64
    for i in range(64):
        r[zig_zag_order[i]] = block[i]
    return r

#def rle_code(block):
#    entropy = []
#    count = 0
#    for i in block:
#        if()

#    return entropy

def rle_code(block):
    return list(chain(*[(symbol,len(list(g))) for symbol, g in groupby(block)]))


def huffman(block):
    return block


if __name__ == '__main__':
    (r88_blocks,g88_blocks,b88_blocks) = readRgbImageBlocks("24x24.bmp")
    height = 24
    width = 24
    blocks_number = len(r88_blocks)

    fileJpeg = open("modelGenerated" + ".jpeg", "wb")
    jpegHeaderAPP0      = [0xFF,0xD8,0xFF,0xE0,0x00,0x10,'J','F','I','F', 1,1,0,1,1,0,0]
    jpegHeaderDQTy      = [0xFF,0xDB]+  int(len(y_quant_table)+3) + [0x01] + y_quant_table
    jpegHeaderDQTcbcr   = [0xFF, 0xDB] + int(len(cbcr_quant_table) + 3) + [0x01] + cbcr_quant_table
    jpegHeaderSOF0      = [0xFF, 0xc0, 17,8,64,64,3,12,2,0,2,1,1,1,3,1,1,1]
    jpegHeaderDHT       = [0xFF, 0xC4, len(HuffmanTable)+3,0,0]
    jpegHeaderDATA      = [0xFF, 0xDA, 12, 3,0x01,0x00,0x02,Ss,Se,AhAi]
    'Here goes image bytes'
    jpegHeaderEnd = [0xFF, 0xD9]
    header = jpegHeaderAPP0 + jpegHeaderDQTy + jpegHeaderDQTcbcr + jpegHeaderSOF0 + jpegHeaderDHT + jpegHeaderDATA
    bytesToAdd = bytearray(header)
    fileJpeg.write(bytesToAdd)

    (dcy_prev,dccb_prev,dccr_prev) = (0,0,0)
    for i in range(blocks_number):
        y_block, cb_block, cr_block = rgb2ycbcr(r88_blocks[i],g88_blocks[i],b88_blocks[i])
        y_dct_block   = dct(y_block)
        cb_dct_block  = dct(cb_block)
        cr_dct_block  = dct(cr_block)
        y_quant_block = quantize(y_dct_block, y_quant_table)
        cb_quant_block =quantize(cb_dct_block, cbcr_quant_table)
        cr_quant_block =quantize(cr_dct_block, cbcr_quant_table)
        y_zig  = zigzag(y_quant_block)
        cb_zig = zigzag(cb_quant_block)
        cr_zig = zigzag(cr_quant_block)

        ac_y_zig = y_zig[1:]
        ac_cb_zig = cb_zig[1:]
        ac_cr_zig = cr_zig[1:]

        #DC differences
        dc_y_zig = y_zig[0] - dcy_prev
        dcy_prev = y_zig[0]
        y_zig[0] = dc_y_zig

        dc_cb_zig = cb_zig[0] - dccb_prev
        dccb_prev = cb_zig[0]
        cb_zig[0] = dc_cb_zig

        dc_cr_zig = cr_zig[0] - dccr_prev
        dccr_prev = cr_zig[0]
        cr_zig[0] = dc_cr_zig

        y_rle  = rle_code(y_zig)
        cb_rle = rle_code(cb_zig)
        cr_rle = rle_code(cr_zig)

        huffman(y_rle)
        huffman(cb_rle)
        huffman(cr_rle)



