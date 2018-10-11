import os
import io
import math
import binascii
import textwrap
from PIL import Image, ImageDraw, ImageFont
import common

class Encoder(object):
    def __init__(self, filepath):
        self.input_filepath = filepath
        self.crc = 0
        self.frame_count = math.ceil(os.path.getsize(self.input_filepath) / common.BMP_BODY_LEN) + 1

    @property
    def input_filename(self):
        return os.path.basename(self.input_filepath)

    @property
    def output_filepath(self):
        return self.input_filepath + '.avi'

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    def encode(self):
        common.create_tmp_dir()
        self.prepare()
        self.generate_1st_frame()
        self.generate_main_frames()
        self.add_original_file_info_to_1st_frame()
        self.correct_avi_header()
        self.end()
        common.delete_tmp_dir()

    def prepare(self):
        if os.path.exists(self.output_filepath_tmp):
            os.remove(self.output_filepath_tmp)
        if os.path.exists(self.output_filepath):
            os.remove(self.output_filepath)
        self.f_output = open(self.output_filepath_tmp, 'wb+')

        # Read whole avi header (without 'LIST movi') to output, we'll change frame count and file size later.
        with open('avi_header', 'rb') as f:
            avi_header = f.read()
            self.f_output.write(avi_header)

        # 'LIST' '(size)' 'movi'
        self.f_output.write(b'LIST')
        chunks_len = min(self.frame_count, common.CONTINUES_FRAME_COUNT) * (common.BMP_BODY_LEN + 8)
        print('1st chunks len:', chunks_len)
        self.f_output.write((chunks_len + 4).to_bytes(4, byteorder='little'))
        self.f_output.write(b'movi')

    def correct_avi_header(self):
        # Avi file size.
        chunks_len = min(self.frame_count, common.CONTINUES_FRAME_COUNT) * (common.BMP_BODY_LEN + 8)
        self.f_output.seek(4)
        self.f_output.write((chunks_len + 12 + os.path.getsize('avi_header') - 8).to_bytes(4, byteorder='little'))

        # Frame count.
        self.f_output.seek(48)
        print('Frame count:', self.frame_count)
        self.f_output.write(self.frame_count.to_bytes(4, byteorder='little'))
        self.f_output.seek(140)
        self.f_output.write(self.frame_count.to_bytes(4, byteorder='little'))

        # 'idx1' is dropped.

    # First frame is for original file info and title thumbnail
    def generate_1st_frame(self):
        filename = 'img00001.bmp'
        filepath = common.TMP_DIR + '/' + filename
        print('Generating', filename)

        # Create empty bmp.
        with open('bmp_header_{0}p'.format(common.VIDEO_HEIGHT), 'rb') as f:
            bmp_header = f.read(54)
        with open(filepath, 'wb') as f:
            f.write(bmp_header)
            f.write(bytearray(common.BMP_BODY_LEN))

        # Draw f2v mark on top left.
        image = Image.open(filepath)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("msyh.ttf", 35)
        draw.rectangle([(0, 0), (140, 45)], fill=(75, 100, 171, 255))
        draw.text((10, 0), 'f2v (v{0})'.format(int.from_bytes(common.CODE_VERSION, byteorder='little')), fill=(255, 255, 255, 255), font=font)

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
                line = old_frame[-common.VIDEO_WIDTH * 3:]
                frame.extend(line)
                old_frame = old_frame[:-common.VIDEO_WIDTH * 3]

            self.f_output.write(b'00dc')
            self.f_output.write(common.BMP_BODY_LEN.to_bytes(4, byteorder='little'))
            self.f_output.write(frame)
            
    def add_original_file_info_to_1st_frame(self):
        # Add file info.
        self.f_output.seek(os.path.getsize('avi_header') + 20)
        self.f_output.write(common.CODE_VERSION) # Version.
        
        input_filesize = os.path.getsize(self.input_filepath)
        print('Input file size:', input_filesize)
        if input_filesize > 1024 * 1024 * 1024 * 10:
            raise Exception('Input file size too big.')
        self.f_output.write(input_filesize.to_bytes(5, byteorder='little')) # File size.

        print('CRC:', self.crc)
        self.f_output.write(self.crc.to_bytes(4, byteorder='little')) # CRC

    def generate_main_frames(self):
        i = 1
        j = 2
        with open(self.input_filepath, 'rb') as f:
            while True:
                chunk = f.read(common.BMP_BODY_LEN)
                if chunk:
                    if j > common.CONTINUES_FRAME_COUNT:
                        self.f_output.write(b'RIFF')
                        chunks_len = min(self.frame_count - i * common.CONTINUES_FRAME_COUNT, common.CONTINUES_FRAME_COUNT) * (common.BMP_BODY_LEN + 8)
                        print('Next chunks len:', chunks_len)
                        self.f_output.write((chunks_len + 16).to_bytes(4, byteorder='little'))
                        self.f_output.write(b'AVIX')
                        self.f_output.write(b'LIST')
                        self.f_output.write((chunks_len + 4).to_bytes(4, byteorder='little'))
                        self.f_output.write(b'movi')
                        j = 1
                        i = i + 1

                    print('Generating [{0}] {1} frame.'.format(i, j))
                    self.crc = binascii.crc32(chunk, self.crc)
                    if len(chunk) != common.BMP_BODY_LEN:
                        chunk = bytearray(chunk)
                        chunk.extend(bytearray(common.BMP_BODY_LEN - len(chunk)))

                    self.f_output.write(b'00dc')
                    self.f_output.write(common.BMP_BODY_LEN.to_bytes(4, byteorder='little'))
                    self.f_output.write(chunk)
                    j = j + 1
                else:
                    break

    def end(self):
        self.f_output.close()
        os.rename(self.output_filepath_tmp, self.output_filepath)

def encode(filepath):
    encoder = Encoder(filepath)
    encoder.encode()
    print('Encode end.')