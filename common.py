import os
import shutil

TMP_DIR = os.path.dirname(__file__) + '/tmp'

def create_tmp_dir():
    delete_tmp_dir()
    os.mkdir(TMP_DIR)
    
def delete_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

VIDEO_WIDTH = 640
VIDEO_HEIGHT = 360
BMP_BODY_LEN = VIDEO_WIDTH * VIDEO_HEIGHT * 3