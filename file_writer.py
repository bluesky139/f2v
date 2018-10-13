import os
import io

class IFileWriter(object):
    def __init__(self, output):
        print(self.__class__.__name__, 'open', output)

    def write(self, chunk):
        raise NotImplementedError(self.__class__.__name__ + '.write()')

    def close(self):
        raise NotImplementedError(self.__class__.__name__ + '.close()')

class OriginalFileWriter(IFileWriter):
    def __init__(self, output):
        super(OriginalFileWriter, self).__init__(output)
        self.output_filepath = output
        self.f = open(self.output_filepath_tmp, 'wb')

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    def write(self, chunk):
        self.f.write(chunk)

    def close(self):
        self.f.close()
        os.rename(self.output_filepath_tmp, self.output_filepath)

class OriginalFolderWriter(IFileWriter):
    def __init__(self, output):
        super(OriginalFolderWriter, self).__init__(output)
        self.output_filepath = output
        self._file_list = None

    @property
    def output_filepath_tmp(self):
        return self.output_filepath + '.tmp'

    @property
    def file_list(self):
        return self._file_list

    @file_list.setter
    def file_list(self, l):
        self._file_list = l
        
        name = self._file_list[0][0]
        print('OriginalFolderWriter open', name)
        path = self.output_filepath_tmp + '/' + name
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)

        self.f = open(path, 'wb')
        self.current_f_pos = 0

    def write(self, chunk):
        while True:
            to_write = min(self.file_list[self.current_f_pos][2] - self.f.tell(), len(chunk))
            write_data = chunk[:to_write]
            self.f.write(write_data)

            if self.f.tell() == self.file_list[self.current_f_pos][2]:
                self.f.close()
                self.f = None
                self.current_f_pos = self.current_f_pos + 1
                if self.current_f_pos == len(self.file_list):
                    break
                
                name = self._file_list[self.current_f_pos][0]
                print('OriginalFolderWriter open to write', name)
                path = self.output_filepath_tmp + '/' + name
                dir = os.path.dirname(path)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                self.f = open(path, 'wb')

                chunk = chunk[to_write:]
            else:
                break

    def close(self):
        if self.f:
            self.f.close()
            self.f = None
        os.rename(self.output_filepath_tmp, self.output_filepath)