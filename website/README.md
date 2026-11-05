# Genesis 研究者工坊网站

静态中文学习网站，对应 https://github.com/HeHaodong2004/Genesis_learning 。

`dist/` 可直接作为静态站点托管。无需 API key、模型调用或数据库；课程和源码均随站点提供，无外部 CDN。浏览器仅在 localStorage 保存自评进度、笔记和用户输入，支持 JSON 导出/导入。

网页中的命令需要在自己的工作站执行；网页不运行 Python、Genesis 或 GPU 代码。完整研究训练包与验证记录在 GitHub。参考源码更新后，应同步 `course-data.js` 并重新验证课程命令。

本地预览：在 `dist/` 中运行 `python3 -m http.server 8765 --bind 127.0.0.1`，浏览器打开 `http://127.0.0.1:8765`。
