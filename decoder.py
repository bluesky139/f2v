import binascii
import ffmpeg
import common

class Decoder(object):
    def __init__(self, filepath):
        if not filepath.endswith('.avi'):
            raise Exception('Expect input file name ends with .avi')
        self.input_filepath = filepath

    @property
    def output_filepath(self):
        return self.input_filepath[:-4]

    def decode(self):
        common.create_tmp_dir()
        self.avi_to_bmp()
        self.assemble_file()
        common.delete_tmp_dir()

    def avi_to_bmp(self):
        print('Avi to bmp...')
        out, _ = (ffmpeg
            .input(self.input_filepath)
            .output(common.TMP_DIR + '/img%05d.bmp')
            .run()
        )

    def assemble_file(self):
        print('Assemble file...')
        with open(common.TMP_DIR + '/img00001.bmp', 'rb') as f:
            f.seek(54)
            version = f.read(1)
            if version == b'\x01':
                self.assemble_file_v1(f)
            else:
                raise Exception('Not implemented version ' + version)

    def assemble_file_v1(self, f_info):
        output_filesize = int.from_bytes(f_info.read(5), byteorder='big')
        print('Output file size:', output_filesize)
        expected_crc = int.from_bytes(f_info.read(4), byteorder='big')
        print('Expect CRC:', expected_crc)

        i = 2
        read = 0
        crc = 0
        with open(self.output_filepath, 'wb') as fw:
            while read < output_filesize:
                filename = 'img' + str(i).zfill(5) + '.bmp'
                print('Reading', filename)
                with open(common.TMP_DIR + '/' + filename, 'rb') as f:
                    f.seek(54)
                    to_read = common.BMP_BODY_LEN if output_filesize - read >= common.BMP_BODY_LEN else output_filesize - read
                    chunk = f.read(to_read)
                    crc = binascii.crc32(chunk, crc)
                    fw.write(chunk)
                
                read = read + to_read
                i = i + 1

        if crc != expected_crc:
            raise Exception('CRC not match, calculated crc {0}, expected crc {1}.', crc, expected_crc)

def decode(filepath):
    decoder = Decoder(filepath)
    decoder.decode()
    print('Decode end.')