"""Tabuleiro isométrico 8x8 - arquivo ÚNICO para testes (sem dependências do projeto).

Uso:
    pip install flet
    python battle_standalone_scaled.py

Estrutura esperada (opcional, ao lado deste arquivo):
    assets/
        battle_field.jpg     <- imagem de fundo
        hero.gif             <- sprite do personagem
        monster.gif          <- sprite do monstro

Se algum arquivo não existir, aparece um placeholder colorido no lugar.

ESCALA: todos os tamanhos (stage, tiles, origem, sprites e offsets) são definidos
na resolução base e multiplicados por SCALE. Mude só o SCALE para redimensionar
tudo junto (0.5 = metade, 1.0 = original, 1.5 = 50% maior...).

ARRASTE (v2): um único GestureDetector cobre o stage inteiro. A posição do token
é calculada a partir da posição ABSOLUTA do ponteiro (menos o ponto onde você
agarrou o sprite), e não somando deltas.
"""
import os

import flet as ft
import flet.canvas as cv


# ============================================================
# CONFIG
# ============================================================
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SHOW_GRID = True          # contornos dos tiles (desligue depois de calibrar)


BOARD = {
    "image": "battle_field.jpg",   # relativo a assets/
    "width": 1100,               # tamanho FIXO do stage, em pixels
    "height": 700,
    "cols": 10,
    "rows": 10,
    "tile_w": 96,               # losango 2:1
    "tile_h": 48,
    "origin_x": 540,            # centro do tile (0,0) na imagem
    "origin_y": 200,
    "blocked": [],                 # ex.: [(3, 3), (4, 3)]
}

INITIAL_UNITS = {
    "hero": {
        "sprite": "hero3.gif",
        "w": 62, "h": 110,
        "col": 0, "row": 4,
        "draggable": True,
        "placeholder": "#2E5BFF",
        "offset_x": 0,
        "offset_y": 20,    # "pés" abaixo do centro do tile
    },
    "monster": {
        "sprite": "monster.gif",
        "w": 50, "h": 50,
        "col": 9, "row": 4,
        "draggable": True,
        "placeholder": "#B3261E",
        "offset_x": 0,
        "offset_y": 6,
    },
}

# Cores
BG_PAGE = "#05070F"
BG_PLACEHOLDER = "#1A1712"
BORDER = "#2A2410"
TITLE = "#D4C48A"
COLOR_GRID = "#C4C4C4"
COLOR_VALID = ft.Colors.with_opacity(0.40, "#D4AF37")
COLOR_INVALID = ft.Colors.with_opacity(0.40, "#B3261E")


# ============================================================
# MATEMÁTICA ISOMÉTRICA (funções puras)
# ============================================================
def grid_to_screen(col: int, row: int, cfg: dict) -> tuple[int, int]:
    """Centro do tile (col,row) em pixels do stage."""
    x = cfg["origin_x"] + (col - row) * cfg["tile_w"] / 2
    y = cfg["origin_y"] + (col + row) * cfg["tile_h"] / 2
    return x, y


def screen_to_grid(x: int, y: int, cfg: dict) -> tuple[int, int]:
    """Pixel -> tile mais próximo (o round() é o 'encaixe')."""
    dx = (x - cfg["origin_x"]) / (cfg["tile_w"] / 2)
    dy = (y - cfg["origin_y"]) / (cfg["tile_h"] / 2)
    return round((dx + dy) / 2), round((dy - dx) / 2)


def in_bounds(col: int, row: int, cfg: dict) -> bool:
    return 0 <= col < cfg["cols"] and 0 <= row < cfg["rows"]


def asset_exists(src: str) -> bool:
    return os.path.exists(os.path.join(ASSETS_DIR, src))


def sprite_box(u, cx, cy, cfg=BOARD):
    left = cx - u["w"] / 2 + u.get("offset_x", 0)
    top = cy - u["h"] + u.get("offset_y", 0)
    return left, top, left + u["w"], top + u["h"]


def pointer_pos(e) -> tuple[int, int]:
    """Posição do ponteiro relativa ao stage (compatível com versões do Flet)."""
    p = getattr(e, "local_position", None)
    if p is not None:
        return p.x, p.y
    return e.local_x, e.local_y


# ============================================================
# DESENHO DOS TILES
# ============================================================
def diamond(col: int, row: int, paint: ft.Paint, cfg: dict) -> cv.Path:
    cx, cy = grid_to_screen(col, row, cfg)
    hw, hh = cfg["tile_w"] / 2, cfg["tile_h"] / 2
    return cv.Path(
        [
            cv.Path.MoveTo(cx, cy - hh),
            cv.Path.LineTo(cx + hw, cy),
            cv.Path.LineTo(cx, cy + hh),
            cv.Path.LineTo(cx - hw, cy),
            cv.Path.Close(),
        ],
        paint=paint,
    )


def outline_paint() -> ft.Paint:
    return ft.Paint(color=COLOR_GRID, style=ft.PaintingStyle.STROKE, stroke_width=1)


def fill_paint(color: str) -> ft.Paint:
    return ft.Paint(color=color, style=ft.PaintingStyle.FILL)


def build_static_shapes(cfg: dict) -> list:
    """Contornos + tiles bloqueados: não mudam durante o arraste, então são montados uma vez."""
    shapes = []
    if SHOW_GRID:
        for r in range(cfg["rows"]):
            for c in range(cfg["cols"]):
                shapes.append(diamond(c, r, outline_paint(), cfg))
    for c, r in cfg["blocked"]:
        shapes.append(diamond(c, r, fill_paint(COLOR_INVALID), cfg))
    return shapes


