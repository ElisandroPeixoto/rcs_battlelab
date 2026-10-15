import os
import flet as ft
import themes as t
from services.battle_geometry import BoardConfig
from pages.battle_page import battle_page


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
board_config = BoardConfig()


def main(page: ft.Page):
    page.title = "Battlefield Board"
    page.bgcolor = t.PAGE_BACKGROUND_COLOR
    page.padding = 0
    page.render(battle_page)
    page.update()


if __name__ == "__main__":
    ft.run(main=main, assets_dir=ASSETS_DIR)
