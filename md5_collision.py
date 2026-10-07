"""CTF MD5 toolkit; standard library only, Python 3.9+."""
import argparse
import base64
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import queue
import random
import re
import struct
import sys
import time
from urllib.parse import quote_from_bytes
from md5_core import compress, padding, differential_trace
from collision_files import verify_collision

CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def md5(data):
    return hashlib.md5(data).hexdigest()


def is_magic(digest):
    """A full numeric-zero hex digest, including multiple leading zeros."""
    return re.fullmatch(r'0+e[0-9]+', digest) is not None


class MD5State:
    def __init__(self, digest):
        if not re.fullmatch(r'[0-9a-fA-F]{32}', digest):
            raise ValueError('已知 MD5 必须是 32 位十六进制')
        self.state = struct.unpack('<4I', bytes.fromhex(digest))

    def update(self, block):
        self.state = compress(block, self.state)

    def hexdigest(self):
        return struct.pack('<4I', *self.state).hex()


def length_extend(known_hash, known_length, append):
    """Return glue+append and MD5(original+glue+append), without original bytes."""
    state = MD5State(known_hash)
    glue = padding(known_length)
    total = known_length + len(glue) + len(append)
    tail = append + padding(total)
    for offset in range(0, len(tail), 64):
        state.update(tail[offset:offset + 64])
    return glue + append, state.hexdigest()


def encoded(data):
    return {'hex': data.hex(), 'url': quote_from_bytes(data, safe=''),
            'base64': base64.b64encode(data).decode('ascii')}


def evaluate(candidate, config):
    message = config['prefix'] + candidate + config['suffix']
    digest = md5(message.encode('utf-8'))
    mode = config['mode']
    if mode in ('magic', 'magic-double'):
        match = is_magic(digest)
    else:
        start, target = config['start_pos'], config['substr']
        match = digest[start:start + len(target)] == target
    second = None
    if match and mode in ('double', 'magic-double'):
        second = md5(digest.encode('ascii'))
        match = is_magic(second) if mode == 'magic-double' else second[config['start_pos']:config['start_pos'] + len(config['substr'])] == config['substr']
    if match:
        result = {'candidate': candidate, 'message': message, 'md5': digest}
        if second is not None:
            result['md5_second'] = second
        return result
    return None


def search_worker(config, quota, stop, output):
    rng = random.Random()
    count = 0
    try:
        while quota is None or count < quota:
            if stop.is_set():
                break
            candidate = ''.join(rng.choices(config['charset'], k=config['length']))
            count += 1
            result = evaluate(candidate, config)
            if result is not None:
                output.put(('found', result))
                stop.set()
                break
    except Exception as exc:
        output.put(('error', str(exc)))
        stop.set()
    finally:
        output.put(('done', count))


def search(config):
    ctx = mp.get_context('spawn')
    stop, output = ctx.Event(), ctx.Queue()
    workers = config['workers']
    limit = config['max_attempts']
    if limit is not None:
        workers = min(workers, limit)
    processes = []
    began = time.monotonic()
    deadline = began + config['timeout'] if config['timeout'] is not None else None
    found, attempts, completed, status = None, 0, 0, 'exhausted'
    try:
        for i in range(workers):
            quota = None if limit is None else limit // workers + (i < limit % workers)
            process = ctx.Process(target=search_worker, args=(config, quota, stop, output))
            process.start()
            processes.append(process)
        while completed < workers:
            if deadline is not None and time.monotonic() >= deadline:
                if found is None:
                    status = 'timeout'
                break
            try:
                kind, payload = output.get(timeout=0.05)
            except queue.Empty:
                if any(p.exitcode not in (None, 0) for p in processes):
                    raise RuntimeError('搜索子进程异常退出')
                continue
            if kind == 'found':
                found, status = payload, 'found'
            elif kind == 'error':
                raise RuntimeError(payload)
            else:
                attempts += payload
                completed += 1
    except KeyboardInterrupt:
        status = 'interrupted'
    finally:
        stop.set()
        # Drain the queue before joining: workers may be flushing their messages.
        until = time.monotonic() + 2
        while completed < len(processes) and time.monotonic() < until:
            try:
                kind, payload = output.get(timeout=0.05)
                if kind == 'done':
                    attempts += payload
                    completed += 1
                elif kind == 'found':
                    found, status = payload, 'found'
            except queue.Empty:
                if all(not p.is_alive() for p in processes):
                    break
        for process in processes:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join()
        output.close()
        output.join_thread()
    elapsed = time.monotonic() - began
    return {'status': status, 'result': found, 'attempts': attempts,
            'attempts_complete': completed == len(processes),
            'elapsed_seconds': round(elapsed, 4),
            'attempts_per_second': round(attempts / elapsed, 2) if elapsed else 0}




def strong_collision(args):
    from fastcoll_backend import generate_collision
    if args.substr is not None or args.start_pos != 0 or args.suffix is not None:
        raise ValueError('strong 不支持 -s/-p/-f；摘要片段搜索请使用 single/double/suffix')
    if args.prefix_file is not None and args.prefix:
        raise ValueError('--prefix-file 与 -c 不能同时使用')
    prefix = Path(args.prefix_file).read_bytes() if args.prefix_file is not None else args.prefix.encode('utf-8')
    return generate_collision(prefix, args.output_dir, args.fastcoll, args.timeout if args.timeout is not None else 120)


