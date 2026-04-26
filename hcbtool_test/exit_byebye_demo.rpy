# exit_byebye_demo.rpy
#
# 基于 f_00037BF7 的近似 Ren'Py 复现脚本。
#
# 目标：
# - 复现 FVP 在“退出游戏”时的 byebye 演出：
#   1) 锁定输入语义（在本示例中用 modal screen / 不给玩家操作机会近似）
#   2) 叠加 byebye 相关图层
#   3) 背景与 logo 渐入
#   4) logo 轻微缩放收束
#   5) 全屏白 tile 在后段淡入，形成整体冲白/退场感
#   6) 演出结束后退出到桌面或返回调用处
#
# 使用说明：
# 1. 将本文件放入 Ren'Py 工程的 game/ 目录。
# 2. 将资源放入 game/exit/ 目录：
#    - menu_byebye_bg.png
#    - menu_byebye.png
# 3. 可在任意位置调用：
#       call fvp_exit_byebye_demo
# 4. 若要真退出程序，保留 `Quit(confirm=False)`；若只想调试演出，可改成 `return`。
#
# 说明：
# - 该脚本尽量使用 Ren'Py 原生 image / transform / label / scene / show / hide。
# - 不依赖 Python 代码驱动。
# - 这是近似视觉复现，不是 1:1 的 FVP 渲染器移植。

init offset = 50

# -----------------------------------------------------------------------------
# 资源定义
# -----------------------------------------------------------------------------

image fvp_exit_tile_black = Solid("#000000")
image fvp_exit_tile_white = Solid("#FFFFFF")
image fvp_exit_menu_bg = "exit/menu_byebye_bg.png"
image fvp_exit_menu_logo = "exit/menu_byebye.png"

# -----------------------------------------------------------------------------
# 图层动画
# -----------------------------------------------------------------------------
# 依据：
# - prim 430 (`menu_byebye_bg`)：alpha 0 -> 160，时长 l0≈3000ms
# - prim 99  (`menu_byebye`)：alpha 0 -> 128，时长 l0≈3000ms
# - prim 99 / 429：scale 1100 -> 1000，type=3 减速
# - prim 35 白 tile：alpha 0 -> 255，时长 l0-500≈2500ms
#
# 在 Ren'Py 里做近似映射：
# - alpha 160/255 ≈ 0.627
# - alpha 128/255 ≈ 0.502
# - scale 1100 -> 1000 近似为 zoom 1.1 -> 1.0
# - 白 tile 在 2.5 秒内从透明到全白

transform fvp_exit_black_base:
    anchor (0.0, 0.0)
    pos (0, 0)
    alpha 1.0

transform fvp_exit_bg_enter:
    subpixel True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    linear 3.0 alpha 0.627

transform fvp_exit_logo_dark_enter:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.1
    parallel:
        linear 3.0 alpha 0.502
    parallel:
        easeout 3.0 zoom 1.0

transform fvp_exit_logo_light_enter:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.1
    parallel:
        linear 3.0 alpha 0.502
    parallel:
        linear 3.0 zoom 1.0

transform fvp_exit_white_flash:
    anchor (0.0, 0.0)
    pos (0, 0)
    alpha 0.0
    linear 2.5 alpha 1.0

# 可选：让整屏最后再略停一瞬，模拟 ThreadNext / ThreadExit 前的完成帧。
transform fvp_exit_hold:
    alpha 1.0

# -----------------------------------------------------------------------------
# 演出标签
# -----------------------------------------------------------------------------

label fvp_exit_byebye_demo:
    window hide
    scene black

    # 1) 先铺黑底，相当于构建退场场景的底板。
    show fvp_exit_tile_black at fvp_exit_black_base

    # 2) 叠加 byebye 背景与 logo 两层。
    #    这里使用两层相同 logo 来近似 FVP 中 99 与 429 两层不同 blend 的结构。
    show fvp_exit_menu_bg at fvp_exit_bg_enter
    show fvp_exit_menu_logo at fvp_exit_logo_dark_enter
    show fvp_exit_menu_logo at fvp_exit_logo_light_enter

    # 3) 叠加白色 tile，在后段逐渐升高 alpha，模拟整体冲白/退场。
    show fvp_exit_tile_white at fvp_exit_white_flash

    # 4) 等待整段退出演出播完。
    pause 3.0
    pause 0.5

    # 5) 可选择真正退出，或仅返回。
    # 若只想测试演出，把下一行改成 `return` 即可。
    #$ renpy.quit(save=False)
    #return
