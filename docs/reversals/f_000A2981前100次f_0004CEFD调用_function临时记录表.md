# f_000A2981 前 100 次 f_0004CEFD 调用：function 分析临时记录表

扫描对象：[`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:1)

截止位置：第 100 次 [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 调用位于 [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:1227)。此前共出现 195 次内部 function 调用，去重后 35 个 function。

## 1. 待补逐条反汇编函数

| 顺序 | function | 首次调用位置 | 当前状态 | 备注 |
|---:|---|---:|---|---|
| 1 | [`f_0004B1F4()`](Sakura_hcb_ir/Sakura/f_0004B1F4.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:6) | 待补 | 现有文档仅在初始化分析中提及 |
| 2 | [`f_0004B21B()`](Sakura_hcb_ir/Sakura/f_0004B21B.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:10) | 待补 | 现有文档仅在初始化分析中提及 |
| 3 | [`f_0004B135()`](Sakura_hcb_ir/Sakura/f_0004B135.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:18) | 待补 | 记录中无独立完整推断 |
| 4 | [`f_000547D2()`](Sakura_hcb_ir/Sakura/f_000547D2.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:47) | 待补 | 记录有初步参数猜测，但没有逐条反汇编 |
| 5 | [`f_00015543()`](Sakura_hcb_ir/Sakura/f_00015543.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:61) | 待补 | 记录只给出背景函数族的粗略名称 |
| 6 | [`f_00036848()`](Sakura_hcb_ir/Sakura/f_00036848.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:63) | 待补 | 记录有 BGM 初步说明，但未展开本体 |
| 7 | [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000A2981.lua:90) | 待补 | 本次目标核心正文显示入口 |
| 8 | [`f_00002711()`](Sakura_hcb_ir/Sakura/f_00002711.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_00002711.lua:547) | 待补 | 现有 CG/剧情文档仅引用，未展开 |
| 9 | [`f_000026A3()`](Sakura_hcb_ir/Sakura/f_000026A3.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000026A3.lua:596) | 待补 | 现有 CG/剧情文档仅引用，未展开 |
| 10 | [`f_000550BF()`](Sakura_hcb_ir/Sakura/f_000550BF.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000550BF.lua:703) | 待补 | 现有记录与文档均无有效推断 |
| 11 | [`f_000109BC()`](Sakura_hcb_ir/Sakura/f_000109BC.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_000109BC.lua:720) | 待补 | 现有记录与文档均无有效推断 |
| 12 | [`f_00097A34()`](Sakura_hcb_ir/Sakura/f_00097A34.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_00097A34.lua:909) | 待补 | 现有记录与文档均无有效推断 |
| 13 | [`f_00013C1F()`](Sakura_hcb_ir/Sakura/f_00013C1F.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_00013C1F.lua:926) | 待补 | 现有记录与文档均无有效推断 |
| 14 | [`f_00036514()`](Sakura_hcb_ir/Sakura/f_00036514.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_00036514.lua:965) | 待补 | 现有记录与文档均无有效推断 |
| 15 | [`f_0000E1EB()`](Sakura_hcb_ir/Sakura/f_0000E1EB.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_0000E1EB.lua:972) | 待补 | 现有记录与文档均无有效推断 |
| 16 | [`f_00014F10()`](Sakura_hcb_ir/Sakura/f_00014F10.lua:1) | [`f_000A2981.lua`](Sakura_hcb_ir/Sakura/f_00014F10.lua:1043) | 待补 | 现有记录与文档均无有效推断 |

## 2. 已有逐条反汇编或已有明确资料的 function

[`f_0004D788()`](Sakura_hcb_ir/Sakura/f_0004D788.lua:1)、[`f_00055946()`](Sakura_hcb_ir/Sakura/f_00055946.lua:1)、[`f_000376B4()`](Sakura_hcb_ir/Sakura/f_000376B4.lua:1)、[`f_00055D3D()`](Sakura_hcb_ir/Sakura/f_00055D3D.lua:1)、[`f_000493AC()`](Sakura_hcb_ir/Sakura/f_000493AC.lua:1)、[`f_00037708()`](Sakura_hcb_ir/Sakura/f_00037708.lua:1)、[`f_00002403()`](Sakura_hcb_ir/Sakura/f_00002403.lua:1)、[`f_00000004()`](Sakura_hcb_ir/Sakura/f_00000004.lua:1)、[`f_0000258B()`](Sakura_hcb_ir/Sakura/f_0000258B.lua:1)、[`f_000025C3()`](Sakura_hcb_ir/Sakura/f_000025C3.lua:1)、[`f_000025FB()`](Sakura_hcb_ir/Sakura/f_000025FB.lua:1)、[`f_00002633()`](Sakura_hcb_ir/Sakura/f_00002633.lua:1)、[`f_0005207E()`](Sakura_hcb_ir/Sakura/f_0005207E.lua:1)、[`f_0000266B()`](Sakura_hcb_ir/Sakura/f_0000266B.lua:1)、[`f_0001052C()`](Sakura_hcb_ir/Sakura/f_0001052C.lua:1)、[`f_000104E8()`](Sakura_hcb_ir/Sakura/f_000104E8.lua:1)、[`f_00000512()`](Sakura_hcb_ir/Sakura/f_00000512.lua:1)、[`f_00055113()`](Sakura_hcb_ir/Sakura/f_00055113.lua:1)、[`f_00001918()`](Sakura_hcb_ir/Sakura/f_00001918.lua:1)。

另有部分函数虽没有逐条文档，但在初始化/收尾资料中已有局部说明；本表仍将其列入待补，以避免“有引用”被误认为“已完成逐条反汇编”。
