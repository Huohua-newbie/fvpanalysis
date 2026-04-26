# title_main_menu_demo.rpy
#
# 基于 f_00075195 对标题按钮资源与 MotionAnim 逻辑的逆向结果，
# 近似还原 FVP 风格标题界面。
#
# 说明：
# 1. 把本文件放入 Ren'Py 工程的 game/ 目录。
# 2. 把按钮图片放入 game/title/ 目录。
# 3. 本文件尽量使用 Ren'Py 原生 screen / image / ATL 语法，
#    不依赖 Python 块去驱动帧切换逻辑。
# 4. 当前 hover 帧 2~15 的 left/top 若没有逐帧偏移数据，则统一按 hover 第 1 帧原点处理。
# 5. 这些定义会直接提供一个可运行的 `screen main_menu()`。

init offset = 30

default fvp_title_album_unlocked = True

# -----------------------------------------------------------------------------
# START
# 已知：
# - title_start   : top-left=(1039, 94), size=(204, 54)
# - title_start1  : top-left=(942, 92),  size=(338, 56)
# idle 相对 hover1 原点偏移 = (97, 2)
# -----------------------------------------------------------------------------

image title_start_idle_aligned = LiveComposite(
    (500, 120),
    (97, 2), "title/title_start.png"
)

image title_start_hover_aligned_1 = LiveComposite((500, 120), (0, 0), "title/title_start1.png")
image title_start_hover_aligned_2 = LiveComposite((500, 120), (0, 1), "title/title_start2.png")
image title_start_hover_aligned_3 = LiveComposite((500, 120), (0, 1), "title/title_start3.png")
image title_start_hover_aligned_4 = LiveComposite((500, 120), (0, 1), "title/title_start4.png")
image title_start_hover_aligned_5 = LiveComposite((500, 120), (0, 1), "title/title_start5.png")
image title_start_hover_aligned_6 = LiveComposite((500, 120), (0, 1), "title/title_start6.png")
image title_start_hover_aligned_7 = LiveComposite((500, 120), (0, 2), "title/title_start7.png")
image title_start_hover_aligned_8 = LiveComposite((500, 120), (0, 2), "title/title_start8.png")
image title_start_hover_aligned_9 = LiveComposite((500, 120), (0, 2), "title/title_start9.png")
image title_start_hover_aligned_10 = LiveComposite((500, 120), (0, 1), "title/title_start10.png")
image title_start_hover_aligned_11 = LiveComposite((500, 120), (0, 1), "title/title_start11.png")
image title_start_hover_aligned_12 = LiveComposite((500, 120), (0, 1), "title/title_start12.png")
image title_start_hover_aligned_13 = LiveComposite((500, 120), (0, 1), "title/title_start13.png")
image title_start_hover_aligned_14 = LiveComposite((500, 120), (0, 1), "title/title_start14.png")
image title_start_hover_aligned_15 = LiveComposite((500, 120), (0, 1), "title/title_start15.png")

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
# CONTINUE
# 已知：
# - title_continue  : (1040, 195)
# - title_continue1 : (942, 193)
# idle 相对 hover1 原点偏移 = (98, 2)
# -----------------------------------------------------------------------------

image title_continue_idle_aligned = LiveComposite(
    (500, 120),
    (98, 2), "title/title_continue.png"
)

image title_continue_hover_aligned_1 = LiveComposite((500, 120), (0, 0), "title/title_continue1.png")
image title_continue_hover_aligned_2 = LiveComposite((500, 120), (0, 1), "title/title_continue2.png")
image title_continue_hover_aligned_3 = LiveComposite((500, 120), (0, 1), "title/title_continue3.png")
image title_continue_hover_aligned_4 = LiveComposite((500, 120), (0, 1), "title/title_continue4.png")
image title_continue_hover_aligned_5 = LiveComposite((500, 120), (0, 1), "title/title_continue5.png")
image title_continue_hover_aligned_6 = LiveComposite((500, 120), (0, 1), "title/title_continue6.png")
image title_continue_hover_aligned_7 = LiveComposite((500, 120), (0, 2), "title/title_continue7.png")
image title_continue_hover_aligned_8 = LiveComposite((500, 120), (0, 2), "title/title_continue8.png")
image title_continue_hover_aligned_9 = LiveComposite((500, 120), (0, 2), "title/title_continue9.png")
image title_continue_hover_aligned_10 = LiveComposite((500, 120), (0, 1), "title/title_continue10.png")
image title_continue_hover_aligned_11 = LiveComposite((500, 120), (0, 1), "title/title_continue11.png")
image title_continue_hover_aligned_12 = LiveComposite((500, 120), (0, 1), "title/title_continue12.png")
image title_continue_hover_aligned_13 = LiveComposite((500, 120), (0, 1), "title/title_continue13.png")
image title_continue_hover_aligned_14 = LiveComposite((500, 120), (0, 1), "title/title_continue14.png")
image title_continue_hover_aligned_15 = LiveComposite((500, 120), (0, 1), "title/title_continue15.png")

