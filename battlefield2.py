import flet as ft


# THEMES
BG_PAGE = "#05070F"
BORDER = "#2A2410"


# ELEMENTS
BOARD = {
    "image": "battle_field.jpg",
    # Fixed Dimensions
    "width": 1100,
    "height": 700,
}


@ft.component
def battle_board():

    background = ft.Image(src=BOARD["image"],
                          width=BOARD["width"],
                          height=BOARD["height"],
                          fit=ft.BoxFit.FILL)

    return ft.Stack(controls=[background],
                    width=BOARD["width"],
                    height=BOARD["height"]
                    )


@ft.component
def battle_page():

    return ft.Container(
        border=ft.Border.all(1, BORDER),
        border_radius=6,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=battle_board()
    )


def main(page: ft.Page):

    page.title = "Battlefield Board"
    page.padding = 0
    page.render_views(lambda: ft.View(route="/", padding=0, controls=[battle_page()]))
    page.update()


if __name__ == "__main__":
    ft.run(main=main, assets_dir="assets")
