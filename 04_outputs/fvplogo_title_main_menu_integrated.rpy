# fvplogo_title_integrated.rpy
#
# 单文件整合方案：
# - 把开头 fvplogo 的“退场覆盖层”与 title main menu 放进同一个 main_menu screen
# - 背景在 opening logo 开始淡出时同步淡入/缩入
# - opening logo 完全淡出后，title_logo 与各按钮才开始渐入
# - 由于一切都在同一个 `screen main_menu()` 中完成，因此每次回到标题时，
#   只要主菜单 screen 被重新创建，就会重新播放这整套入场演出
#
# 使用说明：
# 1. 将本文件放入 Ren'Py 工程的 game/ 目录。
# 2. 关闭/移走旧的 `fvplogo.rpy` 与 `title_main_menu.rpy`，避免重复定义 `screen main_menu()`。
# 3. 将标题按钮图片放入 `game/title/` 目录。
# 4. 将开头 FVP logo 演出用图层放入 `game/logo_assets/` 目录：
#       - logo_bg.png
#       - logo_favo.png
#       - logo_favo_view.png
#       - logo_favo_view_p1.png
#       - logo_favo_view_p2.png
#       - logo_favo_view_p3.png
#
# 说明：
# - 本文件尽量只使用 Ren'Py 原生 image / screen / ATL / timer 语法。
# - 不依赖 Python 块去驱动标题逻辑。
# - hover 动画时序遵循逆向结论：首帧约 1ms，其后每帧 150ms。
# - 这里不再只用“一张 opening overlay”代替开头 logo，而是把先前在
#   `logo-test.rpy` 中整理出的那套 opening logo 演出过程直接并入主菜单。

init offset = 40

default fvp_title_album_unlocked = True

# -----------------------------------------------------------------------------
# Opening logo + title background/title logo
# -----------------------------------------------------------------------------
# 根据先前对 f_00074DA5 的分析，这里把 opening logo 的六层图元本身放进标题界面：
# - 0.0s  开始播放开头 logo
# - 1.8s  opening logo 开始退场，同时 title 背景开始“由大到正常”的进入
# - 5.6s  opening logo 彻底退出后，title_logo 与按钮才开始渐入

image fvp_opening_bg = LiveComposite(
    (1280, 720),
    (0, 0), "logo_assets/logo_bg.png"
)
image fvp_opening_favo = LiveComposite(
    (1280, 720),
    (463, 260), "logo_assets/logo_favo.png"
)
image fvp_opening_view = LiveComposite(
    (1280, 720),
    (539, 406), "logo_assets/logo_favo_view.png"
)
image fvp_opening_p1 = LiveComposite(
    (1280, 720),
    (618, 409), "logo_assets/logo_favo_view_p1.png"
)
image fvp_opening_p2 = LiveComposite(
    (1280, 720),
    (618, 404), "logo_assets/logo_favo_view_p2.png"
)
image fvp_opening_p3 = LiveComposite(
    (1280, 720),
    (618, 400), "logo_assets/logo_favo_view_p3.png"
)

image fvp_title_bg = "title/title_bg1_A.png"
image fvp_title_logo = "title/title_logo1.png"

transform fvp_opening_bg_timeline:
    subpixel True
    anchor (0.0, 0.0)
    pos (0, 0)
    alpha 1.0
    pause 1.8
    linear 3.5 alpha 0.0

transform fvp_opening_favo_timeline:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.3333333
    parallel:
        linear 1.8 alpha 1.0
        pause 1.2
        linear 2.5 alpha 0.0
    parallel:
        easeout 1.8 zoom 1.0

transform fvp_opening_view_timeline:
    subpixel True
    transform_anchor True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.3333333
    yoffset 50
    parallel:
        linear 2.0 alpha 1.0
        pause 1.0
        linear 2.5 alpha 0.0
    parallel:
        easeout 2.0 zoom 1.0
    parallel:
        easeout 2.0 yoffset 0

transform fvp_opening_p1_timeline:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate 360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
        pause 1.0
        linear 2.5 alpha 0.0
    parallel:
        easeout 2.0 rotate 0.0
    parallel:
        easeout 2.0 zoom 1.0

transform fvp_opening_p2_timeline:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate 360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
        pause 1.0
        linear 2.5 alpha 0.0
    parallel:
        easeout 2.0 rotate 0.0
    parallel:
        easeout 2.0 zoom 1.0

