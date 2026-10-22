# BattleBoard Main Class
from services.battle_animation import get_sheet


class BoardConfig:
    def __init__(self):
        self.background_image: str = "battle_field.jpg"
        self.show_grid: bool = True

        # The stage has a FIXED pixel size so that board maths and pointer
        self.width: int = 1100
        self.height: int = 700

        # 10X10 Table
        self.column_count: int = 10
        self.row_count: int = 10

        # Isometric diamond tile, 2:1 ratio
        self.tile_width: int = 96
        self.tile_height: int = 48

        # Pixel position of the CENTER of tile (0, 0) on the stage
        self.origin_x: int = 540
        self.origin_y: int = 200

        # Scenery obstacles as (col, row) pairs
        self.blocked_tiles: list[tuple[int, int]] = []


# Main Functions

def tile_to_pixel(col: int, row: int, board: BoardConfig) -> tuple[float, float]:
    """
    Pixel center of tile (col, row).
    Each tile step is a diagonal vector:
        +1 col -> (+tile_width/2, +tile_height/2)   down-right
        +1 row -> (-tile_width/2, +tile_height/2)   down-left
    Summing both contributions gives (col - row) for X and (col + row) for Y.
    """
    x = board.origin_x + (col - row) * board.tile_width / 2
    y = board.origin_y + (col + row) * board.tile_height / 2
    return x, y


def pixel_to_tile(x: float, y: float, board: BoardConfig) -> tuple[int, int]:
    """
    Nearest tile for a pixel: the inverse of tile_to_pixel.
    round() is what produces the "snap to tile" behavior.
    """
    half_tiles_x = (x - board.origin_x) / (board.tile_width / 2)    # equals col - row
    half_tiles_y = (y - board.origin_y) / (board.tile_height / 2)   # equals col + row
    col = round((half_tiles_x + half_tiles_y) / 2)
    row = round((half_tiles_y - half_tiles_x) / 2)
    return col, row


def is_inside_board(col: int, row: int, board: BoardConfig) -> bool:
    return 0 <= col < board.column_count and 0 <= row < board.row_count


def get_depth(unit: dict) -> int:
    """
    Bigger value = closer to the viewer = drawn on top.
    In isometric view the screen Y grows with (col + row), so that sum is the depth.
    """
    return unit["col"] + unit["row"]


def sort_units_by_depth(units: dict, farthest_first: bool = True) -> list[tuple[str, dict]]:
    """
    Return (unit_id, unit) pairs ordered by depth.
    farthest_first=True  -> painting order (the last one ends up on top).
    farthest_first=False -> hit-test order (the visually topmost unit is tested first).
    """
    return sorted(units.items(), key=lambda item: get_depth(item[1]), reverse=not farthest_first)


def get_sprite_bounds(unit: dict, tile_center_x: float, tile_center_y: float):
    """(left, top, right, bottom) da caixa do sprite; os pés ficam no centro do tile."""
    if unit.get("sheet"):
        sheet = get_sheet(unit["sheet"])
        left = tile_center_x - sheet.anchor_x + unit.get("offset_x", 0)
        top = tile_center_y - sheet.anchor_y + unit.get("offset_y", 0)
        return left, top, left + sheet.frame_w, top + sheet.frame_h

    left = tile_center_x - unit["width"] / 2 + unit.get("offset_x", 0)
    top = tile_center_y - unit["height"] + unit.get("offset_y", 0)
    return left, top, left + unit["width"], top + unit["height"]