STATIC_SHAPES = build_static_shapes(BOARD)


# ============================================================
# ESTADO DO ARRASTE
# Dicionário mutável: sempre guarda o valor MAIS RECENTE, independente de qual
# render o handler pertence (evita o problema de closure velha).
# ============================================================
_drag = {
    "uid": None,     # unidade sendo arrastada
    "gx": 0.0,       # offset do ponteiro em relação ao centro do tile do token
    "gy": 0.0,
    "x": 0.0,        # posição atual do token (centro do "tile" em pixels)
    "y": 0.0,
    "n": 0,          # contador para forçar re-render
}


# ============================================================
# COMPONENTE DO TABULEIRO
# ============================================================
@ft.component
def battle_board():
    cfg = BOARD
    units, set_units = ft.use_state(INITIAL_UNITS)
    _, set_tick = ft.use_state(0)

    def refresh():
        _drag["n"] += 1
        set_tick(_drag["n"])

    def is_valid_target(uid: str, col: int, row: int) -> bool:
        if not in_bounds(col, row, cfg):
            return False
        if (col, row) in cfg["blocked"]:
            return False
        return not any(
            u["col"] == col and u["row"] == row
            for k, u in units.items() if k != uid
        )

    # ---------- handlers (um só detector para o stage inteiro) ----------
    def on_start(e):
        px, py = pointer_pos(e)
        # testa do mais "à frente" (col+row maior) para o mais "ao fundo"
        for uid, u in sorted(units.items(), key=lambda kv: kv[1]["col"] + kv[1]["row"], reverse=True):
            if not u.get("draggable"):
                continue
            cx, cy = grid_to_screen(u["col"], u["row"], cfg)
            left, top, right, bottom = sprite_box(u, cx, cy, cfg)
            if left <= px <= right and top <= py <= bottom:
                _drag.update(uid=uid, gx=px - cx, gy=py - cy, x=cx, y=cy)
                refresh()
                return

    def on_update(e):
        if _drag["uid"] is None:
            return
        px, py = pointer_pos(e)
        _drag["x"] = px - _drag["gx"]
        _drag["y"] = py - _drag["gy"]
        refresh()

    def on_end(e):
        uid = _drag["uid"]
        if uid is None:
            return
        col, row = screen_to_grid(_drag["x"], _drag["y"], cfg)
        if is_valid_target(uid, col, row):
            set_units({**units, uid: {**units[uid], "col": col, "row": row}})
        # inválido = volta pro tile antigo
        _drag["uid"] = None
        refresh()

    # ---------- camada 1: fundo ----------
    if asset_exists(cfg["image"]):
        background = ft.Image(
            src=cfg["image"],
            width=cfg["width"],
            height=cfg["height"],
            fit=ft.BoxFit.FILL,   # FILL mantém o mapeamento 1:1 com o canvas
        )
    else:
        background = ft.Container(
            width=cfg["width"], height=cfg["height"], bgcolor=BG_PLACEHOLDER,
        )

    # ---------- camada 2: grid + highlight do tile alvo ----------
    shapes = list(STATIC_SHAPES)
    if _drag["uid"] is not None:
        c, r = screen_to_grid(_drag["x"], _drag["y"], cfg)
        if in_bounds(c, r, cfg):
            color = COLOR_VALID if is_valid_target(_drag["uid"], c, r) else COLOR_INVALID
            shapes.append(diamond(c, r, fill_paint(color), cfg))

    grid_overlay = cv.Canvas(shapes=shapes, width=cfg["width"], height=cfg["height"])

    # ---------- camada 3: tokens (ordenados por profundidade) ----------
    tokens = []
    for uid, u in sorted(units.items(), key=lambda kv: kv[1]["col"] + kv[1]["row"]):
        if _drag["uid"] == uid:
            cx, cy = _drag["x"], _drag["y"]
        else:
            cx, cy = grid_to_screen(u["col"], u["row"], cfg)

        left, top, _, _ = sprite_box(u, cx, cy, cfg)

        if asset_exists(u["sprite"]):
            visual = ft.Image(src=u["sprite"], width=u["w"], height=u["h"], fit=ft.BoxFit.CONTAIN)
        else:
            visual = ft.Container(
                width=u["w"], height=u["h"],
                bgcolor=u["placeholder"], border_radius=6,
            )
        visual.left, visual.top = left, top
        tokens.append(visual)

    # O token arrastado fica por cima de todos
    if _drag["uid"] is not None:
        idx = [k for k, _ in sorted(units.items(), key=lambda kv: kv[1]["col"] + kv[1]["row"])]
        pos = idx.index(_drag["uid"])
        tokens.append(tokens.pop(pos))

    stage = ft.Stack(
        controls=[background, grid_overlay, *tokens],
        width=cfg["width"],
        height=cfg["height"],
    )

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
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Container(
                    border=ft.Border.all(1, BORDER),
                    border_radius=6,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=battle_board(),
                ),
            ],
        ),
    )


# ============================================================
# ENTRYPOINT
# ============================================================
def main(page: ft.Page):
    page.title = "Battle Board - teste"
    page.bgcolor = BG_PAGE
    page.padding = 0

    try:
        page.render(battle_page)            # Flet 1.0 (declarativo)
    except AttributeError:
        # fallback: mesmo padrão usado no main.py do projeto
        page.render_views(lambda: ft.View(route="/", padding=0, controls=[battle_page()]))
    page.update()


if __name__ == "__main__":
    ft.run(main=main, assets_dir=ASSETS_DIR)
