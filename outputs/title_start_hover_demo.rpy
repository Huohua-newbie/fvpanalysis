# title_start_hover_demo.rpy
#
# 目标：
# - 未悬停时显示 title_start.png
# - 鼠标悬停时，从 title_start1 到 title_start15 逐帧切换
# - 尽量使用 Ren'Py 原生语句与 ATL，不依赖内嵌 Python 逻辑
#
# 说明：
# 1. 请将本文件放入 Ren'Py 工程的 game/ 目录。
# 2. 请将图片放入 game/logo_assets/ 目录。
# 3. 本示例使用“左下角对齐”的思路处理不同高度帧。
# 4. 当前已知精确数据：
#    - title_start   : top-left=(1039, 94),  size=(204, 54)
#    - title_start1  : top-left=(942,  92),  size=(338, 56)
#    二者 bottom 值同为 148，因此可以推定应以底边对齐。
# 5. title_start2~title_start15 目前没有逐帧偏移/尺寸数据时，先按与 title_start1
#    同一基准处理；若后续拿到各帧数据，只需逐帧替换对应 LiveComposite 的坐标即可。
#
# 原脚本时序参考：
# - 进入动画的首帧切换近似瞬时（1ms）
# - 后续逐帧动画为 150ms / 帧

init offset = 20

# -----------------------------------------------------------------------------
# 对齐策略
# -----------------------------------------------------------------------------
# 我们取已知 hover 帧 title_start1 的 top-left 作为公共画布原点：
#   origin = (942, 92)
#
# 这样：
# - title_start1 在本地画布内坐标为 (0, 0)
# - title_start   在本地画布内坐标为 (1039-942, 94-92) = (97, 2)
#
# 由于两者底边都落在 y=148，因此本地坐标天然完成“底边对齐”。
#
# 画布大小暂设为 400x80，留出余量给后续帧使用；若未来发现某些帧更大，可再扩大。

image title_start_idle_aligned = LiveComposite(
    (400, 80),
    (97, 2), "logo_assets/title_start.png"
)

image title_start_hover_aligned_1 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start1.png"
)

# 下面 2~15 号帧当前按与 title_start1 同一左下角基准处理。
# 若后续获得每一帧的精确 HZC 偏移，请把 (0, 0) 替换成对应的本地坐标。

image title_start_hover_aligned_2 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start2.png"
)

image title_start_hover_aligned_3 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start3.png"
)

image title_start_hover_aligned_4 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start4.png"
)

image title_start_hover_aligned_5 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start5.png"
)

image title_start_hover_aligned_6 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start6.png"
)

image title_start_hover_aligned_7 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start7.png"
)

image title_start_hover_aligned_8 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start8.png"
)

image title_start_hover_aligned_9 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start9.png"
)

image title_start_hover_aligned_10 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start10.png"
)

image title_start_hover_aligned_11 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start11.png"
)

image title_start_hover_aligned_12 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start12.png"
)

image title_start_hover_aligned_13 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start13.png"
)

image title_start_hover_aligned_14 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start14.png"
)

image title_start_hover_aligned_15 = LiveComposite(
    (400, 80),
    (0, 0), "logo_assets/title_start15.png"
)

# -----------------------------------------------------------------------------
# 悬停动画定义
# -----------------------------------------------------------------------------
# 语义近似：
# - 第 1 帧：近似瞬时切入
# - 第 2~15 帧：150ms/帧
# - repeat：持续悬停时循环播放

image title_start_hover_anim:
    "title_start_hover_aligned_1"
    pause 0.001
    "title_start_hover_aligned_2"
    pause 0.15
    "title_start_hover_aligned_3"
    pause 0.15
    "title_start_hover_aligned_4"
    pause 0.15
    "title_start_hover_aligned_5"
    pause 0.15
    "title_start_hover_aligned_6"
    pause 0.15
    "title_start_hover_aligned_7"
    pause 0.15
    "title_start_hover_aligned_8"
    pause 0.15
    "title_start_hover_aligned_9"
    pause 0.15
    "title_start_hover_aligned_10"
    pause 0.15
    "title_start_hover_aligned_11"
    pause 0.15
    "title_start_hover_aligned_12"
    pause 0.15
    "title_start_hover_aligned_13"
    pause 0.15
    "title_start_hover_aligned_14"
    pause 0.15
    "title_start_hover_aligned_15"
    pause 0.15
    repeat

# -----------------------------------------------------------------------------
# 屏幕示例
# -----------------------------------------------------------------------------
# 注意：这里按钮摆放位置直接使用公共原点 (942, 92)，因为所有对齐后的图像
# 都是在这个原点对应的局部画布里做位置换算的。

screen title_start_hover_demo_screen():
    modal False

    imagebutton:
        idle "title_start_idle_aligned"
        hover "title_start_hover_anim"
        xpos 942
        ypos 92
        focus_mask True
        action NullAction()

    text "将鼠标移动到 START 按钮上，观察 15 帧悬停动画。\n当前示例以底边对齐为基准。" xpos 40 ypos 40 color "#FFFFFF"

label title_start_hover_demo:
    scene black
    show screen title_start_hover_demo_screen
    "这是 title_start 悬停动画的 Ren'Py 示例。"
    "把鼠标移到按钮上即可看到由 title_start1 到 title_start15 组成的逐帧动画。"
    hide screen title_start_hover_demo_screen
    return
