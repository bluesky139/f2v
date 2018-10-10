import os
import io
import binascii
import common

class Decoder(object):
    def __init__(self, filepath):
        if not filepath.endswith('.avi'):
            raise Exception('Expect input file name ends with .avi')
        self.input_filepath = filepath

    @property
    def output_filepath(self):
        return self.input_filepath[:-4]

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    def decode(self):
        common.create_tmp_dir()
        self.assemble_file()
        self.end()
        common.delete_tmp_dir()

    def assemble_file(self):
        print('Assemble file...')
        if os.path.exists(self.output_filepath_tmp):
            os.remove(self.output_filepath_tmp)
        if os.path.exists(self.output_filepath):
            os.remove(self.output_filepath)

        with open(self.input_filepath, 'rb') as f:
            f.seek(os.path.getsize('avi_header') + 20)
            version = f.read(1)
            if version == b'\x01':
                raise Exception('v1 is deprecated.')
            elif version == b'\x02':
                self.assemble_file_v2(f)
            else:
                raise Exception('Not implemented version ' + version)

    def assemble_file_v2(self, f):
        output_filesize = int.from_bytes(f.read(5), byteorder='little')
        print('Output file size:', output_filesize)
        expected_crc = int.from_bytes(f.read(4), byteorder='little')
        print('Expect CRC:', expected_crc)
        f.seek(common.BMP_BODY_LEN - 10, io.SEEK_CUR)

        i = 2
        read = 0
        crc = 0
        with open(self.output_filepath_tmp, 'wb') as fw:
            while read < output_filesize:
                print('Reading', i, 'frame.')
                f.seek(8, io.SEEK_CUR)
                to_read = common.BMP_BODY_LEN if output_filesize - read >= common.BMP_BODY_LEN else output_filesize - read
                chunk = f.read(to_read)
                crc = binascii.crc32(chunk, crc)
                fw.write(chunk)
                
                read = read + to_read
                i = i + 1

        if crc != expected_crc:
            raise Exception('CRC not match, calculated crc {0}, expected crc {1}.', crc, expected_crc)

    def end(self):
        os.rename(self.output_filepath_tmp, self.output_filepath)

def decode(filepath):
    decoder = Decoder(filepath)
    decoder.decode()
    print('Decode end.')