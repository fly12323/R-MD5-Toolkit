import hashlib
import random
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
import test_toolkit
from test_toolkit import toolkit


class ExtendedTests(unittest.TestCase):
    cli = test_toolkit.ToolkitTests.cli
    def test_real_search(self):
        code, result = self.cli('-m', 'single', '-s', 'ABC', '-c', 'ctf_', '-f', '_end', '-l', '12', '-w', '2', '--max-attempts', '100000', '--timeout', '10')
        self.assertEqual(code, 0, result)
        message = result['result']['message']
        self.assertTrue(message.startswith('ctf_') and message.endswith('_end'))
        self.assertEqual(len(result['result']['candidate']), 12)
        self.assertEqual(hashlib.md5(message.encode()).hexdigest(), result['result']['md5'])
        self.assertTrue(result['result']['md5'].startswith('abc'))
        print('Real search evidence:', result)

    def test_position_unicode(self):
        message = '前缀a 后缀 '
        digest = hashlib.md5(message.encode()).hexdigest()
        code, result = self.cli('-m', 'single', '-s', digest[5:9].upper(), '-p', '5', '-c', '前缀', '-f', ' 后缀 ', '--charset', 'a', '-l', '1', '--max-attempts', '1', '-w', '4')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['result']['message'], message)
        self.assertEqual(result['attempts'], 1)

    def test_magic_search(self):
        args = ['-c', 'QNKCDZ', '--charset', 'O', '-l', '1', '--max-attempts', '1']
        code, result = self.cli('-m', 'magic', *args)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['result']['message'], 'QNKCDZO')
        self.assertTrue(toolkit.is_magic(result['result']['md5']))
        code, result = self.cli('-m', 'magic-double', *args)
        self.assertEqual(code, 1)
        self.assertIsNone(result['result'])

    def test_magic_double_positive_logic(self):
        config = {'mode': 'magic-double', 'prefix': '', 'suffix': ''}
        with patch.object(toolkit, 'md5', side_effect=['0e' + '1' * 30, '00e' + '2' * 29]) as digest:
            result = toolkit.evaluate('candidate', config)
        self.assertIsNotNone(result)
        self.assertEqual(digest.call_args_list[1].args[0], ('0e' + '1' * 30).encode('ascii'))

    def test_random_extensions(self):
        rng = random.Random(42)
        for _ in range(200):
            original = bytes(rng.randrange(256) for _ in range(rng.randrange(2048)))
            append = bytes(rng.randrange(256) for _ in range(rng.randrange(512)))
            extension, digest = toolkit.length_extend(hashlib.md5(original).hexdigest(), len(original), append)
            self.assertEqual(digest, hashlib.md5(original + extension).hexdigest())

    def test_file_cli_and_missing_generator(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / 'a.bin', Path(temporary) / 'b.bin'
            data = b'\x00\xff\x80'
            a.write_bytes(data)
            b.write_bytes(data)
            code, result = self.cli('-m', 'inspect', '--file', str(a))
            self.assertEqual(code, 0)
            self.assertEqual(result['md5'], hashlib.md5(data).hexdigest())
            self.assertEqual(bytes.fromhex(result['raw_digest']['hex']), hashlib.md5(data).digest())
            code, result = self.cli('-m', 'verify', '--file1', str(a), '--file2', str(b))
            self.assertEqual(code, 1)
            self.assertFalse(result['collision'])
            code, result = self.cli('-m', 'verify', '--file1', str(a), '--file2', str(b) + '.missing')
            self.assertEqual(code, 2)
            self.assertIn('error', result)
        code, result = self.cli('-m', 'strong', '--fastcoll', 'definitely_missing_fastcoll_123456')
        self.assertEqual(code, 2)
        self.assertIn('error', result)
