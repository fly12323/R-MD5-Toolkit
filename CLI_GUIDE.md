# CTF MD5 Toolkit

面向 CTF 和密码学实验的 MD5 命令行工具箱。Python 3.9+，仅使用标准库；常规功能无需第三方 Python 库；strong 模式使用原生 fastcoll，不需要 Docker。

## 模式

| 模式 | 用途 |
| --- | --- |
| `single` | 搜索 MD5 摘要指定位置的十六进制片段 |
| `double` | 第一层摘要与其十六进制文本的 MD5 都匹配指定片段 |
| `suffix` | 搜索带固定后缀的消息，兼容原脚本用法 |
| `magic` | 搜索完整摘要满足 `0+e[0-9]+` 的魔术哈希 |
| `magic-double` | 第一层和第二层摘要均为魔术哈希 |
| `inspect` | 检查文本/文件摘要、魔术哈希、双重 MD5 和原始摘要编码 |
| `verify` | 验证两个文件内容不同而 MD5 相同 |
| `trace` | 使用自主核心追踪等长、完整分块消息的差分 |
| `strong` | 调用原生 fastcoll 生成相同前缀碰撞，并独立验证和保存 |
| `extend` | 从已知摘要和总字节长度计算长度扩展 |

片段搜索和魔术哈希搜索不是完整 MD5 碰撞，也不是解密或恢复未知原文。双重 MD5 指 `MD5(MD5(message).hexdigest().encode('ascii'))`，不是对原始 16 字节摘要再哈希。

## 搜索

原有 `-m/-s/-p/-l/-f/-c` 参数保留。`-p` 从 0 开始，`-l` 是候选字符数；前后缀按 UTF-8 编码。所有搜索模式均可添加固定前缀和后缀。

```bash
python md5_collision.py -m single -s 0e -l 20 --timeout 30
python md5_collision.py -m double -s 0e -w 4 --max-attempts 1000000
python md5_collision.py -m suffix -s 91e0c -f 12ba --timeout 60
python md5_collision.py -m single -s ab -p 4 -c "user=" -f "&id=1" --timeout 30
python md5_collision.py -m magic --charset 0123456789 -l 10 --timeout 60
python md5_collision.py -m magic-double --timeout 60
```

`--workers/-w` 默认最多 4 个进程，可自行调整。`--max-attempts` 是所有进程合计上限，`--timeout` 单位为秒，包含进程启动时间。默认无搜索上限，Ctrl+C 可停止。输出尝试次数、耗时、平均速度和匹配结果；超时/中断会收集已完成进程的计数，强制终止时 `attempts_complete` 为 false，计数是下界。

随机候选可能重复。指定 k 个十六进制字符时，单层搜索平均约需 `16**k` 次，双层约 `16**(2*k)` 次（按摘要均匀且近似独立估计），不保证在限额内找到。完整魔术哈希远比单纯 `0e` 前缀难找，双重魔术哈希尤其昂贵。

## PHP 弱比较与原始摘要

```bash
python md5_collision.py -m inspect --text 240610708
python md5_collision.py -m inspect --text QNKCDZO --json
python md5_collision.py -m inspect --file challenge.bin
```

这些已知文本可以本地验证：其摘要不同，但都符合科学计数法的零。PHP 在两个数字字符串使用 `==` 比较时会按数值比较；`===` 比较不会因此相等。不要把 PHP 8 的部分类型比较变化理解为所有魔术哈希场景都消失。

`inspect` 同时输出原始 16 字节摘要的 hex、URL 和 Base64，便于分析 PHP `md5($input, true)` 相关题目。原始摘要是二进制，不能当作普通 UTF-8 文本。SQL 注入是否成立仍取决于具体查询、转义和参数化方式；本工具只展示字节。

数组传入 `md5` 的题型也依赖 PHP 版本与异常处理，不能用搜索哈希来通用解决。