image title_continue_hover_anim:
    "title_continue_hover_aligned_1"
    pause 0.001
    "title_continue_hover_aligned_2"
    pause 0.15
    "title_continue_hover_aligned_3"
    pause 0.15
    "title_continue_hover_aligned_4"
    pause 0.15
    "title_continue_hover_aligned_5"
    pause 0.15
    "title_continue_hover_aligned_6"
    pause 0.15
    "title_continue_hover_aligned_7"
    pause 0.15
    "title_continue_hover_aligned_8"
    pause 0.15
    "title_continue_hover_aligned_9"
    pause 0.15
    "title_continue_hover_aligned_10"
    pause 0.15
    "title_continue_hover_aligned_11"
    pause 0.15
    "title_continue_hover_aligned_12"
    pause 0.15
    "title_continue_hover_aligned_13"
    pause 0.15
    "title_continue_hover_aligned_14"
    pause 0.15
    "title_continue_hover_aligned_15"
    pause 0.15
    repeat

# -----------------------------------------------------------------------------
# ALBUM / OMIT
# 已知：
# - title_album  : (1110, 295)
# - title_album1 : (1013, 293)
# - title_omit   : (1110, 300)
# album idle 相对 hover1 原点偏移 = (97, 2)
# omit  相对 hover1 原点偏移 = (97, 7)
# -----------------------------------------------------------------------------

image title_album_idle_aligned = LiveComposite(
    (500, 120),
    (97, 2), "title/title_album.png"
)

image title_omit_idle_aligned = LiveComposite(
    (500, 120),
    (97, 7), "title/title_omit.png"
)

image title_album_hover_aligned_1 = LiveComposite((500, 120), (0, 0), "title/title_album1.png")
image title_album_hover_aligned_2 = LiveComposite((500, 120), (0, 1), "title/title_album2.png")
image title_album_hover_aligned_3 = LiveComposite((500, 120), (0, 1), "title/title_album3.png")
image title_album_hover_aligned_4 = LiveComposite((500, 120), (0, 1), "title/title_album4.png")
image title_album_hover_aligned_5 = LiveComposite((500, 120), (0, 1), "title/title_album5.png")
image title_album_hover_aligned_6 = LiveComposite((500, 120), (0, 1), "title/title_album6.png")
image title_album_hover_aligned_7 = LiveComposite((500, 120), (0, 2), "title/title_album7.png")
image title_album_hover_aligned_8 = LiveComposite((500, 120), (0, 2), "title/title_album8.png")
image title_album_hover_aligned_9 = LiveComposite((500, 120), (0, 2), "title/title_album9.png")
image title_album_hover_aligned_10 = LiveComposite((500, 120), (0, 1), "title/title_album10.png")
image title_album_hover_aligned_11 = LiveComposite((500, 120), (0, 1), "title/title_album11.png")
image title_album_hover_aligned_12 = LiveComposite((500, 120), (0, 1), "title/title_album12.png")
image title_album_hover_aligned_13 = LiveComposite((500, 120), (0, 1), "title/title_album13.png")
image title_album_hover_aligned_14 = LiveComposite((500, 120), (0, 1), "title/title_album14.png")
image title_album_hover_aligned_15 = LiveComposite((500, 120), (0, 1), "title/title_album15.png")

image title_album_hover_anim:
    "title_album_hover_aligned_1"
    pause 0.001
    "title_album_hover_aligned_2"
    pause 0.15
    "title_album_hover_aligned_3"
    pause 0.15
    "title_album_hover_aligned_4"
    pause 0.15
    "title_album_hover_aligned_5"
    pause 0.15
    "title_album_hover_aligned_6"
    pause 0.15
    "title_album_hover_aligned_7"
    pause 0.15
    "title_album_hover_aligned_8"
    pause 0.15
    "title_album_hover_aligned_9"
    pause 0.15
    "title_album_hover_aligned_10"
    pause 0.15
    "title_album_hover_aligned_11"
    pause 0.15
    "title_album_hover_aligned_12"
    pause 0.15
    "title_album_hover_aligned_13"
    pause 0.15
    "title_album_hover_aligned_14"
    pause 0.15
    "title_album_hover_aligned_15"
    pause 0.15
    repeat

# -----------------------------------------------------------------------------
# OPTION
# 已知：
# - title_option  : (1090, 395)
# - title_option1 : (1003, 393)
# idle 相对 hover1 原点偏移 = (87, 2)
# -----------------------------------------------------------------------------

