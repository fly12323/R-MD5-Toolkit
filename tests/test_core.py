import hashlib
import random
import struct
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import md5_core as core


class CoreTests(unittest.TestCase):
    def test_rfc_vectors(self):
        vectors = [(b'', 'd41d8cd98f00b204e9800998ecf8427e'),
                   (b'a', '0cc175b9c0f1b6a831c399e269772661'),
                   (b'abc', '900150983cd24fb0d6963f7d28e17f72'),
                   (b'message digest', 'f96b697d7cb7938d525a2f31aaf161d0'),
                   (b'abcdefghijklmnopqrstuvwxyz', 'c3fcd3d76192e4007dfb496cca67e13b'),
                   (b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', 'd174ab98d277d9f5a5611c2c9f419d9f'),
                   (b'1234567890' * 8, '57edf4a22be3c955ac49da2e2107b67a')]
        for message, digest in vectors:
            self.assertEqual(core.hexdigest(message), digest)

    def test_random_hashes(self):
        rng = random.Random(7)
        for length in list(range(130)) + [rng.randrange(8192) for _ in range(100)]:
            data = bytes(rng.randrange(256) for _ in range(length))
            self.assertEqual(core.hexdigest(data), hashlib.md5(data).hexdigest())

    def test_inverse_every_step(self):
        rng = random.Random(11)
        for step in range(64):
            for _ in range(20):
                a, b, c, d, word = [rng.getrandbits(32) for _ in range(5)]
                q = core.next_q(step, a, b, c, d, word)
                self.assertEqual(core.recover_word(step, a, b, c, d, q), word)

    def test_first_round_conditions(self):
        rng = random.Random(21)
        for _ in range(50):
            block = bytes(rng.randrange(256) for _ in range(64))
            constraints = {}
            for step in range(1, 17):
                mask = rng.getrandbits(32)
                constraints[step] = (mask, rng.getrandbits(32) & mask)
            modified = core.modify_first_round(block, constraints)
            _, trace = core.compress(modified, with_trace=True)
            for step, (mask, bits) in constraints.items():
                self.assertEqual(trace[step + 3] & mask, bits)
        self.assertEqual(core.modify_first_round(block, {}), block)

    def test_trace_validation(self):
        for first, second in [(b'a', b'b'), (b'a' * 64, b'')]:
            with self.assertRaises(ValueError):
                core.differential_trace(first, second)
        with self.assertRaises(ValueError):
            core.compress(b'')
        with self.assertRaises(ValueError):
            core.modify_first_round(b'\0' * 64, {17: (1, 1)})
        with self.assertRaises(ValueError):
            core.modify_first_round(b'\0' * 64, {1: (1, 2)})