def parser_for_cli():
    parser = argparse.ArgumentParser(description='CTF MD5 工具箱：哈希搜索、魔术哈希、碰撞验证、长度扩展')
    parser.add_argument('-m', '--mode', required=True, choices=['single', 'double', 'suffix', 'magic', 'magic-double', 'inspect', 'verify', 'trace', 'strong', 'extend'])
    parser.add_argument('-s', '--substr', help='目标十六进制片段')
    parser.add_argument('-p', '--start_pos', '--start-pos', type=int, default=0)
    parser.add_argument('-l', '--length', type=int, default=20, help='随机候选字符数')
    parser.add_argument('-f', '--suffix', default=None)
    parser.add_argument('-c', '--prefix', default='', help='固定消息前缀（UTF-8）')
    parser.add_argument('--charset', default=CHARS)
    parser.add_argument('-w', '--workers', type=int, default=min(os.cpu_count() or 1, 4))
    parser.add_argument('--max-attempts', type=int, help='所有进程合计最大尝试次数')
    parser.add_argument('--timeout', type=float, help='秒；搜索包含进程启动时间')
    parser.add_argument('--json', action='store_true', help='输出 JSON')
    parser.add_argument('--text', help='inspect 模式的文本（UTF-8）')
    parser.add_argument('--file', help='inspect 模式的二进制文件')
    parser.add_argument('--file1')
    parser.add_argument('--file2')
    parser.add_argument('--fastcoll', help='本地原生 fastcoll 路径，优先于配置和环境变量')
    parser.add_argument('--prefix-file', help='strong 的二进制前缀文件')
    parser.add_argument('--output-dir', default='collisions', help='碰撞输出根目录')
    parser.add_argument('--known-hash')
    parser.add_argument('--known-length', type=int, help='原始总字节数，含未知秘密')
    appended = parser.add_mutually_exclusive_group()
    appended.add_argument('--append', help='追加文本，保留空白，UTF-8')
    appended.add_argument('--append-hex', help='追加二进制数据的十六进制')
    return parser


def main(argv=None):
    parser = parser_for_cli()
    args = parser.parse_args(argv)
    try:
        if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
            raise ValueError('--timeout 必须是有限正数')
        if args.mode in ('single', 'double', 'suffix', 'magic', 'magic-double'):
            if args.length < 1 or args.workers < 1 or not args.charset:
                raise ValueError('length、workers 必须为正数，charset 不能为空')
            if args.max_attempts is not None and args.max_attempts < 1:
                raise ValueError('--max-attempts 必须为正数')
            if args.mode == 'suffix' and args.suffix is None:
                raise ValueError('suffix 模式必须提供 -f')
            if args.mode not in ('magic', 'magic-double'):
                if not args.substr or not re.fullmatch(r'[0-9a-fA-F]+', args.substr):
                    raise ValueError('-s 必须是非空十六进制片段')
                args.substr = args.substr.lower()
                if args.start_pos < 0 or args.start_pos + len(args.substr) > 32:
                    raise ValueError('匹配位置必须落在 32 位摘要范围内')
            else:
                if args.substr is not None or args.start_pos != 0:
                    raise ValueError('magic 模式匹配完整摘要，不使用 -s/-p')
            config = vars(args).copy()
            config['suffix'] = args.suffix or ''
            result = search(config)
            code = 0 if result['status'] == 'found' else 130 if result['status'] == 'interrupted' else 1
        elif args.mode == 'inspect':
            if (args.text is None) == (args.file is None):
                raise ValueError('inspect 必须且只能提供 --text 或 --file')
            data = args.text.encode('utf-8') if args.text is not None else Path(args.file).read_bytes()
            digest = md5(data)
            result = {'length_bytes': len(data), 'md5': digest, 'magic': is_magic(digest),
                      'md5_second': md5(digest.encode('ascii')), 'raw_digest': encoded(bytes.fromhex(digest))}
            code = 0
        elif args.mode == 'verify':
            if not args.file1 or not args.file2:
                raise ValueError('verify 需要 --file1 和 --file2')
            result = verify_collision(args.file1, args.file2)
            code = 0 if result['collision'] else 1
        elif args.mode == 'trace':
            if not args.file1 or not args.file2:
                raise ValueError('trace 需要 --file1 和 --file2')
            result = differential_trace(Path(args.file1).read_bytes(), Path(args.file2).read_bytes())
            code = 0
        elif args.mode == 'strong':
            result, code = strong_collision(args), 0
        else:
            known_length = args.known_length if args.known_length is not None else int(input('[>] 原始总字节数: '))
            known_hash = args.known_hash if args.known_hash is not None else input('[>] 已知 MD5: ').strip()
            append = bytes.fromhex(args.append_hex) if args.append_hex is not None else (args.append if args.append is not None else input('[>] 追加文本: ')).encode('utf-8')
            extension, digest = length_extend(known_hash, known_length, append)
            result = {'known_length': known_length, 'extension': encoded(extension), 'final_hash': digest}
            code = 0
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (ValueError, OSError, RuntimeError, EOFError) as exc:
        if args.json:
            print(json.dumps({'error': str(exc)}, ensure_ascii=True))
        else:
            print('错误: ' + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    mp.freeze_support()
    sys.exit(main())
