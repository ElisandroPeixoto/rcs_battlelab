"""Visualizador do cálculo isométrico (Flet 1.0).

    pip install flet
    python iso_visualizer.py

O que você vê:
  - O grid isométrico com os rótulos (col,row) em cada tile.
  - A fórmula como CAMINHO: origem -> col * passo_col (vermelho)
                                   -> row * passo_row (azul) -> tile final.
  - Os valores numéricos da fórmula, atualizados em tempo real.
  - A conversão inversa: clique/arraste no tabuleiro e veja o pixel,
    o (col,row) FRACIONÁRIO antes do round() e o tile escolhido.

Controles:
  - Botões col/row +1/-1  : mexe no tile e vê o token andar na diagonal.
  - Sliders tile_w/tile_h : mude a proporção do losango.
  - Clique ou arraste no canvas: escolhe o tile pelo ponteiro (screen_to_grid).
"""
import flet as ft
import flet.canvas as cv


# ============================================================
# CONFIG
# ============================================================
N = 5                       # grid N x N
STAGE_W, STAGE_H = 640, 480
ORIGIN_X, ORIGIN_Y = 320, 90

BG_PAGE = "#05070F"
CARD_BG = "#0D0F17"
CARD_BORDER = "#2A2410"
TITLE = "#D4C48A"
MUTED = "#7A7568"
GRID = "#6B6B6B"
GOLD = "#D4AF37"
RED = "#E5484D"      # passo_col
BLUE = "#4C8DFF"     # passo_row
GREEN = "#3DD68C"    # ponteiro


# ============================================================
# MATEMÁTICA (as mesmas funções do tabuleiro)
# ============================================================
def grid_to_screen(col, row, w, h):
    x = ORIGIN_X + (col - row) * w / 2
    y = ORIGIN_Y + (col + row) * h / 2
    return x, y


def screen_to_grid_float(x, y, w, h):
    """Antes do round(): coordenadas fracionárias."""
    dx = (x - ORIGIN_X) / (w / 2)
    dy = (y - ORIGIN_Y) / (h / 2)
    return (dx + dy) / 2, (dy - dx) / 2, dx, dy


def pointer_pos(e):
    p = getattr(e, "local_position", None)
    if p is not None:
        return p.x, p.y
    return e.local_x, e.local_y


# ============================================================
# PRIMITIVAS DE DESENHO
# ============================================================
def stroke(color, width=1):
    return ft.Paint(color=color, style=ft.PaintingStyle.STROKE, stroke_width=width)


def fill(color):
    return ft.Paint(color=color, style=ft.PaintingStyle.FILL)


def diamond(cx, cy, w, h, paint):
    return cv.Path(
        [
            cv.Path.MoveTo(cx, cy - h / 2),
            cv.Path.LineTo(cx + w / 2, cy),
            cv.Path.LineTo(cx, cy + h / 2),
            cv.Path.LineTo(cx - w / 2, cy),
            cv.Path.Close(),
        ],
        paint=paint,
    )


def arrow(x1, y1, x2, y2, color, width=3):
    """Linha com ponta de seta. Retorna lista de shapes."""
    shapes = [cv.Line(x1, y1, x2, y2, paint=stroke(color, width))]
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1:
        return shapes
    ux, uy = dx / length, dy / length          # direção unitária
    size = 10
    # duas "asas" da seta, giradas ~±150° em relação à direção
    for sign in (1, -1):
        ax = -ux * 0.87 + sign * -uy * 0.5
        ay = -uy * 0.87 + sign * ux * 0.5
        shapes.append(cv.Line(x2, y2, x2 + ax * size, y2 + ay * size, paint=stroke(color, width)))
    return shapes


def label(x, y, text, color, size=11, bold=False):
    return cv.Text(
        x=x, y=y, value=text,
        alignment=ft.Alignment.CENTER,
        style=ft.TextStyle(size=size, color=color,
                           weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL),
    )


# ============================================================
# COMPONENTES DE UI
# ============================================================
def mono(text, color="#FFFFFF", size=13, bold=False):
    return ft.Text(text, size=size, color=color, font_family="monospace",
                   weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL)