参考：[PHP 数字字符串](https://www.php.net/manual/en/language.types.numeric-strings.php)、[PHP 比较运算符](https://www.php.net/manual/en/language.operators.comparison.php)。

## 长度扩展

保留交互模式，并支持非交互参数和二进制追加：

```bash
python md5_collision.py -m extend
python md5_collision.py -m extend --known-hash 5d41402abc4b2a76b9719d911017c592 --known-length 5 --append " world"
python md5_collision.py -m extend --known-hash 5d41402abc4b2a76b9719d911017c592 --known-length 5 --append-hex 00ff
```

上述摘要对应 `hello`；长度单位是字节。输出的 `extension` 是完整的“胶水填充 + 追加内容”，实际新消息是 `original + extension`；URL 编码采用完整字节转义。`--append` 保留两端空白。

对 `MD5(secret + message)`，`--known-length` 必须包含秘密长度。秘密长度未知时需分别尝试候选长度并通过题目提供的校验判断。此方法不适用于 HMAC-MD5，也不直接适用于 `MD5(message + secret)`。

Python 接口：

```python
from md5_collision import length_extend
extension, new_hash = length_extend(known_hash, total_original_bytes, b"&admin=true")
```

## 原生碰撞生成

Windows 首次配置：

```bash
python setup_fastcoll.py --download-windows
python md5_collision.py -m strong -c "ctf_prefix_" --timeout 120
```

配置脚本从原作者 HTTPS 站点下载 Windows 版本到项目 `bin/fastcoll.exe`，保存下载来源与 SHA-256，并写入本地 `fastcoll.local.json`。不修改系统 PATH，不覆盖已存在的可执行文件。下载记录的 SHA-256 用于记录文件身份，不是预先认证的官方签名。

已有原生程序可以配置一次，或仅对本次调用指定：

```bash
python setup_fastcoll.py --path "C:/Tools/fastcoll.exe"
python md5_collision.py -m strong -c prefix --fastcoll "C:/Tools/fastcoll.exe"
```

查找优先级：`--fastcoll` > `FASTCOLL_PATH` 环境变量 > 项目本地配置 > `bin` 目录 > PATH。显式配置错误时会报错，不悄悄换用其他程序。

Linux/macOS 使用本机编译的 fastcoll。原作者源码见 [HashClash](https://github.com/cr-marcstevens/hashclash/tree/master/src/md5fastcoll)，可执行文件名 `fastcoll` 和 `md5_fastcoll` 均支持。配置方法相同：

```bash
python setup_fastcoll.py --path /path/to/md5_fastcoll
```

### 前缀与结果

```bash
python md5_collision.py -m strong --timeout 120 --json
python md5_collision.py -m strong -c "中文前缀" --output-dir "my collisions" --timeout 120
python md5_collision.py -m strong --prefix-file prefix.bin --timeout 120
python md5_collision.py -m verify --file1 msg1.bin --file2 msg2.bin
```

`-c` 使用 UTF-8 文本；`--prefix-file` 接受任意二进制字节，不能与非空 `-c` 同时使用。strong 默认超时 120 秒，可以通过 `--timeout` 调整。超时和中断会终止原生进程并清理临时文件。

工具仅在文件内容不同、完整 MD5 相同、两个文件都保留原始前缀且保存后再次验证通过时报告成功。输出保存到 `collisions/collision-*` 新目录，包含 `msg1.bin`、`msg2.bin` 和 `result.json`，不覆盖已有结果。

这是相同前缀碰撞，不能直接指定两个不同前缀；fastcoll 会把不足 64 字节的前缀块用零补齐，碰撞内容包含二进制字节，并非任意可打印字符串。`-s` 控制的是哈希搜索条件，不能用于指定 strong 生成结果的摘要前缀。

本机 Windows 原生后端已真实验证带前缀生成。碰撞搜索耗时会变化，不保证每次在限时内成功。外部工具的来源和分发说明见 [THIRD_PARTY.md](THIRD_PARTY.md)。

## 自主 MD5 研究核心

`md5_core.py` 按公开数学规范自行编写，提供压缩、中间 Q 状态、单步逆运算、第一轮位条件修改和双消息差分追踪。长度扩展复用这个核心；它不承担 strong 的碰撞搜索，完整自主搜索仍为独立研究方向。

```bash
python md5_collision.py -m trace --file1 msg1.bin --file2 msg2.bin --json
```

trace 要求等长文件且字节数为 64 的整数倍。输出 Q1..Q64，模加差分方向为右消息减左消息（mod 2^32）；分块追踪不包含自动 MD5 填充，最终摘要仍正常包含填充。研究进度见 [COLLISION_DEVELOPMENT.md](COLLISION_DEVELOPMENT.md)。

## 输出与验证

所有模式支持 `--json`，输出单个 JSON 对象，便于其他脚本读取。默认输出缩进的 JSON。退出码：0 成功/检查完成，1 搜索未找到或文件不构成碰撞，2 参数/运行错误，130 用户中断。参数解析错误由 argparse 输出到 stderr。

```bash
python -m unittest discover -s tests -v
```

测试覆盖长度扩展填充边界、二进制/中文、秘密前缀、已知魔术哈希、已知完整碰撞、多进程搜索限额和超时、错误输入。自主核心另外覆盖 RFC 标准向量、随机摘要、步骤逆运算、第一轮条件和已知两块碰撞的差分抵消。原生后端另外测试配置优先级、结果保存、输出拒绝及超时终止；自主碰撞搜索尚未完成。


## 使用的工具与致谢

感谢 Marc Stevens 提供的 **fastcoll**。本项目的 `strong` 模式调用其原生程序完成 MD5 碰撞搜索，Python 适配层负责参数处理、超时控制、结果保存和独立验证。

- [fastcoll 原作者页面](https://marc-stevens.nl/research/)
- [HashClash 中的 fastcoll 源码](https://github.com/cr-marcstevens/hashclash/tree/master/src/md5fastcoll)

`md5_core.py` 的基础运算依据 [RFC 1321](https://www.rfc-editor.org/rfc/rfc1321.html) 自行实现。第三方来源及分发说明见 [THIRD_PARTY.md](THIRD_PARTY.md)。
