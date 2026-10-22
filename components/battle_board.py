import flet as ft
import flet.canvas as cv
from services.battle_state import BattleState
from services.battle_geometry import (
    is_inside_board, sort_units_by_depth, get_sprite_bounds, tile_to_pixel, pixel_to_tile,
)
from services.battle_actions import can_move, perform_move, perform_attack, get_attack_tiles
from services.assets import asset_file_exists
from components.battle_grid import STATIC_GRID_SHAPES, create_tile_diamond, create_fill_paint
import themes as t
from components.unit_sprite import unit_sprite


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
# COMPONENT
# state e selected_skill vêm da página; on_change(clear_skill=False) avisa a página
# que o estado mudou (para atualizar cards, log e timer).
# `version` só existe para a página poder forçar o re-render deste componente.
# ============================================================
@ft.component
def battle_board(state: BattleState, version: int, selected_skill: str | None, on_change):
    board = state.board
    units = state.units
    _, set_render_tick = ft.use_state(0)

    def force_rerender():
        _drag_state["render_counter"] += 1
        set_render_tick(_drag_state["render_counter"])

    def player_can_act() -> bool:
        return (state.winner is None and not state.input_locked
                and state.current_unit()["team"] == "player")

    # ---------- gesture handlers ----------
    def handle_drag_start(event):
        if not player_can_act():
            return
        unit_id = state.current_unit_id            # só a unidade da vez pode ser arrastada
        unit = units[unit_id]
        if not unit.get("is_draggable"):
            return

        pointer_x, pointer_y = get_pointer_position(event)
        tile_center_x, tile_center_y = tile_to_pixel(unit["col"], unit["row"], board)
        left, top, right, bottom = get_sprite_bounds(unit, tile_center_x, tile_center_y)
        if left <= pointer_x <= right and top <= pointer_y <= bottom:
            _drag_state.update(
                unit_id=unit_id,
                grab_offset_x=pointer_x - tile_center_x,
                grab_offset_y=pointer_y - tile_center_y,
                token_x=tile_center_x,
                token_y=tile_center_y,
            )
            force_rerender()

    def handle_drag_update(event):
        if _drag_state["unit_id"] is None:
            return
        pointer_x, pointer_y = get_pointer_position(event)
        _drag_state["token_x"] = pointer_x - _drag_state["grab_offset_x"]
        _drag_state["token_y"] = pointer_y - _drag_state["grab_offset_y"]
        force_rerender()

    def handle_drag_end(event):
        unit_id = _drag_state["unit_id"]
        if unit_id is None:
            return
        target_col, target_row = pixel_to_tile(_drag_state["token_x"], _drag_state["token_y"], board)
        result = perform_move(state, unit_id, target_col, target_row)   # valida PA, ocupação, limites
        _drag_state["unit_id"] = None
        force_rerender()
        if result["ok"]:
            on_change()
        elif result["reason"] != "already on this tile":
            print(f"[move] {result['reason']}")

    def handle_tap(event):
        """Modo ataque: com uma skill selecionada, clicar no inimigo ataca."""
        if not selected_skill or not player_can_act():
            return
        attacker_id = state.current_unit_id
        attacker_team = units[attacker_id]["team"]
        pointer_x, pointer_y = get_pointer_position(event)

        for unit_id, unit in sort_units_by_depth(units, farthest_first=False):
            if unit["hp"] <= 0 or unit["team"] == attacker_team:
                continue
            center_x, center_y = tile_to_pixel(unit["col"], unit["row"], board)
            left, top, right, bottom = get_sprite_bounds(unit, center_x, center_y)
            if left <= pointer_x <= right and top <= pointer_y <= bottom:
                result = perform_attack(state, attacker_id, unit_id, selected_skill)
                if result["ok"]:
                    on_change(clear_skill=True)
                else:
                    print(f"[attack] {result['reason']}")
                return

    # ---------- layer 1: background ----------
    if asset_file_exists(board.background_image):
        background = ft.Image(src=board.background_image, width=board.width,
                              height=board.height, fit=ft.BoxFit.FILL)
    else:
        background = ft.Container(width=board.width, height=board.height,
                                  bgcolor=t.PLACEHOLDER_BACKGROUND_COLOR)

    # ---------- layer 2: grid + destaques ----------
    grid_shapes = list(STATIC_GRID_SHAPES)
    dragged_unit_id = _drag_state["unit_id"]

    if dragged_unit_id is not None:
        # destino do arraste: verde se can_move, vermelho se não
        hover_col, hover_row = pixel_to_tile(_drag_state["token_x"], _drag_state["token_y"], board)
        if is_inside_board(hover_col, hover_row, board) and (hover_col, hover_row) != (
                units[dragged_unit_id]["col"], units[dragged_unit_id]["row"]):
            is_valid, _, _ = can_move(state, dragged_unit_id, hover_col, hover_row)
            color = t.VALID_TILE_COLOR if is_valid else t.INVALID_TILE_COLOR
            grid_shapes.append(create_tile_diamond(hover_col, hover_row, create_fill_paint(color), board))
    elif selected_skill and player_can_act():
        # modo ataque: destaca os tiles que a skill alcança
        for col, row in get_attack_tiles(state, state.current_unit_id, selected_skill):
            grid_shapes.append(create_tile_diamond(col, row, create_fill_paint(t.ATTACK_TILE_COLOR), board))

    grid_layer = cv.Canvas(shapes=grid_shapes, width=board.width, height=board.height)

    # ---------- layer 3: sprites (só unidades vivas) ----------
    drawn_ids = []
    sprite_controls = []
    for unit_id, unit in sort_units_by_depth(units):
        has_sheet = bool(unit.get("sheet"))
        if unit["hp"] <= 0 and not has_sheet:
            continue  # sem sheet não há animação de morte: some na hora
        if unit_id == dragged_unit_id:
            center_x, center_y = _drag_state["token_x"], _drag_state["token_y"]
        else:
            center_x, center_y = tile_to_pixel(unit["col"], unit["row"], board)

        left, top, _, _ = get_sprite_bounds(unit, center_x, center_y)

        if has_sheet:
            sprite = unit_sprite(unit, left, top)
        elif asset_file_exists(unit["sprite"]):
            sprite = ft.Image(src=unit["sprite"], width=unit["width"],
                              height=unit["height"], fit=ft.BoxFit.CONTAIN)
        else:
            sprite = ft.Container(width=unit["width"], height=unit["height"],
                                  bgcolor=unit["placeholder_color"], border_radius=6)
        sprite.left, sprite.top = left, top
        sprite_controls.append(sprite)
        drawn_ids.append(unit_id)

    if dragged_unit_id is not None and dragged_unit_id in drawn_ids:
        sprite_controls.append(sprite_controls.pop(drawn_ids.index(dragged_unit_id)))

    stage = ft.Stack(
        controls=[background, grid_layer, *sprite_controls],
        width=board.width,
        height=board.height,
    )

    gesture_detector = ft.GestureDetector(
        content=stage,
        on_tap_down=handle_tap,
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
