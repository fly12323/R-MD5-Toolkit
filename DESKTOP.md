# Windows 桌面版

界面采用 R 品牌标识、深蓝功能侧栏和浅色工作台。左侧切换功能，
中间配置参数，右侧查看摘要、JSON 与运行日志。窗口与 EXE 均使用
`assets/r-icon.ico`；图标原图及生成提示词见 `assets/README.md`。

安装与运行：

```powershell
python -m pip install -r requirements-ui.txt
python md5_desktop.py
```

生成桌面程序：

```powershell
python build_desktop.py
```

输出为 `dist/MD5Toolkit/MD5Toolkit.exe`。运行和分发时保留整个
`MD5Toolkit` 文件夹（包含 Qt/Python 运行库），目标机器无需安装 Python。

界面覆盖 CLI 的十种模式，复用既有参数校验与算法。计算由独立进程执行，
Windows 停止与关闭操作使用 taskkill 清理整个任务进程树。任务完成后
显示结构化结果，支持复制、保存 JSON 和打开结果所在目录。
后台算法目前只在结束时输出 JSON，因此日志展示启动信息和最终输出；
不定进度条与耗时表示运行状态，不声称有实时搜索次数或百分比。

碰撞生成默认输出至用户 `Documents/MD5-Collisions`。默认超时 120 秒；
搜索默认最多尝试 100 万次。可在界面调整参数。

fastcoll 不捆绑进 EXE。开发时可沿用项目本机配置；打包后应在界面选择
本机 `fastcoll.exe` 路径。其来源和使用限制见 `THIRD_PARTY.md`。

双重哈希和魔术哈希的随机搜索可能在次数/时间上限内没有结果，
界面将分别显示“已达到尝试次数”或“已超时”。

开发验证：

```powershell
python -m unittest discover -s tests -v
python tests/desktop_smoke.py
python tests/desktop_full_check.py
python tests/desktop_frozen_smoke.py
```

最后一项需先打包。两项桌面验证中的原生碰撞检查需要项目
`bin/fastcoll.exe`；测试生成的碰撞文件保存在临时目录并自动清理。
