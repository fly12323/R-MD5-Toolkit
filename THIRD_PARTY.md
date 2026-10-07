# 第三方工具来源

项目的 Python 后端适配层由本项目实现。实际的完整 MD5 碰撞搜索由 Marc Stevens 的 fastcoll 完成，不宣称为自主碰撞算法。

Windows 官方版本下载地址：
https://www.win.tue.nl/hashclash/fastcoll_v1.0.0.5.exe.zip

原作者研究页面：
https://marc-stevens.nl/research/

源码参考：
https://github.com/cr-marcstevens/hashclash/tree/master/src/md5fastcoll

安装时仅在用户本机获取原生程序，bin/ 和 fastcoll.local.json 均不提交；项目不重新打包分发该程序。下载来源与文件 SHA-256 保存在 bin/fastcoll-source.json。

2006 年 fastcoll 源文件头部声明科学/教育用途，并包含使用、修改和再分发限制；HashClash 顶层 LICENSE 不宜直接视为覆盖所有历史文件头部。分发外部程序或源码时需遵守该版本的声明。
