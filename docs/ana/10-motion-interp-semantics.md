# 10 · Motion 插值精确语义与帧时钟

> **前置阅读**：[04 · Syscall 系统](./04-syscall-system.md)、[`18_Motion`](../syscalls/18_Motion.md)、[`31_V3D`](../syscalls/31_V3D.md)
>
> 置信度：**[已验证]**——以下全部结论来自 rfvp 源码逐行对照 + 真机 14350 ticks 全程回放（`diffs=0`，含 5 easing 全覆盖）。

`18_Motion.md` 讲了 API 形状，本文补上**时间维**：motion 注册后，值是何时、以什么公式、被谁推进的。不搞清这三点，逐帧回放/预览必然对不上。

---

## 1. 一句话结论

Motion 只是**登记一条插值记录**；真正写 prim 的是**每帧的容器 `update()`**（`exec_*_motion(elapsed)`），`elapsed` 按固定 **16ms/tick** 累加。回放侧只要复刻"登记参数 × tick 计数 × easing 公式"，就能与引擎逐位一致。

## 2. 帧时钟：headless 必须手动带，否则 eternal busy-loop

真机主机每帧做的事（`app.rs` / `soft_host.rs` 对标）：

| 时钟 | 主机位置 | 不带的后果 |
|---|---|---|
| `timer_manager.tick(16)` | `app.rs` 附近 | `TimerGet` 等待永不到期 |
| `inputs_manager.begin_frame()` | 同上 | `InputGetState` 永远看不到点击 |
| `update_alpha/move/s2/rotation/z/v3d/anim/snow_motions(16, …)` | `anzu_scene::update_after_vm` | `Motion*Test` 忙轮询撞墙 |
| `tick_dissolve(16)` / `tick_dissolve2(16)` | 同上 | `DissolveWait` 卡死 |

注意 `parts`（`update_parts_motions`）需要 `&Vfs`，headless 拿不到时**必须跳过**——代价是 parts 合成类 tachie 差分不更新（见 §7）。

## 3. Easing 公式（整数运算，原样复刻）

`Move / S2 / Z / R / V3D` 共用同一家族（`MoveMotionType` 等，`0=None, 1=Linear, 2=Accelerate, 3=Decelerate, 4=Rebound, 5=Bounce`）。设 `src, dst, e(elapsed), d(duration)`，**Rust `i64` 除法=向零截断**（Python `//` 是向下取整，负数必须自己实现 `trunc`），`as i16/u8` 是**回绕**不是钳制：

- Linear: `src + delta*e/d`
- Accelerate: `src + delta*e*e/(d*d)`
- Decelerate: `dst - delta*(d-e)*(d-e)/(d*d)`
- Rebound: 前半 `src + hd*e*e/(hdur*hdur)`，后半 `dst - (delta-hd)*(d-e)^2/(d-hdur)^2`（`hd=delta/2, hdur=d/2`，均为截断除法）
- Bounce: 与 Rebound 镜像（V3D 的实现是**链式除法** `/k/k`，经证明与单次除法在截断语义下一致，但照抄更稳）

Alpha 只有两型（`AlphaMotionType::Linear=0 / Immediate=1`）：Linear 用 `src + (dst-src)*e/d`；Immediate 每 tick 写 `src`。

## 4. 完成 / 停止 / 替换语义（各不相同！）

| 事件 | prim motion（alpha/move/…） | V3D motion |
|---|---|---|
| `elapsed >= duration`（自然完成） | 写 `dst`，结束 | `stop_motion()` → current = `dst` |
| 显式 `*Stop` | **冻结**（保持最后插值，不写 dst） | **snap 到 `dst`** |
| 新 motion 注册（同 prim） | 停掉旧的（`elapsed` 清零），值从旧插值处连续 | 先把 current snap 到旧 `dst`，再以 current 为 src 起新 |

V3D 注册**没有 src 参数**（src = 注册时 current），这点与 prim 系不同。

## 5. 参数守卫（决定 op 是否直接扔掉）

- `duration`：必须 `Int` 且 `1..=300000`，否则整 op 无效（各系一致）。
- `typ`：`MotionAlpha` 缺省/非法一律按 Linear；`Move/S2/Z/R/V3D` 要求显式 `Int` 且在枚举内（`typ=0/None` = 从不写，`Nil` = 整 op 扔掉）。
- 回退：`Nil` 的 src 回退到**当前值**（含 motion 插值中的值）；但 `MotionAlpha` 的 **`Nil` dst = 255（不透明），不是当前值**（rfvp 上游 `motion_alpha` 的 Nil→当前值在此与原版相悖，见下）。
- V3D 只有 `Linear/Accelerate/Decelerate` 参与插值？否——V3D 枚举同样有 0..5（含 Rebound/Bounce），见 `v3d.rs`。

> ⚠️ **勘误（2026-10-04，真机截图证实）**：Sakura 开场的 tachie 分镜四次同构 setup（`PrimSetSprt/GroupIn/OP/XY/Alpha0/淡入`），三次用 `MotionAlpha(pid,0,Nil,525)`、一次用显式 `MotionAlpha(pid,0,255,525)`。按"Nil→当前值"（此时恒为刚设的 0）三次淡入全是 0→0 死代码；但原版实机在 Nil 那次**显示了立绘**（`--ref-png` 对照：rfvp 显示无立绘、原版有）。结论：**原版 `MotionAlpha` 的 Nil dst ≡ 255**；Nil src 仍为当前值（`(_,Nil,0,365)` 的淡出行为符合此解释）。`Move/S2/Z/R` 系暂无反例，保持 Nil→当前值。

## 6. `Test` 与暂停门

`*Test` 只读不写，可忽略。暂停门（prim/祖先 `paused`）会冻结插值；Sakura 开场实测全程无暂停，可忽略，遇到 systematically 对不上的行优先查它。

## 7. 已知近似（本篇不覆盖）

- `MotionAnim`（帧动画改显示帧）、parts 合成（需 VFS tick）、`reverse`/Ctrl 快进（负 elapsed）。
- `GraphRGB(100,100,100)` 是**字节级 no-op**（上游显式 early-return），回放可直接忽略；非 100 才 bump generation。
- `Text*` 文本渲染、`Snow`、`Movie` 另行建模。

## 8. 验证方法

逐 tick 记录 `(tick, op)`，回放时对 motion 记录求值（`e=(tick-t0)*16`：`e<=0` 取注册前值、`e>=dur` 取 dst、否则 easing），终态与真机活快照逐字段对比。Sakura 开场 14350 ticks：`diffs=0`，零字段剔除。
