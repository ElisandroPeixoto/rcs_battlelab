import flet as ft
import themes as t


def turn_panel(state, on_end_turn, on_leave, width: int, height: int):
    can_end_turn = (state.winner is None and not state.input_locked
                    and state.current_unit()["team"] == "player")

    if state.winner == "victory":
        status = "Victory!"
    elif state.winner == "defeat":
        status = "Defeat..."
    elif state.input_locked:
        status = "Enemy turn..."
    else:
        status = f"Time: {state.time_left}s"

    return ft.Container(
        width=width, height=height,
        bgcolor=t.CARD_BG,
        border=ft.Border.all(1, t.CARD_BORDER),
        padding=16,
        content=ft.Column(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(spacing=10, controls=[
                    ft.Text(f"Round: {state.round:02d}", size=20, color=t.NORMAL_TEXT, font_family="Cinzel"),
                    ft.Text(status, size=20, color=t.NORMAL_TEXT, font_family="Cinzel"),
                ]),
                ft.Row(spacing=8, controls=[
                    ft.Button(content=ft.Text("Turn End", font_family="Cinzel", size=16),
                              bgcolor=t.BUTTON_SECONDARY, color=t.NORMAL_TEXT,
                              disabled=not can_end_turn, expand=True, height=46,
                              on_click=on_end_turn),
                    ft.Button(content=ft.Text("Leave", font_family="Cinzel", size=16),
                              bgcolor=t.BUTTON_ALERT, color=t.NORMAL_TEXT,
                              expand=True, height=46, on_click=on_leave),
                ]),
            ],
        ),
    )
