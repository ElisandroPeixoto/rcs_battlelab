from services.battle_state import BattleState
from services.battle_actions import (
    SKILLS, manhattan, in_range, can_attack, can_move, perform_attack, perform_move,
)


def _main_skill(unit: dict) -> str:
    return unit["skills"][0]


def _nearest_enemy_id(state: BattleState, unit_id: str) -> str | None:
    me = state.units[unit_id]
    candidates = [
        (manhattan(me["col"], me["row"], other["col"], other["row"]), other_id)
        for other_id, other in state.units.items()
        if other["team"] != me["team"] and other["hp"] > 0
    ]
    return min(candidates)[1] if candidates else None


def _best_approach_tile(state: BattleState, unit_id: str, target_id: str, skill_name: str):
    unit, target = state.units[unit_id], state.units[target_id]
    skill = SKILLS[skill_name]
    current_distance = manhattan(unit["col"], unit["row"], target["col"], target["row"])

    best_key, best_tile = None, None
    for col in range(state.board.column_count):
        for row in range(state.board.row_count):
            ok, _, cost = can_move(state, unit_id, col, row)
            if not ok:
                continue
            can_hit_from_there = (
                in_range(col, row, target["col"], target["row"], skill["range"])
                and unit["ap"] - cost >= skill["ap_cost"]
            )
            distance = manhattan(col, row, target["col"], target["row"])
            key = (0 if can_hit_from_there else 1, distance, cost)
            if best_key is None or key < best_key:
                best_key, best_tile = key, (col, row)

    if best_key is None:
        return None
    reached_attack_tile = best_key[0] == 0
    if not reached_attack_tile and best_key[1] >= current_distance:
        return None     # não melhora nada, melhor ficar parado
    return best_tile


# BEHAVIORS
def passive(state: BattleState, unit_id: str):
    """Do nothing"""
    return
    yield


def attack_every_turn(state: BattleState, unit_id: str):
    """Attack the closest enemy when its possible - Do not move"""
    skill = _main_skill(state.units[unit_id])
    while not state.winner:
        target_id = _nearest_enemy_id(state, unit_id)
        if target_id is None:
            return
        result = perform_attack(state, unit_id, target_id, skill)
        if not result["ok"]:
            return
        yield


def approach_and_attack(state: BattleState, unit_id: str):
    """If it does not reach the target, move; Attack when its possible and have AP"""
    skill = _main_skill(state.units[unit_id])
    target_id = _nearest_enemy_id(state, unit_id)
    if target_id is None:
        return

    can_hit_now, _ = can_attack(state, unit_id, target_id, skill)
    if not can_hit_now:
        destination = _best_approach_tile(state, unit_id, target_id, skill)
        if destination is not None:
            perform_move(state, unit_id, *destination)
            yield

    yield from attack_every_turn(state, unit_id)


BEHAVIORS = {
    "passive": passive,
    "attack_every_turn": attack_every_turn,
    "approach_and_attack": approach_and_attack,
}


def iter_ai_turn(state: BattleState, unit_id: str):
    behavior = BEHAVIORS.get(state.units[unit_id].get("ai", "passive"), passive)
    yield from behavior(state, unit_id)


def run_ai_turn(state: BattleState, unit_id: str) -> None:
    for _ in iter_ai_turn(state, unit_id):
        pass
