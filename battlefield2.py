import os
import flet as ft
import flet.canvas as cv


# ============================================================
# THEME
# ============================================================
SHOW_GRID = True
GRID_LINE_COLOR = "#C4C4C4"
PAGE_BACKGROUND_COLOR = "#05070F"
PLACEHOLDER_BACKGROUND_COLOR = "#1A1712"
BOARD_BORDER_COLOR = "#2A2410"
VALID_TILE_COLOR = ft.Colors.with_opacity(0.40, "#D4AF37")
INVALID_TILE_COLOR = ft.Colors.with_opacity(0.40, "#B3261E")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ============================================================
# BOARD CONFIGURATION
# ============================================================
class BoardConfig:
    def __init__(self):
        self.background_image: str = "battle_field.jpg"

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


board_config = BoardConfig()


# ============================================================
# UNITS
# ============================================================

# MOCKUPS
INITIAL_UNITS = {
    "hero": {
        "sprite": "hero3.gif", "width": 62, "height": 110,
        "col": 0, "row": 4, "is_draggable": True,
        "placeholder_color": "#2E5BFF",
        "offset_x": 0, "offset_y": 20,
    },
    "monster": {
        "sprite": "monster.gif", "width": 50, "height": 50,
        "col": 9, "row": 4, "is_draggable": True,
        "placeholder_color": "#B3261E",
        "offset_x": 0, "offset_y": 6,
    },
}


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
    """
    Return (left, top, right, bottom) of the sprite box for a given tile center.
    The sprite is anchored by its FEET
    """
    left = tile_center_x - unit["width"] / 2 + unit.get("offset_x", 0)
    top = tile_center_y - unit["height"] + unit.get("offset_y", 0)
    return left, top, left + unit["width"], top + unit["height"]


# ============================================================
# DRAG STATE
# ============================================================
_drag_state = {
    "unit_id": None,        # unit being dragged, or None when idle
    "grab_offset_x": 0.0,   # pointer minus tile center at the moment of the grab
    "grab_offset_y": 0.0,
    "token_x": 0.0,         # current "virtual tile center" of the dragged unit, in pixels
    "token_y": 0.0,
    "render_counter": 0,    # ever-increasing value used only to trigger re-renders
}


def get_pointer_position(event) -> tuple[float, float]:
    """Pointer position relative to the stage (works across Flet versions)."""
    position = getattr(event, "local_position", None)
    if position is not None:
        return position.x, position.y
    return event.local_x, event.local_y


# ============================================================
# ISOMETRIC MATH
# ============================================================
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


def asset_file_exists(file_name: str) -> bool:
    return os.path.exists(os.path.join(ASSETS_DIR, file_name))


# ============================================================
# GRID DRAWING
# ============================================================
def create_outline_paint() -> ft.Paint:
    return ft.Paint(color=GRID_LINE_COLOR, style=ft.PaintingStyle.STROKE, stroke_width=1)


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
    if SHOW_GRID:
        for row in range(board.row_count):
            for col in range(board.column_count):
                shapes.append(create_tile_diamond(col, row, create_outline_paint(), board))
    for col, row in board.blocked_tiles:
        shapes.append(create_tile_diamond(col, row, create_fill_paint(INVALID_TILE_COLOR), board))
    return shapes


# Built once at import time: re-creating ~100 shapes on every pointer move is wasteful.
STATIC_GRID_SHAPES = build_static_grid_shapes(board_config)


