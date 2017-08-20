COREDIR = ../
PYTHON = python3

CMD = PYTHONPATH=$(COREDIR) $(PYTHON)

all: clean rgb2ycbcr_tb ycbcr2rgb_tb ycbcr_resampling_tb

rgb2ycbcr_tb:
	$(CMD) rgb2ycbcr_tb.py

ycbcr2rgb_tb:
	$(CMD) ycbcr2rgb_tb.py

ycbcr_resampling_tb:
	$(CMD) ycbcr_resampling_tb.py

zigzag_tb:
	$(CMD) zigzag_tb.py

dct_tb:
	$(CMD) dct_tb.py

quantization_tb:
	$(CMD) quantization_tb.py

clean:
	rm -rf *_*.png *.vvp *.v *.vcd

.PHONY: clean