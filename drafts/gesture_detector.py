"""Etapa 5 - arquivo mínimo e executável.

    python etapa5_gesture.py

Mova/clique/arraste sobre o retângulo e olhe o TERMINAL (os print aparecem lá,
não na janela do Flet).
"""
import flet as ft

BOARD = {"width": 1100, "height": 700}
BG_PAGE = "#05070F"
BG_PLACEHOLDER = "#1A1712"
BORDER = "#2A2410"


# ---------- helper: fica FORA do componente, no nível do módulo ----------
def pointer_pos(e):
    p = getattr(e, "local_position")
    return p.x, p.y


# ---------- o componente do tabuleiro ----------
@ft.component
def battle_board():
    cfg = BOARD

    # handlers: ficam DENTRO do componente, antes do return
    def on_start(e):
        print(type(e).__name__, e.local_position)
        print("start", pointer_pos(e))

    def on_update(e):
        print("update", pointer_pos(e))

    def on_end(e):
        print("end")

    # o "stage" (por enquanto só um retângulo de tamanho fixo)
    background = ft.Container(
        width=cfg["width"], height=cfg["height"], bgcolor=BG_PLACEHOLDER,
    )
    stage = ft.Stack(
        controls=[background],
        width=cfg["width"], height=cfg["height"],
    )

    # o return do componente é o GestureDetector envolvendo o stage
    return ft.GestureDetector(
        content=stage,
        on_pan_start=on_start,
        on_pan_update=on_update,
        on_pan_end=on_end,
    )


@ft.component
def battle_page():
    return ft.Container(
        expand=True,
        bgcolor=BG_PAGE,
        alignment=ft.Alignment.CENTER,
        content=ft.Container(
            border=ft.Border.all(1, BORDER),
            border_radius=6,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=battle_board(),
        ),
    )


# ---------- entrypoint: a View sai de um COMPONENTE ----------
@ft.component
def root():
    return ft.View(route="/", padding=0, controls=[battle_page()])


def main(page: ft.Page):
    page.title = "Etapa 5"
    page.bgcolor = BG_PAGE
    page.padding = 0
    page.render_views(root)
    page.update()


if __name__ == "__main__":
    ft.run(main=main)