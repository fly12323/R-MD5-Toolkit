import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fastcoll_backend as backend

FIRST = bytes.fromhex('d131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f8955ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5bd8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70')
SECOND = bytes.fromhex('d131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f8955ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5bd8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70')


class FakeProcess:
    def __init__(self, cwd, pair, returncode=0):
        self.returncode = returncode
        if pair is not None:
            for filename, data in zip(('msg1.bin', 'msg2.bin'), pair):
                (Path(cwd) / filename).write_bytes(data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def communicate(self, timeout=None):
        return b'', b''


class NativeBackendTests(unittest.TestCase):
    def run_backend(self, pair, prefix=b'', returncode=0):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output with spaces'
            def factory(command, **kwargs):
                self.assertEqual(command[1:], ['-q', '-p', 'prefix.bin', '-o', 'msg1.bin', 'msg2.bin'])
                return FakeProcess(kwargs['cwd'], pair, returncode)
            with patch.object(backend, 'resolve_fastcoll', return_value=Path(sys.executable)), patch.object(backend.subprocess, 'Popen', side_effect=factory):
                result = backend.generate_collision(prefix, output)
                self.assertTrue(result['collision'])
                self.assertNotEqual(result['sha256'][0], result['sha256'][1])
                self.assertTrue((Path(result['files'][0]).parent / 'result.json').exists())
                return result

    def test_valid_pair_saved(self):
        self.run_backend((FIRST, SECOND))

    def test_invalid_output_rejected(self):
        for pair, prefix, code in [(None, b'', 0), ((FIRST, FIRST), b'', 0), ((b'a', b'b'), b'', 0), ((FIRST, SECOND), b'wrong', 0), (None, b'', 1)]:
            with self.subTest(pair=pair, prefix=prefix, code=code):
                with self.assertRaises(RuntimeError):
                    self.run_backend(pair, prefix, code)

    def test_configuration_precedence(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'config.json'
            config.write_text(json.dumps({'fastcoll': sys.executable}))
            with patch.object(backend, 'CONFIG', config), patch.dict(backend.os.environ, {}, clear=True):
                self.assertEqual(backend.resolve_fastcoll(), Path(sys.executable).resolve())
                with self.assertRaises(ValueError):
                    backend.resolve_fastcoll('definitely_missing_executable_12345')
            with patch.object(backend, 'CONFIG', config), patch.dict(backend.os.environ, {'FASTCOLL_PATH': 'definitely_missing_executable_12345'}):
                with self.assertRaises(ValueError):
                    backend.resolve_fastcoll()

    def test_native_timeout(self):
        binary = backend.ROOT / 'bin' / 'fastcoll.exe'
        if not binary.exists():
            self.skipTest('Windows native executable not configured')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output'
            with self.assertRaisesRegex(RuntimeError, '超时'):
                backend.generate_collision(b'timeout_test', output, str(binary), timeout=0.000001)
            self.assertFalse(output.exists())

    def test_malformed_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'config.json'
            for value in ([], {}, {'fastcoll': 123}):
                config.write_text(json.dumps(value))
                with patch.object(backend, 'CONFIG', config), patch.dict(backend.os.environ, {}, clear=True):
                    with self.assertRaises(ValueError):
                        backend.resolve_fastcoll()

    def test_cli_rejects_conflicting_parameters(self):
        import md5_collision
        import contextlib
        import io
        for extra in (['-s', 'abc'], ['-f', 'suffix'], ['--prefix-file', 'anything', '-c', 'prefix']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = md5_collision.main(['-m', 'strong', '--json', *extra])
            self.assertEqual(code, 2)
            self.assertIn('error', json.loads(output.getvalue()))