image title_option_idle_aligned = LiveComposite(
    (500, 120),
    (87, 2), "title/title_option.png"
)

image title_option_hover_aligned_1 = LiveComposite((500, 120), (0, 0), "title/title_option1.png")
image title_option_hover_aligned_2 = LiveComposite((500, 120), (0, 1), "title/title_option2.png")
image title_option_hover_aligned_3 = LiveComposite((500, 120), (0, 1), "title/title_option3.png")
image title_option_hover_aligned_4 = LiveComposite((500, 120), (0, 1), "title/title_option4.png")
image title_option_hover_aligned_5 = LiveComposite((500, 120), (0, 1), "title/title_option5.png")
image title_option_hover_aligned_6 = LiveComposite((500, 120), (0, 1), "title/title_option6.png")
image title_option_hover_aligned_7 = LiveComposite((500, 120), (0, 2), "title/title_option7.png")
image title_option_hover_aligned_8 = LiveComposite((500, 120), (0, 2), "title/title_option8.png")
image title_option_hover_aligned_9 = LiveComposite((500, 120), (0, 2), "title/title_option9.png")
image title_option_hover_aligned_10 = LiveComposite((500, 120), (0, 1), "title/title_option10.png")
image title_option_hover_aligned_11 = LiveComposite((500, 120), (0, 1), "title/title_option11.png")
image title_option_hover_aligned_12 = LiveComposite((500, 120), (0, 1), "title/title_option12.png")
image title_option_hover_aligned_13 = LiveComposite((500, 120), (0, 1), "title/title_option13.png")
image title_option_hover_aligned_14 = LiveComposite((500, 120), (0, 1), "title/title_option14.png")
image title_option_hover_aligned_15 = LiveComposite((500, 120), (0, 1), "title/title_option15.png")

image title_option_hover_anim:
    "title_option_hover_aligned_1"
    pause 0.001
    "title_option_hover_aligned_2"
    pause 0.15
    "title_option_hover_aligned_3"
    pause 0.15
    "title_option_hover_aligned_4"
    pause 0.15
    "title_option_hover_aligned_5"
    pause 0.15
    "title_option_hover_aligned_6"
    pause 0.15
    "title_option_hover_aligned_7"
    pause 0.15
    "title_option_hover_aligned_8"
    pause 0.15
    "title_option_hover_aligned_9"
    pause 0.15
    "title_option_hover_aligned_10"
    pause 0.15
    "title_option_hover_aligned_11"
    pause 0.15
    "title_option_hover_aligned_12"
    pause 0.15
    "title_option_hover_aligned_13"
    pause 0.15
    "title_option_hover_aligned_14"
    pause 0.15
    "title_option_hover_aligned_15"
    pause 0.15
    repeat

# -----------------------------------------------------------------------------
# END
# 已知：
# - title_end  : (1150, 495)
# - title_end1 : (1053, 493)
# idle 相对 hover1 原点偏移 = (97, 2)
# -----------------------------------------------------------------------------

image title_end_idle_aligned = LiveComposite(
    (500, 120),
    (97, 2), "title/title_end.png"
)

image title_end_hover_aligned_1 = LiveComposite((500, 120), (0, 0), "title/title_end1.png")
image title_end_hover_aligned_2 = LiveComposite((500, 120), (0, 1), "title/title_end2.png")
image title_end_hover_aligned_3 = LiveComposite((500, 120), (0, 1), "title/title_end3.png")
image title_end_hover_aligned_4 = LiveComposite((500, 120), (0, 1), "title/title_end4.png")
image title_end_hover_aligned_5 = LiveComposite((500, 120), (0, 1), "title/title_end5.png")
image title_end_hover_aligned_6 = LiveComposite((500, 120), (0, 1), "title/title_end6.png")
image title_end_hover_aligned_7 = LiveComposite((500, 120), (0, 2), "title/title_end7.png")
image title_end_hover_aligned_8 = LiveComposite((500, 120), (0, 2), "title/title_end8.png")
image title_end_hover_aligned_9 = LiveComposite((500, 120), (0, 2), "title/title_end9.png")
image title_end_hover_aligned_10 = LiveComposite((500, 120), (0, 1), "title/title_end10.png")
image title_end_hover_aligned_11 = LiveComposite((500, 120), (0, 1), "title/title_end11.png")
image title_end_hover_aligned_12 = LiveComposite((500, 120), (0, 1), "title/title_end12.png")
image title_end_hover_aligned_13 = LiveComposite((500, 120), (0, 1), "title/title_end13.png")
image title_end_hover_aligned_14 = LiveComposite((500, 120), (0, 1), "title/title_end14.png")
image title_end_hover_aligned_15 = LiveComposite((500, 120), (0, 1), "title/title_end15.png")

