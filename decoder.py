import os
import io
import json
import shutil
import binascii
from common import *
from file_writer import *

class Decoder(object):
    def __init__(self, filepath):
        if not filepath.endswith('.mkv'):
            raise Exception('Expect input file name ends with .mkv')
        self.input_filepath = filepath

    @property
    def output_filepath(self):
        return self.input_filepath[:-4]

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    def decode(self):
        create_tmp_dir()
        self.assemble_file()
        self.end()
        delete_tmp_dir()

    def assemble_file(self):
        print('Assemble file...')
        if os.path.exists(self.output_filepath_tmp):
            if os.path.isdir(self.output_filepath_tmp):
                shutil.rmtree(self.output_filepath_tmp)
            else:
                os.remove(self.output_filepath_tmp)
        if os.path.exists(self.output_filepath):
            if os.path.isdir(self.output_filepath):
                shutil.rmtree(self.output_filepath)
            else:
                os.remove(self.output_filepath)

        with open(self.input_filepath, 'rb') as f:
            f.seek(os.path.getsize('mkv_header') + 20)
            if b'f2v' != f.read(3):
                raise Exception('Not a f2v mkv file.')

            version = f.read(1)
            if version == b'\x01' or version == b'\x02':
                raise Exception('v1 and v2 are deprecated.')
            elif version == b'\x03':
                self.assemble_file_v3(f)
            else:
                raise Exception('Not implemented version ' + version)

    def assemble_file_v3(self, f):
        info_size = int.from_bytes(f.read(4), byteorder='big')
        print('Info size:', info_size)

        output_filesize = int.from_bytes(f.read(5), byteorder='big')
        print('Output file size:', output_filesize)
        expected_crc = int.from_bytes(f.read(4), byteorder='big')
        print('Expect CRC:', expected_crc)

        is_dir = int.from_bytes(f.read(1), byteorder='big')
        print('Is dir:', is_dir)
        if is_dir:
            j_file_list = f.read(info_size - 10).decode()
            file_list = json.loads(j_file_list)
            print('File list len:', len(file_list))

        f.seek(BMP_BODY_LEN - 8 - info_size, io.SEEK_CUR)
        i = 1
        read = 0
        crc = 0

        if is_dir:
            fw = OriginalFolderWriter(self.output_filepath)
            fw.file_list = file_list
        else:
            fw = OriginalFileWriter(self.output_filepath)

        while read < output_filesize:
            print('Reading {0} frame.'.format(i))
            f.seek(20, io.SEEK_CUR)
            to_read = BMP_BODY_LEN if output_filesize - read >= BMP_BODY_LEN else output_filesize - read
            chunk = f.read(to_read)
            crc = binascii.crc32(chunk, crc)
            fw.write(chunk)
            
            read = read + to_read
            i = i + 1

        if crc != expected_crc:
            raise Exception('CRC not match, calculated crc {0}, expected crc {1}.', crc, expected_crc)
        fw.close()

    def end(self):
        pass

def decode(filepath):
    decoder = Decoder(filepath)
    decoder.decode()
    print('Decode end.')