# FVP 引擎逆向分析笔记

这是一套关于 FAVORITE 社 FVP（Favorite View Point）视觉小说引擎的逆向分析文档，以博客风格整理，供人阅读。

## 文章列表

| 编号 | 标题 | 内容摘要 |
|---|---|---|
| [01](./01-overview.md) | FVP 引擎总览 | 引擎架构、运行方式、资源系统概述 |
| [02](./02-hcb-file-format.md) | HCB 文件格式详解 | 代码区、系统描述区、导入表结构 |
| [03](./03-vm-and-opcodes.md) | VM 与指令集 | 栈机模型、opcode 全表、函数调用机制 |
| [04](./04-syscall-system.md) | Syscall 系统 | 导入表机制、功能域分类、常见 syscall 说明 |
| [05](./05-bin-and-hzc-formats.md) | BIN 与 HZC 资源格式 | 资源包结构、图像格式、VFS 覆盖规则 |
| [06](./06-hcb-ir-toolchain.md) | HCB 可逆转换工具链 | IR 设计、CFG、Lua-like 输出、回编译规则 |
| [07](./07-case-study-speak-functions.md) | 案例：SPEAK 函数族分析 | Sakura.hcb 说话人名系统逆向解析 |
| [08](./08-case-study-logo-animation.md) | 案例：LOGO 演出分析 | f_00074DA5 图层运动逐步解析 |
| [09](./09-roadmap.md) | 研究路线图 | 阶段划分、当前进展与后续方向 |

## 关于这套笔记

这套笔记的材料来自：

- 多份 FVP 相关开源工具的源码（`rfvp`、`fvp-1.0`、`FVP-Yuki`、`GARbro`、`my-sakura-moyu`）
- 民间汉化文档与逆向经验贴
- 对 `Sakura.hcb`、`WA_funta.hcb` 等实际 HCB 文件的逐条反汇编与分析

内容由 AI 辅助整理，所有结论标注了可信度。带 **[待验证]** 标记的内容需要实机或额外源码确认。

---

*最后更新：2026-08*
