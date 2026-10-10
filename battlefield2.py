import flet as ft
import flet.canvas as cv


# THEMES
SHOW_GRID = True
COLOR_GRID = "#C4C4C4"
BG_PAGE = "#05070F"
BORDER = "#2A2410"


# BATTLE BOARD
class BattleBoard:
    def __init__(self):
        self.image: str = "battle_field.jpg"
        self.width: int = 1100
        self.height: int = 700
        self.cols: int = 10
        self.rows: int = 10
        self.tile_w: int = 96
        self.tile_h: int = 48
        self.origin_x : int = 540
        self.origin_y: int = 200
        self.is_blocked: list = []

cfg_battleboard = BattleBoard()


# AUXILIARY FUNCTIONS
def grid_to_screen(col: int, row: int, cfg: BattleBoard):
    """
    Input: Cols and Rows
    Output: Tuple - Position in pixels
    """
    x = cfg.origin_x + (col - row) * cfg.tile_w/ 2
    y = cfg.origin_y + (col + row) * cfg.tile_h / 2

    return x, y


def screen_to_grid(x: int, y: int, cfg: BattleBoard):
    """
    Input: Position in pixels
    Output: Col and Row
    """
    dx = (x - cfg.origin_x) / (cfg.tile_w / 2)
    dy = (y - cfg.origin_y) / (cfg.tile_h / 2)

    return round((dx + dy) / 2), round((dy-dx) / 2)


def draw_diamond(col, row, paint, cfg: BattleBoard):
    """Draw the battleboard diamond form"""
    cx, cy = grid_to_screen(col, row, cfg)
    hw, hh = cfg.tile_w / 2, cfg.tile_h / 2
    return cv.Path([
        cv.Path.MoveTo(cx, cy - hh),
        cv.Path.LineTo(cx + hw, cy),
        cv.Path.LineTo(cx, cy + hh),
        cv.Path.LineTo(cx - hw, cy),
        cv.Path.Close(),

    ],
        paint=paint,
    )


def outline_paint():
    return ft.Paint(
        color=COLOR_GRID,
        style=ft.PaintingStyle.STROKE, stroke_width=1
    )


def build_static_shapes(cfg: BattleBoard):
    shapes = []
    if SHOW_GRID:
        for r in range(cfg.rows):
            for c in range(cfg.cols):
                shapes.append(draw_diamond(c, r, outline_paint(), cfg))

    return shapes

STATIC_SHAPES = build_static_shapes(cfg_battleboard)


@ft.component
def battle_board():
    grid_overlay = cv.Canvas(shapes=list(STATIC_SHAPES), width=cfg_battleboard.width, height=cfg_battleboard.height)

    background = ft.Image(src=cfg_battleboard.image,
                          width=cfg_battleboard.width,
                          height=cfg_battleboard.height,
                          fit=ft.BoxFit.FILL)

    return ft.Stack(controls=[background, grid_overlay],
                    width=cfg_battleboard.width,
                    height=cfg_battleboard.height,
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
