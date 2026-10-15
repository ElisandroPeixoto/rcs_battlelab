import flet as ft
import flet.canvas as cv
from services.battle_geometry import BoardConfig, tile_to_pixel
import themes as t

# Battleboard Grid Drawing

def create_outline_paint() -> ft.Paint:
    return ft.Paint(color=t.GRID_LINE_COLOR, style=ft.PaintingStyle.STROKE, stroke_width=1)


def create_fill_paint(color: str) -> ft.Paint:
    return ft.Paint(color=color, style=ft.PaintingStyle.FILL)


def create_tile_diamond(col: int, row: int, paint: ft.Paint, board: BoardConfig) -> cv.Path:
    """Diamond-shaped path for one tile. The paint decides outline vs. fill."""
    center_x, center_y = tile_to_pixel(col, row, board)
    half_width, half_height = board.tile_width / 2, board.tile_height / 2
    return cv.Path(
        [
            cv.Path.MoveTo(center_x, center_y - half_height),   # top
            cv.Path.LineTo(center_x + half_width, center_y),    # right
            cv.Path.LineTo(center_x, center_y + half_height),   # bottom
            cv.Path.LineTo(center_x - half_width, center_y),    # left
            cv.Path.Close(),
        ],
        paint=paint,
    )


def build_static_grid_shapes(board: BoardConfig) -> list:
    """Shapes that never change while dragging: tile outlines and blocked tiles."""
    shapes = []
    if board.show_grid:
        for row in range(board.row_count):
            for col in range(board.column_count):
                shapes.append(create_tile_diamond(col, row, create_outline_paint(), board))
    for col, row in board.blocked_tiles:
        shapes.append(create_tile_diamond(col, row, create_fill_paint(t.INVALID_TILE_COLOR), board))
    return shapes


# Built once at import time: re-creating ~100 shapes on every pointer move is wasteful.
board_config = BoardConfig()
STATIC_GRID_SHAPES = build_static_grid_shapes(board_config)
