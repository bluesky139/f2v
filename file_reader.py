import os
import io

class IFileReader(object):
    def __init__(self, input):
        print(self.__class__.__name__, 'open', input)

    @property
    def total_size(self):
        raise NotImplementedError(self.__class__.__name__ + '.total_size()')

    def read(self, size):
        raise NotImplementedError(self.__class__.__name__ + '.read()')

class OriginalFileReader(IFileReader):
    def __init__(self, input):
        super(OriginalFileReader, self).__init__(input)
        self.input_filepath = input
        self.f = open(input, 'rb')

    @property
    def total_size(self):
        return os.path.getsize(self.input_filepath)

    def read(self, size):
        return self.f.read(size)

    def __del__(self):
        self.f.close()

class OriginalFolderReader(IFileReader):
    def __init__(self, input):
        super(OriginalFolderReader, self).__init__(input)
        self.input_filepath = input
        self.file_list = []

        self._total_size = 0
        folder_name = os.path.basename(input)
        for root, dirs, files in os.walk(input, topdown=False):
            root = root[len(folder_name) + 1:] if len(root) > len(folder_name) else ''
            root = root.replace('\\', '/')
            for name in files:
                path = root + ('/' if root else '') + name
                filesize = os.path.getsize(folder_name + '/' + path)
                self.file_list.append((path, self._total_size, filesize))
                self._total_size = self._total_size + filesize
        
        name = self.file_list[0][0]
        print('OriginalFolderReader open to read', name)
        self.f = open(self.input_filepath + '/' + name, 'rb')
        self.current_f_pos = 0

    @property
    def total_size(self):
        return self._total_size

    def read(self, size):
        if not self.f:
            return b''
        read = 0
        data = bytearray()
        while True:
            to_read = size - read
            read_data = self.f.read(to_read)
            read = read + len(read_data)
            data.extend(read_data)
            if read == size:
                break
            else:
                self.f.close()
                self.f = None
                self.current_f_pos = self.current_f_pos + 1
                if self.current_f_pos == len(self.file_list):
                    break
                name = self.file_list[self.current_f_pos][0]
                print('OriginalFolderReader open', name)
                self.f = open(self.input_filepath + '/' + name, 'rb')
        return data
            
    def __del__(self):
        if self.f:
            self.f.close()