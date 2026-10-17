import copy
from services.battle_geometry import BoardConfig
from services.battle_log import BattleLog, LogEntry

TURN_DURATION = 30

class BattleState:
    def __init__(self, units: dict, board: BoardConfig, turn_duration: int = TURN_DURATION):
        self.units = copy.deepcopy(units)
        self.board = board
        self.turn_order: list[str] = list(self.units.keys())
        self.turn_index : int = 0
        self.round : int = 1
        self.turn_duration: int = turn_duration
        self.time_left = turn_duration
        self.winner: str | None = None
        self.log = BattleLog()

        # UI Flags
        self.input_locked = False  # True when enemy is playing
        self.closed = False  # TODO: Check if its necessary
        self.version = 0  # Force UI re-render


    # Getters
    @property
    def current_unit_id(self) -> str:
        return self.turn_order[self.turn_index]

    def current_unit(self) -> dict:
        return self.units[self.current_unit_id]

    def is_alive(self, unit_id: str) -> bool:
        return self.units[unit_id]["hp"] > 0

    def unit_at(self, col: int, row: int) -> str | None:
        """Id da unidade VIVA naquele tile (ou None)."""
        for unit_id, unit in self.units.items():
            if unit["hp"] > 0 and unit["col"] == col and unit["row"] == row:
                return unit_id
        return None


    # Turns
    def refill_ap(self, unit_id: str) -> None:
        unit = self.units[unit_id]
        unit["ap"] = unit["max_ap"]

    def end_turn(self) -> None:
        if self.winner:
            return
        count = len(self.turn_order)
        for _ in range(count):
            self.turn_index += 1
            if self.turn_index >= count:
                self.turn_index = 0
                self.round += 1
            if self.is_alive(self.current_unit_id):
                break
        self.time_left = self.turn_duration
        self.refill_ap(self.current_unit_id)

    def tick(self) -> bool:
        """Called each second by UI. Return True if the time is over and the turn ends up"""
        if self.winner:
            return False
        self.time_left -= 1
        if self.time_left <= 0:
            self.end_turn()
            return True
        return False


    # Battle End
    def check_battle_end(self) -> str | None:
        player_alive = any(u["team"] == "player" and u["hp"] > 0 for u in self.units.values())
        enemy_alive = any(u["team"] == "enemy" and u["hp"] > 0 for u in self.units.values())
        if self.winner is None:
            if not enemy_alive:
                self.winner = "victory"
            elif not player_alive:
                self.winner = "defeat"
            if self.winner:
                self.log.add(LogEntry(round=self.round, kind="end", result=self.winner))
        return self.winner
