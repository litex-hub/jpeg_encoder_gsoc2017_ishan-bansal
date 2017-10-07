"""Used to build Huffman Tables"""

import csv


def build_huffman_rom_tables(csvfile):
    """build huffman tables"""
    code = []
    size = []
    with open(csvfile, 'r') as csvfp:
        csvreader = csv.reader(csvfp, delimiter=',')
        for row in csvreader:
            check_comment = str(row[0])
            if(check_comment[0]!='#'):
                code.append(row[0])
                size.append(row[1])

    return code, size
