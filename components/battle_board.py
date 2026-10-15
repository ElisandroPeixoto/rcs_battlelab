import flet as ft
import flet.canvas as cv
import os
from services.battle_geometry import BoardConfig
from mockup import INITIAL_UNITS
from config import ASSETS_DIR
from services.battle_geometry import is_inside_board, sort_units_by_depth, get_sprite_bounds, tile_to_pixel, pixel_to_tile
from components.battle_grid import STATIC_GRID_SHAPES, create_tile_diamond, create_fill_paint
import themes as t


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

def asset_file_exists(file_name: str) -> bool:
    return os.path.exists(os.path.join(ASSETS_DIR, file_name))


# ============================================================
# COMPONENT
# ============================================================
@ft.component
def battle_board():
    board = BoardConfig()
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
                                  bgcolor=t.PLACEHOLDER_BACKGROUND_COLOR)


    # ---------- layer 2: grid + drop-target highlight ----------
    grid_shapes = list(STATIC_GRID_SHAPES)  # copy, so the highlight is not added to the shared list
    dragged_unit_id = _drag_state["unit_id"]
    if dragged_unit_id is not None:
        hover_col, hover_row = pixel_to_tile(_drag_state["token_x"], _drag_state["token_y"], board)
        if is_inside_board(hover_col, hover_row, board):
            is_valid = is_valid_destination(dragged_unit_id, hover_col, hover_row)
            highlight_color = t.VALID_TILE_COLOR if is_valid else t.INVALID_TILE_COLOR
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
        border=ft.Border.all(1, t.BOARD_BORDER_COLOR),
        border_radius=6,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=gesture_detector,
    )