transform fvp_opening_p3_timeline:
    subpixel True
    transform_anchor True
    anchor (0.4953125, 0.5736111111)
    pos (634, 413)
    alpha 0.0
    rotate -360.0
    zoom 5.0
    parallel:
        linear 2.0 alpha 1.0
        pause 1.0
        linear 2.5 alpha 0.0
    parallel:
        easeout 2.0 rotate 0.0
    parallel:
        easeout 2.0 zoom 1.0

transform fvp_title_bg_enter:
    subpixel True
    anchor (0.5, 0.5)
    pos (640, 360)
    alpha 0.0
    zoom 1.5
    pause 1.8
    parallel:
        linear 3.8 alpha 1.0
    parallel:
        easeout 3.8 zoom 1.0

transform fvp_title_logo_delayed_enter:
    subpixel True
    alpha 0.0
    zoom 1.025
    pause 5.6
    parallel:
        linear 3.5 alpha 1.0
    parallel:
        easeout 3.5 zoom 1.0

transform fvp_title_button_delayed_fast:
    subpixel True
    alpha 0.0
    pause 5.6
    linear 3.5 alpha 1.0

transform fvp_title_button_delayed_slow:
    subpixel True
    alpha 0.0
    pause 5.6
    linear 3.8 alpha 1.0

# -----------------------------------------------------------------------------
# START
# 已知：
# - title_start   : top-left=(1039, 94), size=(204, 54)
# - title_start1  : top-left=(942,  92), size=(338, 56)
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
# -----------------------------------------------------------------------------

image title_album_idle_aligned = LiveComposite((500, 120), (97, 2), "title/title_album.png")
image title_omit_idle_aligned = LiveComposite((500, 120), (97, 7), "title/title_omit.png")

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
# -----------------------------------------------------------------------------

image title_option_idle_aligned = LiveComposite((500, 120), (87, 2), "title/title_option.png")

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
# -----------------------------------------------------------------------------

image title_end_idle_aligned = LiveComposite((500, 120), (97, 2), "title/title_end.png")

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

screen main_menu():
    tag menu
    modal True
    default fvp_menu_ready = False

    timer 5.6 action SetScreenVariable("fvp_menu_ready", True)

    add "fvp_title_bg" at fvp_title_bg_enter

    add "fvp_opening_bg" at fvp_opening_bg_timeline zorder 10
    add "fvp_opening_favo" at fvp_opening_favo_timeline zorder 20
    add "fvp_opening_view" at fvp_opening_view_timeline zorder 30
    add "fvp_opening_p1" at fvp_opening_p1_timeline zorder 40
    add "fvp_opening_p2" at fvp_opening_p2_timeline zorder 41
    add "fvp_opening_p3" at fvp_opening_p3_timeline zorder 42

    add "fvp_title_logo" xpos 476 ypos 295 at fvp_title_logo_delayed_enter zorder 50

    imagebutton:
        idle "title_start_idle_aligned"
        hover "title_start_hover_anim"
        xpos 942
        ypos 92
        at fvp_title_button_delayed_fast
        sensitive fvp_menu_ready
        focus_mask True
        action Start()

    imagebutton:
        idle "title_continue_idle_aligned"
        hover "title_continue_hover_anim"
        xpos 942
        ypos 193
        at fvp_title_button_delayed_slow
        sensitive fvp_menu_ready
        focus_mask True
        action ShowMenu("load")

    if fvp_title_album_unlocked:
        imagebutton:
            idle "title_album_idle_aligned"
            hover "title_album_hover_anim"
            xpos 1013
            ypos 293
            at fvp_title_button_delayed_slow
            sensitive fvp_menu_ready
            focus_mask True
            action Jump("fvp_album_placeholder")
    else:
        imagebutton:
            idle "title_omit_idle_aligned"
            hover "title_omit_idle_aligned"
            insensitive "title_omit_idle_aligned"
            xpos 1013
            ypos 293
            at fvp_title_button_delayed_slow
            sensitive False
            focus_mask True
            action NullAction()

    imagebutton:
        idle "title_option_idle_aligned"
        hover "title_option_hover_anim"
        xpos 1003
        ypos 393
        at fvp_title_button_delayed_slow
        sensitive fvp_menu_ready
        focus_mask True
        action ShowMenu("preferences")

    imagebutton:
        idle "title_end_idle_aligned"
        hover "title_end_hover_anim"
        xpos 1053
        ypos 493
        at fvp_title_button_delayed_slow
        sensitive fvp_menu_ready
        focus_mask True
        action Quit(confirm=True)

label fvp_album_placeholder:
    scene black
    "这里是 album / gallery 的占位入口。"
    return
