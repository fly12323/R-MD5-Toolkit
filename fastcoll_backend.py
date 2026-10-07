"""Native fastcoll adapter. Collision search is performed by Marc Stevens' tool."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'fastcoll.local.json'


def resolve_fastcoll(explicit=None):
    selected = explicit or os.environ.get('FASTCOLL_PATH')
    if not selected and CONFIG.exists():
        value = json.loads(CONFIG.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('fastcoll.local.json 必须是 JSON 对象')
        selected = value.get('fastcoll')
        if not isinstance(selected, str) or not selected:
            raise ValueError('fastcoll.local.json 的 fastcoll 字段必须是非空路径')
        if not Path(selected).is_absolute():
            selected = str(ROOT / selected)
    if selected:
        found = shutil.which(selected)
        if not found:
            raise ValueError('指定的 fastcoll 不存在或不可执行: ' + selected)
        return Path(found).resolve()
    for candidate in (ROOT / 'bin' / 'fastcoll.exe', ROOT / 'bin' / 'fastcoll_v1.0.0.5.exe',
                      ROOT / 'bin' / 'fastcoll', ROOT / 'bin' / 'md5_fastcoll', 'fastcoll', 'md5_fastcoll'):
        found = shutil.which(str(candidate))
        if found:
            return Path(found).resolve()
    raise ValueError('未找到原生 fastcoll。Windows 可运行 python setup_fastcoll.py --download-windows；已有程序使用 --fastcoll PATH 或 python setup_fastcoll.py --path PATH')


def generate_collision(prefix, output_dir, executable=None, timeout=120):
    from collision_files import verify_collision
    binary = resolve_fastcoll(executable)
    destination = Path(output_dir).resolve()
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='md5-native-') as temporary:
        work = Path(temporary)
        (work / 'prefix.bin').write_bytes(prefix)
        command = [str(binary), '-q', '-p', 'prefix.bin', '-o', 'msg1.bin', 'msg2.bin']
        with subprocess.Popen(command, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as process:
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError('fastcoll 超时（' + str(timeout) + ' 秒），进程已终止') from None
            except BaseException:
                process.kill()
                process.communicate()
                raise
        if process.returncode:
            log = (stderr + stdout).decode(errors='replace')[-4000:]
            raise RuntimeError('fastcoll 退出码 ' + str(process.returncode) + ': ' + log)
        first, second = work / 'msg1.bin', work / 'msg2.bin'
        if not first.is_file() or not second.is_file():
            raise RuntimeError('fastcoll 没有生成两个输出文件')
        result = verify_collision(first, second)
        if not result['collision']:
            raise RuntimeError('fastcoll 输出未通过独立验证：要求内容不同且完整 MD5 相同')
        for filename in (first, second):
            with filename.open('rb') as stream:
                if stream.read(len(prefix)) != prefix:
                    raise RuntimeError('fastcoll 输出未保留指定前缀')
        destination.mkdir(parents=True, exist_ok=True)
        saved = Path(tempfile.mkdtemp(prefix='collision-', dir=destination))
        try:
            for source in (first, second):
                shutil.copyfile(source, saved / source.name)
            result = verify_collision(saved / first.name, saved / second.name)
            if not result['collision']:
                raise RuntimeError('保存后的文件未通过验证')
            result.update({'backend': 'native-fastcoll', 'executable': str(binary),
                           'prefix_length_bytes': len(prefix),
                           'elapsed_seconds': round(time.monotonic() - began, 4),
                           'sha256': [hashlib.sha256((saved / name).read_bytes()).hexdigest() for name in ('msg1.bin', 'msg2.bin')]})
            (saved / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        except BaseException:
            shutil.rmtree(saved)
            raise
    return result
