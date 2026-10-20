import flet as ft
import themes as t


def unit_card(unit: dict, is_active: bool):
    alive = unit["hp"] > 0
    avatar_src = unit.get("avatar")

    avatar = ft.Container(
        width=64, height=64,
        bgcolor="#1A1712",
        border=ft.Border.all(1, t.CARD_BORDER),
        border_radius=2,
        image=ft.DecorationImage(src=avatar_src, fit=ft.BoxFit.COVER)
    )

    identity = [ft.Text(unit["name"], size=20, color=t.NORMAL_TEXT, font_family="Cinzel")]
    if unit.get("job"):
        identity.append(ft.Text(unit["job"], size=13, color=t.NORMAL_TEXT, font_family="Cinzel"))

    stats = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text(f"HP:  {unit['hp']}/{unit['max_hp']}", size=13, color=t.NORMAL_TEXT, font_family="Cinzel"),
            ft.Text(f"PA:  {unit['ap']}/{unit['max_ap']}", size=13, color=t.NORMAL_TEXT, font_family="Cinzel"),
        ],
    )

    return ft.Container(
        bgcolor=t.CARD_BG,
        border=ft.Border.all(2 if is_active else 1, t.CARD_BORDER_SELECTED if is_active else t.CARD_BORDER),
        padding=8,
        opacity=1 if alive else 0.4,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(spacing=8, controls=[avatar, ft.Column(spacing=2, controls=identity)]),
                stats,
            ],
        ),
    )


def units_panel(state, width: int, height: int):
    """Lista de unidades na ordem dos turnos; a que está jogando fica com borda dourada."""
    cards = [unit_card(state.units[unit_id], unit_id == state.current_unit_id and state.winner is None)
             for unit_id in state.turn_order]
    return ft.Container(
        width=width, height=height,
        bgcolor=t.CARD_BG,
        border=ft.Border.all(1, t.CARD_BORDER),
        padding=8,
        content=ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, controls=cards),
    )
