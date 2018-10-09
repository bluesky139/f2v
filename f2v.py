import sys

def usage():
    print('''
    Usage:
        f2v.py e input_filename
        f2v.py d input_filename.avi

        e[ncode]: Convert any file to video file.
        d[ecode]: Convert back original file from video file.
    ''')

if len(sys.argv) != 3:
    usage()
    exit(1)

command = sys.argv[1]
filepath = sys.argv[2]

if command == 'e':
    import encoder
    encoder.encode(filepath)
elif command == 'd':
    import decoder
    decoder.decode(filepath)
else:
    usage()
    exit(1)