# ============================================================
# COMPONENT
# ============================================================
@ft.component
def battle_board():
    board = board_config
    units, set_units = ft.use_state(INITIAL_UNITS)
    _, set_render_tick = ft.use_state(0)

    def force_rerender():
        # Flet re-renders only when a state value changes. _drag_state is a plain
        # dict, so we bump a counter to guarantee a new value every time.
        _drag_state["render_counter"] += 1
        set_render_tick(_drag_state["render_counter"])

    def is_valid_destination(unit_id: str, col: int, row: int) -> bool:
        if not is_inside_board(col, row, board):
            return False
        if (col, row) in board.blocked_tiles:
            return False
        # Occupied by ANOTHER unit? The dragged unit is excluded so it can
        # be dropped back on its own tile.
        return not any(
            other["col"] == col and other["row"] == row
            for other_id, other in units.items()
            if other_id != unit_id
        )

    # ---------- gesture handlers ----------
    def handle_drag_start(event):
        pointer_x, pointer_y = get_pointer_position(event)

        # Hit test: topmost unit first, so overlapping sprites pick the visible one.
        for unit_id, unit in sort_units_by_depth(units, farthest_first=False):
            if not unit.get("is_draggable"):
                continue
            tile_center_x, tile_center_y = tile_to_pixel(unit["col"], unit["row"], board)
            left, top, right, bottom = get_sprite_bounds(unit, tile_center_x, tile_center_y)
            if left <= pointer_x <= right and top <= pointer_y <= bottom:
                _drag_state.update(
                    unit_id=unit_id,
                    # Remember WHERE inside the sprite it was grabbed, so it does not jump.
                    grab_offset_x=pointer_x - tile_center_x,
                    grab_offset_y=pointer_y - tile_center_y,
                    token_x=tile_center_x,
                    token_y=tile_center_y,
                )
                force_rerender()
                return

    def handle_drag_update(event):
        if _drag_state["unit_id"] is None:
            return
        pointer_x, pointer_y = get_pointer_position(event)
        # ABSOLUTE position (pointer - grab offset) instead of summing deltas,
        # so small errors never accumulate.
        _drag_state["token_x"] = pointer_x - _drag_state["grab_offset_x"]
        _drag_state["token_y"] = pointer_y - _drag_state["grab_offset_y"]
        force_rerender()


    def handle_drag_end(event):
        unit_id = _drag_state["unit_id"]
        if unit_id is None:
            return
        target_col, target_row = pixel_to_tile(_drag_state["token_x"], _drag_state["token_y"], board)
        if is_valid_destination(unit_id, target_col, target_row):
            # Build NEW dicts: Flet only re-renders when it receives a new object.
            set_units({**units, unit_id: {**units[unit_id], "col": target_col, "row": target_row}})
        # Invalid drop needs no special case: units is unchanged, so the unit
        # is simply drawn on its old tile again.
        _drag_state["unit_id"] = None
        force_rerender()

    # ---------- layer 1: background ----------
    if asset_file_exists(board.background_image):
        background = ft.Image(src=board.background_image, width=board.width,
                              height=board.height, fit=ft.BoxFit.FILL)  # FILL keeps 1:1 with the canvas
    else:
        background = ft.Container(width=board.width, height=board.height,
                                  bgcolor=PLACEHOLDER_BACKGROUND_COLOR)


    # ---------- layer 2: grid + drop-target highlight ----------
    grid_shapes = list(STATIC_GRID_SHAPES)  # copy, so the highlight is not added to the shared list
    dragged_unit_id = _drag_state["unit_id"]
    if dragged_unit_id is not None:
        hover_col, hover_row = pixel_to_tile(_drag_state["token_x"], _drag_state["token_y"], board)
        if is_inside_board(hover_col, hover_row, board):
            is_valid = is_valid_destination(dragged_unit_id, hover_col, hover_row)
            highlight_color = VALID_TILE_COLOR if is_valid else INVALID_TILE_COLOR
            grid_shapes.append(create_tile_diamond(hover_col, hover_row, create_fill_paint(highlight_color), board))

    grid_layer = cv.Canvas(shapes=grid_shapes, width=board.width, height=board.height)


    # ---------- layer 3: unit sprites ----------
    units_by_depth = sort_units_by_depth(units)  # painting order: farthest first
    sprite_controls = []
    for unit_id, unit in units_by_depth:
        if unit_id == dragged_unit_id:
            center_x, center_y = _drag_state["token_x"], _drag_state["token_y"]  # follows the pointer
        else:
            center_x, center_y = tile_to_pixel(unit["col"], unit["row"], board)  # rests on its tile

        left, top, _, _ = get_sprite_bounds(unit, center_x, center_y)

        if asset_file_exists(unit["sprite"]):
            sprite = ft.Image(src=unit["sprite"], width=unit["width"],
                              height=unit["height"], fit=ft.BoxFit.CONTAIN)
        else:
            sprite = ft.Container(width=unit["width"], height=unit["height"],
                                  bgcolor=unit["placeholder_color"], border_radius=6)
        sprite.left, sprite.top = left, top  # absolute position inside the Stack
        sprite_controls.append(sprite)

    # The dragged sprite goes on top of everything. Both lists share the same
    # order, so the unit's index in units_by_depth is its index in sprite_controls.
    if dragged_unit_id is not None:
        dragged_index = [unit_id for unit_id, _ in units_by_depth].index(dragged_unit_id)
        sprite_controls.append(sprite_controls.pop(dragged_index))

    stage = ft.Stack(
        controls=[background, grid_layer, *sprite_controls],
        width=board.width,
        height=board.height,
    )

    gesture_detector = ft.GestureDetector(
        content=stage,
        on_pan_start=handle_drag_start,
        on_pan_update=handle_drag_update,
        on_pan_end=handle_drag_end,
    )

    return ft.Container(
        border=ft.Border.all(1, BOARD_BORDER_COLOR),
        border_radius=6,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=gesture_detector,
    )


@ft.component
def battle_page():
    return ft.Container(
        expand=True,
        bgcolor=PAGE_BACKGROUND_COLOR,
        alignment=ft.Alignment.CENTER,
        content=battle_board(),
    )


def main(page: ft.Page):
    page.title = "Battlefield Board"
    page.bgcolor = PAGE_BACKGROUND_COLOR
    page.padding = 0
    page.render(battle_page)
    page.update()


if __name__ == "__main__":
    ft.run(main=main, assets_dir=ASSETS_DIR)
