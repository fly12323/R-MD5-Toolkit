"""Independent, streamed validation of collision file pairs."""
import hashlib


def verify_collision(file1, file2):
    hashes, sizes = [], []
    for filename in (file1, file2):
        h = hashlib.md5()
        size = 0
        with open(filename, 'rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
                size += len(block)
        hashes.append(h.hexdigest())
        sizes.append(size)
    different = sizes[0] != sizes[1]
    if not different:
        with open(file1, 'rb') as left, open(file2, 'rb') as right:
            while True:
                a, b = left.read(1024 * 1024), right.read(1024 * 1024)
                if a != b:
                    different = True
                    break
                if not a:
                    break
    return {'files': [str(file1), str(file2)], 'md5': hashes,
            'sizes': sizes, 'different': different,
            'collision': different and hashes[0] == hashes[1]}
