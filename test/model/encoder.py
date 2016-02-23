import math

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
    r  = [0 for i in range(64)]
    for i, (value, divider) in enumerate(zip(block, table)):
        r[i] = int(value/divider)
    return r

from reference import *

print("rgb2ycbcr")
print("="*40)
y_block, cb_block, cr_block = rgb2ycbcr(r444_16x8_blocks[0], 
	                                    g444_16x8_blocks[0], 
	                                    b444_16x8_blocks[0])
print(y_block)
print(y444_16x8_blocks[0])
print(cb_block)
print(cb444_16x8_blocks[0])
print(cr_block)
print(cr444_16x8_blocks[0])

print("dct")
print("="*40)
print(dct(y422_16x8_blocks[0]))
print(y422_dct_16x8_block[0])
print(dct(cb422_16x8_block))
print(cb422_dct_16x8_block)

print("quantization")
print("="*40)
print(quantize(cb422_dct_16x8_block, cbcr_quant_table))
print(cb422_qwant_16x8_block)
print(quantize(cr422_dct_16x8_block, cbcr_quant_table))
print(cr422_qwant_16x8_block)