image title_end_hover_anim:
    "title_end_hover_aligned_1"
    pause 0.001
    "title_end_hover_aligned_2"
    pause 0.15
    "title_end_hover_aligned_3"
    pause 0.15
    "title_end_hover_aligned_4"
    pause 0.15
    "title_end_hover_aligned_5"
    pause 0.15
    "title_end_hover_aligned_6"
    pause 0.15
    "title_end_hover_aligned_7"
    pause 0.15
    "title_end_hover_aligned_8"
    pause 0.15
    "title_end_hover_aligned_9"
    pause 0.15
    "title_end_hover_aligned_10"
    pause 0.15
    "title_end_hover_aligned_11"
    pause 0.15
    "title_end_hover_aligned_12"
    pause 0.15
    "title_end_hover_aligned_13"
    pause 0.15
    "title_end_hover_aligned_14"
    pause 0.15
    "title_end_hover_aligned_15"
    pause 0.15
    repeat

# -----------------------------------------------------------------------------
# 入场演出补充
# -----------------------------------------------------------------------------
# 依据：
# - f_00075195(1) 本身主要负责装资源并把 logo / 按钮的 alpha 设为 0
# - 真正的标题入场动画发生在其调用者 f_00076122 中
# - 其中可明确读出的效果包括：
#   * 背景 258 ：MotionMoveS2(1500,1000,1500,1000, ..., 3, true)
#       -> 近似理解为背景从 150% 缓慢缩回 100%
#   * logo 265 ：MotionAlpha(0->255, 3500ms) + MotionMoveS2(1025,1000,1025,1000, 3500ms)
#       -> logo 轻微放大后收回，同时淡入
#   * start 1501 ：MotionAlpha(0->255, 3500ms)
#   * continue/album/option/end 1518/1535/1552/1569 ：MotionAlpha(0->255, 3800ms)
# - 因此这里把标题界面补成“背景缩入 + logo/button 渐入”的效果。

transform title_bg_enter:
    subpixel True
    anchor (0.5, 0.5)
    pos (640, 360)
    zoom 1.5
    parallel:
        easeout 32.0 zoom 1.0

transform title_logo_enter:
    subpixel True
    alpha 0.0
    zoom 1.025
    parallel:
        linear 3.5 alpha 1.0
    parallel:
        easeout 3.5 zoom 1.0

transform title_button_enter_fast:
    subpixel True
    alpha 0.0
    linear 3.5 alpha 1.0

transform title_button_enter_slow:
    subpixel True
    alpha 0.0
    linear 3.8 alpha 1.0

# -----------------------------------------------------------------------------
# 实际标题界面
# 放进 Ren'Py 项目后，这个 screen 会直接替换默认 main_menu。
# -----------------------------------------------------------------------------

screen main_menu():
    tag menu
    modal True

    add [title_bg] at title_bg_enter

    # 如有 title_logo1 资源，可直接显示；若没有可注释掉这一行。
    add "title/title_logo1.png" xpos 134 ypos 108 at title_logo_enter

    imagebutton:
        idle "title_start_idle_aligned"
        hover "title_start_hover_anim"
        xpos 942
        ypos 92
        at title_button_enter_fast
        focus_mask True
        action Start()

    imagebutton:
        idle "title_continue_idle_aligned"
        hover "title_continue_hover_anim"
        xpos 942
        ypos 193
        at title_button_enter_slow
        focus_mask True
        action ShowMenu("load")

    if fvp_title_album_unlocked:
        imagebutton:
            idle "title_album_idle_aligned"
            hover "title_album_hover_anim"
            xpos 1013
            ypos 293
            at title_button_enter_slow
            focus_mask True
            action Jump("fvp_album_placeholder")
    else:
        imagebutton:
            idle "title_omit_idle_aligned"
            hover "title_omit_idle_aligned"
            insensitive "title_omit_idle_aligned"
            xpos 1013
            ypos 293
            at title_button_enter_slow
            focus_mask True
            sensitive False
            action NullAction()

    imagebutton:
        idle "title_option_idle_aligned"
        hover "title_option_hover_anim"
        xpos 1003
        ypos 393
        at title_button_enter_slow
        focus_mask True
        action ShowMenu("preferences")

    imagebutton:
        idle "title_end_idle_aligned"
        hover "title_end_hover_anim"
        xpos 1053
        ypos 493
        at title_button_enter_slow
        focus_mask True
        action Quit(confirm=True)

label fvp_album_placeholder:
    scene black
    "这里是 album / gallery 的占位入口。"
    return