def card(title, controls):
    return ft.Container(
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        border_radius=6,
        padding=12,
        content=ft.Column(
            spacing=4,
            controls=[ft.Text(title, size=14, color=TITLE, weight=ft.FontWeight.BOLD), *controls],
        ),
    )


def step_button(text, on_click, color):
    return ft.Button(
        content=ft.Text(text, size=12),
        bgcolor=color, color="#FFFFFF", width=82, height=34,
        on_click=on_click,
    )


# ============================================================
# TELA
# ============================================================
@ft.component
def visualizer():
    col, set_col = ft.use_state(2)
    row, set_row = ft.use_state(1)
    tile_w, set_tile_w = ft.use_state(96)
    tile_h, set_tile_h = ft.use_state(48)
    pointer, set_pointer = ft.use_state(None)    # (x, y) do último ponteiro

    w, h = tile_w, tile_h

    # ---------- handlers ----------
    def move(dc, dr):
        def handler(e):
            set_col(max(0, min(N - 1, col + dc)))
            set_row(max(0, min(N - 1, row + dr)))
        return handler

    def pick(e):
        px, py = pointer_pos(e)
        set_pointer((px, py))
        c_f, r_f, _, _ = screen_to_grid_float(px, py, w, h)
        c, r = round(c_f), round(r_f)
        if 0 <= c < N and 0 <= r < N:
            set_col(c)
            set_row(r)

    # ---------- desenho ----------
    shapes = []

    # 1) grid + rótulos
    for r in range(N):
        for c in range(N):
            cx, cy = grid_to_screen(c, r, w, h)
            selected = (c == col and r == row)
            if selected:
                shapes.append(diamond(cx, cy, w, h, fill(ft.Colors.with_opacity(0.35, GOLD))))
            shapes.append(diamond(cx, cy, w, h, stroke(GOLD if selected else GRID)))
            shapes.append(label(cx, cy, f"{c},{r}", GOLD if selected else MUTED, bold=selected))

    # 2) caminho vetorial: O -> col*u -> + row*v
    ox, oy = ORIGIN_X, ORIGIN_Y
    u = (w / 2, h / 2)       # passo_col
    v = (-w / 2, h / 2)      # passo_row
    mid = (ox + col * u[0], oy + col * u[1])
    end = (mid[0] + row * v[0], mid[1] + row * v[1])

    shapes += arrow(ox, oy, mid[0], mid[1], RED)
    shapes += arrow(mid[0], mid[1], end[0], end[1], BLUE)

    # 3) vetores-base de referência na origem (curtos, tracejados visuais)
    shapes.append(label(ox + u[0] + 14, oy + u[1] - 14, "u", RED, size=13, bold=True))
    shapes.append(label(ox + v[0] - 14, oy + v[1] - 14, "v", BLUE, size=13, bold=True))

    # 4) origem e token
    shapes.append(cv.Circle(ox, oy, 5, fill("#FFFFFF")))
    shapes.append(label(ox, oy - 14, "origem", "#FFFFFF", size=10))
    shapes.append(cv.Circle(end[0], end[1], 9, fill(GOLD)))
    shapes.append(cv.Circle(end[0], end[1], 9, stroke("#000000", 2)))

    # 5) ponteiro
    if pointer is not None:
        px, py = pointer
        shapes.append(cv.Line(px - 6, py - 6, px + 6, py + 6, paint=stroke(GREEN, 2)))
        shapes.append(cv.Line(px - 6, py + 6, px + 6, py - 6, paint=stroke(GREEN, 2)))

    canvas = cv.Canvas(shapes=shapes, width=STAGE_W, height=STAGE_H)

    board = ft.GestureDetector(
        content=ft.Container(
            width=STAGE_W, height=STAGE_H,
            bgcolor=CARD_BG,
            border=ft.Border.all(1, CARD_BORDER),
            border_radius=6,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=canvas,
        ),
        on_tap_down=pick,
        on_pan_start=pick,
        on_pan_update=pick,
    )

    # ---------- painel numérico ----------
    x_val, y_val = grid_to_screen(col, row, w, h)

    forward = card("grid_to_screen  (tile -> pixel)", [
        mono(f"u = (+w/2, +h/2) = ({w/2:g}, {h/2:g})", RED),
        mono(f"v = (-w/2, +h/2) = ({-w/2:g}, {h/2:g})", BLUE),
        mono(""),
        mono(f"x = {ORIGIN_X} + ({col} - {row}) * {w/2:g}"),
        mono(f"  = {ORIGIN_X} + {(col - row) * w / 2:g} = {x_val:g}", GOLD, bold=True),
        mono(f"y = {ORIGIN_Y} + ({col} + {row}) * {h/2:g}"),
        mono(f"  = {ORIGIN_Y} + {(col + row) * h / 2:g} = {y_val:g}", GOLD, bold=True),
        mono(""),
        mono(f"col*u = ({col * u[0]:g}, {col * u[1]:g})", RED),
        mono(f"row*v = ({row * v[0]:g}, {row * v[1]:g})", BLUE),
    ])

    if pointer is None:
        inverse_lines = [mono("Clique ou arraste no tabuleiro", MUTED)]
    else:
        px, py = pointer
        c_f, r_f, dx, dy = screen_to_grid_float(px, py, w, h)
        inside = 0 <= round(c_f) < N and 0 <= round(r_f) < N
        inverse_lines = [
            mono(f"ponteiro = ({px:.0f}, {py:.0f})", GREEN),
            mono(f"dx = ({px:.0f} - {ORIGIN_X}) / {w/2:g} = {dx:.2f}"),
            mono(f"dy = ({py:.0f} - {ORIGIN_Y}) / {h/2:g} = {dy:.2f}"),
            mono(""),
            mono(f"col = (dx + dy) / 2 = {c_f:.2f}"),
            mono(f"row = (dy - dx) / 2 = {r_f:.2f}"),
            mono(f"round -> ({round(c_f)}, {round(r_f)})", GOLD, bold=True),
            mono("dentro do grid" if inside else "FORA do grid (ignorado)",
                 "#FFFFFF" if inside else RED),
        ]
    inverse = card("screen_to_grid  (pixel -> tile)", inverse_lines)

    controls_card = card("Mover tile", [
        ft.Row(spacing=6, controls=[
            ft.Text("col", color=RED, width=28),
            step_button("-1", move(-1, 0), "#141B33"),
            step_button("+1", move(+1, 0), "#141B33"),
        ]),
        ft.Row(spacing=6, controls=[
            ft.Text("row", color=BLUE, width=28),
            step_button("-1", move(0, -1), "#141B33"),
            step_button("+1", move(0, +1), "#141B33"),
        ]),
        ft.Text(f"tile_w = {w}", color="#FFFFFF", size=12),
        ft.Slider(min=40, max=140, divisions=50, value=w,
                  on_change=lambda e: set_tile_w(int(round(e.control.value)))),
        ft.Text(f"tile_h = {h}   (2:1 => {w // 2})", color="#FFFFFF", size=12),
        ft.Slider(min=20, max=80, divisions=60, value=h,
                  on_change=lambda e: set_tile_h(int(round(e.control.value)))),
    ])

    side = ft.Column(width=380, spacing=10, scroll=ft.ScrollMode.AUTO,
                     controls=[controls_card, forward, inverse])

    return ft.Container(
        expand=True,
        bgcolor=BG_PAGE,
        padding=16,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=16,
            controls=[board, side],
        ),
    )


# ============================================================
# ENTRYPOINT
# ============================================================
@ft.component
def root():
    # Mesmo padrão do view_wrapper do projeto: a View é devolvida por um
    # COMPONENTE (e não por uma função/lambda comum). Sem isso, o re-render
    # disparado pelo use_state não acontece e a tela fica "congelada".
    return ft.View(route="/", padding=0, controls=[visualizer()])


def main(page: ft.Page):
    page.title = "Visualizador isométrico"
    page.bgcolor = BG_PAGE
    page.padding = 0
    page.render_views(root)
    page.update()


if __name__ == "__main__":
    ft.run(main=main)