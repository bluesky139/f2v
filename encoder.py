import os
import io
import math
import json
import time
import numpy
import struct
import binascii
import textwrap
from PIL import Image, ImageDraw, ImageFont
from common import *
from file_reader import *

class Encoder(object):
    def __init__(self, filepath):
        self.input_filepath = filepath
        self.crc = 0

    @property
    def input_filename(self):
        return os.path.basename(self.input_filepath)

    @property
    def output_filepath(self):
        return self.input_filepath + '.mkv'

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    def encode(self):
        create_tmp_dir()
        self.prepare()
        self.generate_1st_frame()
        self.generate_main_frames()
        self.add_original_file_info_to_1st_frame()
        self.correct_mkv_header()
        self.end()
        delete_tmp_dir()

    def prepare(self):
        if os.path.exists(self.output_filepath_tmp):
            os.remove(self.output_filepath_tmp)
        if os.path.exists(self.output_filepath):
            os.remove(self.output_filepath)
        
        if os.path.isdir(self.input_filepath):
            self.f_input = OriginalFolderReader(self.input_filepath)
        else:
            self.f_input = OriginalFileReader(self.input_filepath)
        self.frame_count = math.ceil(self.f_input.total_size / BMP_BODY_LEN) + 1
        self.f_output = open(self.output_filepath_tmp, 'wb+')

        # Read whole mkv header (EBML head and Segment(Seek head, Segment information and Tracks)) to output, we'll change duration, date, etc later.
        with open('mkv_header', 'rb') as f:
            mkv_header = f.read()
            self.f_output.write(mkv_header)

    def correct_mkv_header(self):
        # Segment size
        self.f_output.seek(0, io.SEEK_END)
        size = self.f_output.tell() - 0x2C - 8
        print('Segment size:', size)
        self.f_output.seek(0x2C, io.SEEK_SET)
        self.f_output.write((size | 0x100000000000000).to_bytes(8, byteorder='big'))

        # Segment information
        # Duration
        self.f_output.seek(0xB4, io.SEEK_SET)
        duration = float(40 * self.frame_count)
        print('Duration:', duration)
        self.f_output.write(struct.pack('>f', duration))

        # DateUTC
        self.f_output.seek(3, io.SEEK_CUR)
        t = (int(time.time()) - 978307200) * 1000000000  # 978307200 is 2001/01/01 00:00:00 UTC
        self.f_output.write(t.to_bytes(8, byteorder='big'))

        # SegmentUID
        self.f_output.seek(3, io.SEEK_CUR)
        self.f_output.write(numpy.random.bytes(16))

        # Track
        # TrackUID
        self.f_output.seek(0xE3, io.SEEK_SET)
        self.f_output.write(numpy.random.bytes(8))

    def new_cluster(self, frame_pos):
        self.f_output.write(b'\x1F\x43\xB6\x75') # ID "Cluster"
        self.f_output.write(b'\x2A\x8C\x0D') # Cluster size, 640 * 360 * 3 + 13
        self.f_output.write(b'\xE7') # ID "Timecode"
        self.f_output.write(b'\x83') # Timecode size
        self.f_output.write((frame_pos * 40).to_bytes(3, byteorder='big')) # Timecode
        self.f_output.write(b'\xA3') # ID "SimpleBlock"
        self.f_output.write(b'\x2A\x8C\x04') # SimpleBlock size
        self.f_output.write(b'\x81\x00\x00\x00') # SimpleBlock header

    # First frame is for original file info and title thumbnail
    def generate_1st_frame(self):
        filename = 'img00001.bmp'
        filepath = TMP_DIR + '/' + filename
        print('Generating', filename)

        # Create empty bmp.
        with open('bmp_header_{0}p'.format(VIDEO_HEIGHT), 'rb') as f:
            bmp_header = f.read(54)
        with open(filepath, 'wb') as f:
            f.write(bmp_header)
            f.write(bytearray(BMP_BODY_LEN))

        # Draw f2v mark on top left.
        image = Image.open(filepath)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("msyh.ttf", 35)
        draw.rectangle([(0, 0), (140, 45)], fill=(75, 100, 171, 255))
        draw.text((10, 0), 'f2v (v{0})'.format(int.from_bytes(CODE_VERSION, byteorder='big')), fill=(255, 255, 255, 255), font=font)

        # Draw title.
        lines = textwrap.wrap(self.input_filename, width=17)
        y = 50
        for line in lines:
            width, height = font.getsize(line)
            draw.text((10, y), line, fill=(255, 255, 255, 255), font=font)
            y = y + height
        image.save(filepath)

        # Put 1st frame into output.
        # Original file info will be added here later.
        with open(filepath, 'rb') as f:
            f.seek(54)
            old_frame = f.read()

            frame = bytearray()
            while old_frame: # bmp is up side down
                line = old_frame[-VIDEO_WIDTH * 3:]
                frame.extend(line)
                old_frame = old_frame[:-VIDEO_WIDTH * 3]

            self.new_cluster(0)
            self.f_output.write(frame)
            
    def add_original_file_info_to_1st_frame(self):
        # Add file info.
        self.f_output.seek(os.path.getsize('mkv_header') + 20)
        self.f_output.write(b'f2v') # f2v mark
        self.f_output.write(CODE_VERSION) # Version.

        info_size_pos = self.f_output.tell()
        self.f_output.seek(4, io.SEEK_CUR)
        
        input_filesize = self.f_input.total_size
        print('Input file size:', input_filesize)
        if input_filesize > 1024 * 1024 * 1024 * 10:
            raise Exception('Input file size too big.')
        self.f_output.write(input_filesize.to_bytes(5, byteorder='big')) # File size.

        print('CRC:', self.crc)
        self.f_output.write(self.crc.to_bytes(4, byteorder='big')) # CRC

        is_dir = os.path.isdir(self.input_filepath)
        print('Is dir:', is_dir)
        self.f_output.write(b'\x01' if is_dir else b'\x00')

        if is_dir:
            j_file_list = json.dumps(self.f_input.file_list)
            print('File list len:', len(self.f_input.file_list))
            self.f_output.write(j_file_list.encode())

        info_size = self.f_output.tell() - info_size_pos - 4
        print('Info size:', info_size)
        self.f_output.seek(info_size_pos)
        self.f_output.write(info_size.to_bytes(4, byteorder='big'))

    def generate_main_frames(self):
        i = 1
        while True:
            chunk = self.f_input.read(BMP_BODY_LEN)
            if chunk:
                print('Generating {0} frame.'.format(i))
                self.crc = binascii.crc32(chunk, self.crc)
                if len(chunk) != BMP_BODY_LEN:
                    chunk = bytearray(chunk)
                    chunk.extend(bytearray(BMP_BODY_LEN - len(chunk)))

                self.new_cluster(i)
                self.f_output.write(chunk)
                i = i + 1
            else:
                break

    def end(self):
        self.f_output.close()
        os.rename(self.output_filepath_tmp, self.output_filepath)

def encode(filepath):
    encoder = Encoder(filepath)
    encoder.encode()
    print('Encode end.')