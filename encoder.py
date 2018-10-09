import os
import binascii
import textwrap
from PIL import Image, ImageDraw, ImageFont
import ffmpeg
import common

class Encoder(object):
    def __init__(self, filepath):
        self.input_filepath = filepath
        self.crc = 0

    @property
    def input_filename(self):
        return os.path.basename(self.input_filepath)

    @property
    def output_filepath(self):
        return self.input_filepath + '.avi'

    def encode(self):
        common.create_tmp_dir()
        self.prepare()
        self.generate_main_frames()
        self.generate_1st_frame()
        self.bmp_to_avi()
        common.delete_tmp_dir()

    def prepare(self):
        with open('bmp_header_{0}p'.format(common.VIDEO_HEIGHT), 'rb') as f:
            self.bmp_header = f.read(54)
        if len(self.bmp_header) != 54:
            raise Exception('bmp_header is not 54 bytes.')

    # First frame is for file info and title thumbnail
    def generate_1st_frame(self):
        filename = 'img00001.bmp'
        filepath = common.TMP_DIR + '/' + filename
        print('Generating', filename)

        # Create empty bmp.
        with open(filepath, 'wb') as f:
            f.write(self.bmp_header)
            f.write(bytearray(common.BMP_BODY_LEN))

        # Draw f2v mark on top right.
        image = Image.open(filepath)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("msyh.ttf", 35)
        draw.rectangle([(common.VIDEO_WIDTH - 70, 0), (common.VIDEO_WIDTH, 40)], fill=(75, 100, 171, 255))
        draw.text((common.VIDEO_WIDTH - 60, 0), 'f2v', fill=(255, 255, 255, 255), font=font)

        # Draw title.
        lines = textwrap.wrap(self.input_filename, width=17)
        y = 50
        for line in lines:
            width, height = font.getsize(line)
            draw.text((10, y), line, fill=(255, 255, 255, 255), font=font)
            y = y + height
        image.save(filepath)

        # Add file info.
        with open(filepath, 'rb+') as f:
            f.seek(54)
            f.write(b'\x01') # Version.
            
            input_filesize = os.path.getsize(self.input_filepath)
            print('Input file size:', input_filesize)
            if input_filesize > 1024 * 1024 * 1024 * 10:
                raise Exception('Input file size too big.')
            f.write(input_filesize.to_bytes(5, byteorder='big')) # File size.

            print('CRC:', self.crc)
            f.write(self.crc.to_bytes(4, byteorder='big')) # CRC

    def generate_main_frames(self):
        i = 2
        with open(self.input_filepath, 'rb') as f:
            while True:
                chunk = f.read(common.BMP_BODY_LEN)
                if chunk:
                    self.crc = binascii.crc32(chunk, self.crc)
                    if len(chunk) != common.BMP_BODY_LEN:
                        chunk = bytearray(chunk)
                        chunk.extend(bytearray(common.BMP_BODY_LEN - len(chunk)))
                    filename = 'img' + str(i).zfill(5) + '.bmp'
                    print('Generating', filename)
                    with open(common.TMP_DIR + '/' + filename, 'wb') as fw:
                        fw.write(self.bmp_header)
                        fw.write(chunk)
                    i = i + 1
                else:
                    break

    def bmp_to_avi(self):
        print('Bmp to avi...')
        out, _ = (ffmpeg
            .input(common.TMP_DIR + '/img%05d.bmp')
            .output(self.output_filepath, vcodec='rawvideo')
            #.overwrite_output()
            .run()
        )

def encode(filepath):
    encoder = Encoder(filepath)
    encoder.encode()
    print('Encode end.')