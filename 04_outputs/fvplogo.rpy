# logo-test.rpy
#
# 说明：
# 1. 将本文件放入 Ren'Py 工程的 game/ 目录中。
# 2. 将图片资源放入 game/logo_assets/ 目录：
#    - logo_bg.png
#    - logo_favo.png
#    - logo_favo_view.png
#    - logo_favo_view_p1.png
#    - logo_favo_view_p2.png
#    - logo_favo_view_p3.png
# 3. 通过 `call logo_test_play` 或 `jump logo_test_play` 运行。
#
# 本文件尽量使用 Ren'Py 原生脚本语句与 ATL，不依赖 Python 运行时逻辑。
# 它是对 `logo-test.py` 的近似同义改写：
# - 使用 HZC 内部偏移作为资源初始摆位基础；
# - 再叠加 FVP 脚本中识别出的 alpha / rotate / scale / move / z-motion 近似效果。

init python:
    try:
        with open('save.chb','r') as savefile:
            lst=savefile.readlines()
    except Exception:
        f=open('save.chb','w')
        f.close()
        lst=[]
        
    if len(lst)<2:
        title_bg="title/title_bg1.png"
    elif len(lst)==2:
        title_bg="title/title_bg2.png"
    elif len(lst)==3:
        title_bg="title/title_bg3.png"
    else:
        title_bg="title/title_bg4.png"
        
    gui.main_menu_background = title_bg

image title=[title_bg]

transform title_fade_in:
    alpha 0.0
    linear 2.5 alpha 1.0


init offset = 10

# -----------------------------------------------------------------------------
# 资源定义
# -----------------------------------------------------------------------------
# 使用 1280x720 的全屏 LiveComposite，把 HZC 资源内部给出的 top-left 偏移
# 直接编码进图层，这样后续动画只需围绕 FVP 中识别到的 OP/pivot 做变换。

image logo_test_bg = LiveComposite(
    (1280, 720),
    (0, 0), "logo_assets/logo_bg.png"
)

image logo_test_favo = LiveComposite(
    (1280, 720),
    (463, 260), "logo_assets/logo_favo.png"
)

image logo_test_favo_view = LiveComposite(
    (1280, 720),
    (539, 406), "logo_assets/logo_favo_view.png"
)

image logo_test_favo_view_p1 = LiveComposite(
    (1280, 720),
    (618, 409), "logo_assets/logo_favo_view_p1.png"
)

image logo_test_favo_view_p2 = LiveComposite(
    (1280, 720),
    (618, 404), "logo_assets/logo_favo_view_p2.png"
)

image logo_test_favo_view_p3 = LiveComposite(
    (1280, 720),
    (618, 400), "logo_assets/logo_favo_view_p3.png"
)

# -----------------------------------------------------------------------------
# 基础摆位 transform
# -----------------------------------------------------------------------------
# 由于图像已经作为全屏 composite 放好 left/top，因此这里只需要把 composite
# 的 pivot 对齐到脚本中识别出的 OP 坐标即可。

transform logo_test_bg_base:
    subpixel True
    anchor (0.0, 0.0)
    pos (0, 0)
    alpha 1.0

transform logo_test_favo_base:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0

transform logo_test_view_base:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0

transform logo_test_pivot_p:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0

# -----------------------------------------------------------------------------
# 入场动画
# -----------------------------------------------------------------------------
# 这里的映射关系对应 `logo-test.py` 中的近似实现：
# - logo_favo       : Z 750->1000 + alpha 0->255 (1800ms)
# - logo_favo_view  : Y +50->0 + Z 750->1000 + alpha 0->255 (2000ms)
# - p1/p2/p3        : alpha 0->255 + rotation ±3600->0 + scale 5000->1000
#
# 说明：
# - 用 zoom 近似 MotionMoveZ 的深度缩放效果。
# - 用 easein 模拟 type=3（Decelerate）的视觉观感。
# - `zoom 1.3333333` 近似于 1000/750。
# - `zoom 5.0 -> 1.0` 对应 5000 -> 1000。

