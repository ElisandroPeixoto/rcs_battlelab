import flet as ft
from components.battle_board import battle_board
import themes as t


@ft.component
def battle_page():
    return ft.Container(
        expand=True,
        bgcolor=t.PAGE_BACKGROUND_COLOR,
        alignment=ft.Alignment.CENTER,
        content=battle_board(),
    )
