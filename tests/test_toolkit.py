import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import md5_collision as toolkit

ROOT = Path(__file__).resolve().parents[1]


class ToolkitTests(unittest.TestCase):
    def test_extension_boundaries(self):
        for size in (0, 1, 10, 55, 56, 63, 64, 65, 119, 120, 128, 1024):
            original = b'a' * size
            for append in (b'', b'test', b'b' * 55, b'b' * 64, b'b' * 130, ' 中文 '.encode(), b'\0\xff'):
                with self.subTest(size=size, append=append):
                    extension, digest = toolkit.length_extend(hashlib.md5(original).hexdigest(), size, append)
                    self.assertEqual(digest, hashlib.md5(original + extension).hexdigest())
                    self.assertTrue(extension.endswith(append))

    def test_secret_prefix_extension(self):
        secret, message, append = b'secret', b'user=guest', b'&admin=true'
        extension, digest = toolkit.length_extend(toolkit.md5(secret + message), len(secret + message), append)
        self.assertEqual(digest, toolkit.md5(secret + message + extension))

    def test_magic(self):
        for text in ('240610708', 'QNKCDZO'):
            self.assertTrue(toolkit.is_magic(toolkit.md5(text.encode())))
        for digest in ('0e123abc', '0e', 'e123', '0e123\n'):
            self.assertFalse(toolkit.is_magic(digest))
        self.assertTrue(toolkit.is_magic('00e123'))

    def test_validation(self):
        for digest, length in [('bad', 10), ('a' * 32, -1)]:
            with self.assertRaises(ValueError):
                toolkit.length_extend(digest, length, b'a')
        self.assertLessEqual(len(toolkit.padding(10**15)), 72)

    def cli(self, *args):
        proc = subprocess.run([sys.executable, str(ROOT / 'md5_collision.py'), *args, '--json'],
                              capture_output=True, text=True, encoding='utf-8', timeout=15)
        return proc.returncode, json.loads(proc.stdout)

    def test_cli_search(self):
        for mode in ('single', 'double', 'suffix'):
            message = 'xa!' if mode == 'suffix' else 'xa'
            digest = toolkit.md5(message.encode())
            extra = ['-f', '!'] if mode == 'suffix' else []
            if mode == 'double':
                # Find a common nibble position to make the sole candidate succeed.
                second = toolkit.md5(digest.encode())
                position = next(i for i in range(32) if digest[i] == second[i])
                target = digest[position]
            else:
                position, target = 0, digest
            code, result = self.cli('-m', mode, '-s', target, '-p', str(position), '-c', 'x', '--charset', 'a', '-l', '1', '-w', '2', '--max-attempts', '4', *extra)
            self.assertEqual(code, 0, result)
            self.assertEqual(result['result']['message'], message)
            self.assertLessEqual(result['attempts'], 4)
            self.assertTrue(result['attempts_complete'])

    def test_limits_and_timeout(self):
        code, result = self.cli('-m', 'single', '-s', '0' * 32, '--charset', 'a', '-l', '1', '-w', '2', '--max-attempts', '7')
        self.assertEqual(code, 1)
        self.assertEqual(result['attempts'], 7)
        code, result = self.cli('-m', 'magic-double', '--charset', 'a', '-l', '1', '-w', '2', '--timeout', '0.2')
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'timeout')
        self.assertTrue(result['attempts_complete'])

    def test_cli_invalid(self):
        for args in (['-s', 'zz'], ['-s', 'aa', '-p', '31'], ['-s', 'a', '-l', '0'], ['-s', 'a', '--timeout', 'nan']):
            code, result = self.cli('-m', 'single', *args)
            self.assertEqual(code, 2)
            self.assertIn('error', result)

    def test_cli_inspect_extend(self):
        code, result = self.cli('-m', 'inspect', '--text', '240610708')
        self.assertEqual(code, 0)
        self.assertTrue(result['magic'])
        original = b'hello'
        code, result = self.cli('-m', 'extend', '--known-hash', toolkit.md5(original), '--known-length', '5', '--append-hex', '00ff')
        self.assertEqual(code, 0)
        extension = bytes.fromhex(result['extension']['hex'])
        self.assertEqual(result['final_hash'], toolkit.md5(original + extension))

    def test_known_collision_and_identical_files(self):
        # Published Wang/Yu 128-byte collision pair (Peter Selinger's MD5 demo).
        first = bytes.fromhex('d131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f8955ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5bd8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70')
        second = bytes.fromhex('d131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f8955ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5bd8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70')
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / 'a', Path(temporary) / 'b'
            a.write_bytes(first)
            b.write_bytes(second)
            self.assertTrue(toolkit.verify_collision(a, b)['collision'])
            from md5_core import differential_trace
            trace = differential_trace(first, second)
            self.assertEqual(trace['blocks'][0]['output_state_delta'], [0x80000000, 0x82000000, 0x82000000, 0x82000000])
            self.assertEqual(trace['blocks'][1]['output_state_delta'], [0, 0, 0, 0])
            self.assertTrue(trace['collision'])
            self.assertEqual(trace['md5_left'], hashlib.md5(first).hexdigest())
            code, result = self.cli('-m', 'trace', '--file1', str(a), '--file2', str(b))
            self.assertEqual(code, 0)
            self.assertTrue(result['collision'])
            self.assertFalse(toolkit.verify_collision(a, a)['collision'])
            b.write_bytes(b'other')
            self.assertFalse(toolkit.verify_collision(a, b)['collision'])


if __name__ == '__main__':
    unittest.main()
