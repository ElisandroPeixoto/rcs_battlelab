import flet as ft
import themes as t
from services.battle_actions import SKILLS


def skill_button(name: str, skill: dict, is_selected: bool, enabled: bool, on_click):
    icon_src = skill.get("icon")
    icon = ft.Container(
        width=46, height=46,
        bgcolor="#1A1712",
        border=ft.Border.all(2 if is_selected else 1, t.CARD_BORDER_SELECTED if is_selected else t.CARD_BORDER),
        alignment=ft.Alignment.CENTER,
        image=ft.DecorationImage(src=icon_src, fit=ft.BoxFit.COVER),
        content=ft.Icon(ft.Icons.STAR, color=t.TITLE_TEXT, size=22),
    )
    return ft.Container(
        opacity=1 if enabled else 0.4,
        on_click=on_click if enabled else None,
        content=ft.Column(
            spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[icon, ft.Text(name, size=11, color=t.NORMAL_TEXT, font_family="Cinzel")],
        ),
    )


def skills_panel(state, selected_skill: str | None, on_select, width: int, height: int):
    player_turn = (state.winner is None and not state.input_locked
                   and state.current_unit()["team"] == "player")
    unit = state.current_unit() if player_turn else None

    buttons = []
    for name in state.units["hero"]["skills"]:       # skills do personagem do jogador
        skill = SKILLS[name]
        enabled = bool(unit) and unit["ap"] >= skill["ap_cost"]
        buttons.append(skill_button(name, skill, selected_skill == name, enabled,
                                    lambda e, n=name: on_select(n)))

    return ft.Container(
        width=width, height=height,
        bgcolor=t.CARD_BG,
        border=ft.Border.all(1, t.CARD_BORDER),
        padding=10,
        content=ft.Column(spacing=10, controls=[
            ft.Text("Skills", size=18, color=t.NORMAL_TEXT, font_family="Cinzel"),
            ft.Row(spacing=12, controls=buttons),
        ]),
    )
