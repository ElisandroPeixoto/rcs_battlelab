from services.battle_geometry import is_inside_board
from services.battle_state import BattleState
from services.battle_log import LogEntry
from services.battle_animation import play, face_towards


SKILLS = {  # TODO: INSERT ON BACKEND
    "Basic Attack": {
        "ap_cost": 1,
        "damage": 10,
        "range": 1,
        "icon": "Basic Attack.png"
    }
}



def manhattan(col1: int, row1: int, col2: int, row2: int) -> int:
    return abs(col1 - col2) + abs(row1 - row2)


def in_range(col: int, row: int, target_col: int, target_row: int, skill_range: int) -> bool:
    """Target aligned on the same col or row"""
    delta_col, delta_row = abs(col - target_col), abs(row - target_row)
    if delta_col != 0 and delta_row != 0:
        return False
    return 1 <= delta_col + delta_row <= skill_range


# ATTACK

def can_attack(state: BattleState, attacker_id: str, target_id: str, skill_name: str) -> tuple[bool, str]:
    if state.winner:
        return False, "battle is over"
    if state.current_unit_id != attacker_id:
        return False, "not this unit's turn"

    attacker = state.units[attacker_id]
    target = state.units.get(target_id)
    skill = SKILLS.get(skill_name)

    if skill is None or skill_name not in attacker.get("skills", []):
        return False, "unit does not know this skill"
    if target is None or target["hp"] <= 0:
        return False, "invalid target"
    if attacker["team"] == target["team"]:
        return False, "cannot attack an ally"
    if attacker["ap"] < skill["ap_cost"]:
        return False, "not enough AP"
    if not in_range(attacker["col"], attacker["row"], target["col"], target["row"], skill["range"]):
        return False, "target out of range"
    return True, ""


def perform_attack(state: BattleState, attacker_id: str, target_id: str, skill_name: str) -> dict:
    ok, reason = can_attack(state, attacker_id, target_id, skill_name)
    if not ok:
        return {"ok": False, "reason": reason}

    attacker = state.units[attacker_id]
    target = state.units[target_id]
    skill = SKILLS[skill_name]

    attacker["ap"] -= skill["ap_cost"]
    target["hp"] = max(0, target["hp"] - skill["damage"])

    face_towards(attacker, target["col"], target["row"])
    play(attacker, "attack")
    if target["hp"] == 0:
        play(target, "dead")
    else:
        face_towards(target, attacker["col"], attacker["row"])
        play(target, "hurt")

    target_dead = target["hp"] == 0
    if target_dead:
        state.log.add(LogEntry(round=state.round, kind="defeat", target=target["name"]))
        state.check_battle_end()

    return {"ok": True, "reason": "", "damage": skill["damage"], "target_dead": target_dead}


def get_attack_tiles(state: BattleState, unit_id: str, skill_name: str) -> list[tuple[int, int]]:
    """Tiles que a skill alcança a partir da posição atual (para destacar na UI)."""
    unit = state.units[unit_id]
    skill_range = SKILLS[skill_name]["range"]
    tiles = []
    for distance in range(1, skill_range + 1):
        for delta_col, delta_row in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            col, row = unit["col"] + delta_col * distance, unit["row"] + delta_row * distance
            if is_inside_board(col, row, state.board):
                tiles.append((col, row))
    return tiles


# MOVEMENT

def can_move(state: BattleState, unit_id: str, col: int, row: int) -> tuple[bool, str, int]:
    """Returns (ok, reason, AP cost). Cost = 1 AP by tile"""
    if state.winner:
        return False, "battle is over", 0
    if state.current_unit_id != unit_id:
        return False, "not this unit's turn", 0

    unit = state.units[unit_id]
    if (col, row) == (unit["col"], unit["row"]):
        return False, "already on this tile", 0
    if not is_inside_board(col, row, state.board):
        return False, "outside the board", 0
    if (col, row) in state.board.blocked_tiles:
        return False, "tile is blocked", 0

    occupant = state.unit_at(col, row)
    if occupant is not None and occupant != unit_id:
        return False, "tile is occupied", 0

    cost = manhattan(unit["col"], unit["row"], col, row)
    if cost > unit["ap"]:
        return False, "not enough AP", cost
    return True, "", cost


def perform_move(state: BattleState, unit_id: str, col: int, row: int) -> dict:
    ok, reason, cost = can_move(state, unit_id, col, row)
    if not ok:
        return {"ok": False, "reason": reason, "tiles": 0}

    unit = state.units[unit_id]
    face_towards(unit, col, row)
    unit["col"], unit["row"] = col, row
    unit["ap"] -= cost

    state.log.add(LogEntry(round=state.round, kind="move", actor=unit["name"],
                           tiles=cost, dest=(col, row)))
    return {"ok": True, "reason": "", "tiles": cost}