transform logo_test_favo_intro:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.3333333
    parallel:
        linear 1.8 alpha 1.0
    parallel:
        easein 1.8 zoom 1.0

transform logo_test_view_intro:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.3333333
    yoffset 50
    parallel:
        easein_quint 2.0 alpha 0.7
    parallel:
        easein 2.0 zoom 1.0
    parallel:
        easein 2.0 yoffset 0

transform logo_test_p1_intro:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate 360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
    parallel:
        easein 2.0 rotate 0.0
    parallel:
        easein 2.0 zoom 1.0

transform logo_test_p2_intro:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate 360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
    parallel:
        easein 2.0 rotate 0.0
    parallel:
        easein 2.0 zoom 1.0

transform logo_test_p3_intro:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate -360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
    parallel:
        easein 2.0 rotate 0.0
    parallel:
        easein 2.0 zoom 1.0

# -----------------------------------------------------------------------------
# 收尾动画
# -----------------------------------------------------------------------------

transform logo_test_bg_slow_out:
    subpixel True
    anchor (0.0, 0.0)
    pos (0, 0)
    alpha 1.0
    linear 3.5 alpha 0.0

transform logo_test_common_out:
    subpixel True
    alpha 1.0
    linear 2.5 alpha 0.0

transform logo_test_quick_out:
    subpixel True
    alpha 1.0
    linear 0.1 alpha 0.0

# -----------------------------------------------------------------------------
# 演出主标签
# -----------------------------------------------------------------------------
# 注意：
# - 这里用 `pause` 的可中断特性近似 FVP 中的输入跳过检测。
# - 若玩家点击 / 确认键，会提前进入下一阶段，达到“跳过演出”的近似效果。

label logo_test_play:
    window hide
    scene black

    show logo_test_bg at logo_test_bg_base zorder 0
    show logo_test_favo at logo_test_favo_intro zorder 10
    show logo_test_favo_view at logo_test_view_intro zorder 20
    show logo_test_favo_view_p1 at logo_test_p1_intro zorder 30
    show logo_test_favo_view_p2 at logo_test_p2_intro zorder 31
    show logo_test_favo_view_p3 at logo_test_p3_intro zorder 32

    # 主演出段，对应原函数前半段。点击可提前进入下一阶段。
    pause 1.8

    # 背景慢退，对应原脚本里 250 的较长淡出。
    show logo_test_bg at logo_test_bg_slow_out zorder 0

    # 对应原逻辑里后续等待 / 输入打断窗口。
    pause 1.2

    show title at title_fade_in zorder 100  # 放在最上层
    with None
    # 统一淡出阶段。
    show logo_test_favo at logo_test_common_out zorder 10
    show logo_test_favo_view at logo_test_common_out zorder 20
    show logo_test_favo_view_p1 at logo_test_common_out zorder 30
    show logo_test_favo_view_p2 at logo_test_common_out zorder 31
    show logo_test_favo_view_p3 at logo_test_common_out zorder 32

    # 原脚本此处约为 2500ms；仍允许点击提前进入快速清理。
    pause 2.5

    # 快速归零透明度。
    show logo_test_bg at logo_test_quick_out zorder 0
    show logo_test_favo at logo_test_quick_out zorder 10
    show logo_test_favo_view at logo_test_quick_out zorder 20
    show logo_test_favo_view_p1 at logo_test_quick_out zorder 30
    show logo_test_favo_view_p2 at logo_test_quick_out zorder 31
    show logo_test_favo_view_p3 at logo_test_quick_out zorder 32

    $renpy.pause (0.1,hard=True) 

    hide logo_test_favo_view_p3
    hide logo_test_favo_view_p2
    hide logo_test_favo_view_p1
    hide logo_test_favo_view
    hide logo_test_favo
    hide logo_test_bg
    scene black

    return
