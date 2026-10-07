"""Configure a local fastcoll executable, or obtain the original Windows release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile
import io

ROOT = Path(__file__).resolve().parent
URL = 'https://www.win.tue.nl/hashclash/fastcoll_v1.0.0.5.exe.zip'


def main(argv=None):
    parser = argparse.ArgumentParser(description='一次配置本地 fastcoll；不修改系统 PATH')
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument('--path', help='已有原生可执行文件路径')
    choices.add_argument('--download-windows', action='store_true', help='从原作者 HTTPS 站点下载 Windows 版本')
    args = parser.parse_args(argv)
    try:
        if args.download_windows:
            if os.name != 'nt':
                raise ValueError('该下载仅适用于 Windows；其他系统请编译 fastcoll 后使用 --path')
            target = ROOT / 'bin' / 'fastcoll.exe'
            if target.exists():
                raise ValueError('bin/fastcoll.exe 已存在，不覆盖；请用 --path 配置它')
            with urllib.request.urlopen(URL, timeout=30) as response:
                data = response.read()
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                payload = archive.read('fastcoll_v1.0.0.5.exe')
            if payload[:2] != b'MZ':
                raise ValueError('下载内容不是 Windows 可执行文件')
            target.parent.mkdir(exist_ok=True)
            with target.open('xb') as stream:
                stream.write(payload)
            metadata = {'source': URL, 'archive_sha256': hashlib.sha256(data).hexdigest(),
                        'executable_sha256': hashlib.sha256(payload).hexdigest()}
            (target.parent / 'fastcoll-source.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        else:
            found = shutil.which(args.path)
            if not found:
                raise ValueError('可执行文件不存在或不可执行: ' + args.path)
            target = Path(found).resolve()
        (ROOT / 'fastcoll.local.json').write_text(json.dumps({'fastcoll': str(target)}, ensure_ascii=False, indent=2), encoding='utf-8')
        print('配置完成: ' + str(target))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        print('配置失败: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
