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


# UNITS
INITIAL_UNITS = {
    "hero": {
        "sprite": "hero3.gif", "w": 62, "h": 110,
        "col": 0, "row": 4, "draggable": True,
        "offset_x": 0, "offset_y": 20,
    },
    "monster": {
        "sprite": "monster.gif", "w": 50, "h": 50,
        "col": 9, "row": 4, "draggable": True,
        "offset_x": 0, "offset_y": 6,
    },
}

def sprite_box(u: dict, cx: float | int, cy: float | int):
    left = cx - u["w"] / 2 + u.get("offset_x", 0)
    top = cy - u["h"] + u.get("offset_y", 0)
    return left, top, left + u["w"], top + u["h"]


##### ------ AUXILIARY FUNCTIONS ------ #####
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


def draw_diamond(col, row, cfg: BattleBoard):
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
        paint=ft.Paint(color=COLOR_GRID, style=ft.PaintingStyle.STROKE, stroke_width=1),
    )


def build_static_shapes(cfg: BattleBoard):
    shapes = []
    if SHOW_GRID:
        for r in range(cfg.rows):
            for c in range(cfg.cols):
                shapes.append(draw_diamond(c, r, cfg))

    return shapes

STATIC_SHAPES = build_static_shapes(cfg_battleboard)


@ft.component
def battle_board():
    grid_overlay = cv.Canvas(shapes=list(STATIC_SHAPES), width=cfg_battleboard.width, height=cfg_battleboard.height)
    units, set_units = ft.use_state(INITIAL_UNITS)  # Load the units

    # Background Image
    background = ft.Image(src=cfg_battleboard.image,
                          width=cfg_battleboard.width,
                          height=cfg_battleboard.height,
                          fit=ft.BoxFit.FILL)

    # Build the pieces
    tokens = []
    for uid, u in sorted(units.items(), key=lambda kv: kv[1]["col"] + kv[1]["row"]):
        cx, cy = grid_to_screen(u["col"], u["row"], cfg_battleboard)
        left, top, _, _ = sprite_box(u, cx, cy)

        visual = ft.Image(src=u["sprite"], width=u["w"], height=u["h"], fit=ft.BoxFit.CONTAIN)

        visual.left, visual.top = left, top
        tokens.append(visual)


    build_battle_page = ft.Container(border=ft.Border.all(1, BORDER),
                                     border_radius=6,
                                     clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                                     content=ft.Stack(controls=[background, grid_overlay, *tokens],  # Board Elements
                                                      width=cfg_battleboard.width,
                                                      height=cfg_battleboard.height,
                                                      )
                                     )

    return build_battle_page


def main(page: ft.Page):
    page.title = "Battlefield Board"
    page.padding = 0
    page.render_views(lambda: ft.View(route="/", padding=0, controls=[battle_board()]))
    page.update()


if __name__ == "__main__":
    ft.run(main=main, assets_dir="assets")
