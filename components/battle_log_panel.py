import flet as ft
import themes as t


def log_row(entry):
    spans = [ft.TextSpan(entry.message + " ")]
    if entry.damage_text:
        spans.append(ft.TextSpan(entry.damage_text, style=ft.TextStyle(color=t.DAMAGE_TEXT)))
    return ft.Text(spans=spans, size=15, color=t.NORMAL_TEXT, font_family="Cinzel")


def battle_log_panel(entries, width: int, height: int):
    return ft.Container(
        width=width, height=height,
        bgcolor=t.CARD_BG,
        border=ft.Border.all(1, t.CARD_BORDER),
        padding=10,
        content=ft.Column(spacing=8, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                          controls=[
                              ft.Text("Battle Log", size=18, color=t.NORMAL_TEXT, font_family="Cinzel"),
                              ft.Container(
                                  expand=True,
                                  bgcolor="#080A12",
                                  border=ft.Border.all(1, t.CARD_BORDER),
                                  padding=8,
                                  content=ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, auto_scroll=True,
                                                    controls=[log_row(e) for e in entries]),
                              ),
                          ]),
    )
