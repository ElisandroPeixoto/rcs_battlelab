import flet as ft
from services.battle_animation import get_sheet, current_frame


def unit_sprite(unit: dict, left: float, top: float) -> ft.Container:
    sheet = get_sheet(unit["sheet"])
    row, col = current_frame(unit)
    return ft.Container(
        left=left, top=top,
        width=sheet.frame_w, height=sheet.frame_h,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Stack(
            width=sheet.frame_w, height=sheet.frame_h,
            controls=[
                ft.Image(
                    src=sheet.src,
                    left=-col * sheet.frame_w,
                    top=-row * sheet.frame_h,
                    width=sheet.frame_w * sheet.cols,
                    height=sheet.frame_h * sheet.rows,
                    fit=ft.BoxFit.FILL,
                )
            ],
        ),
    )