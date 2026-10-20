from dataclasses import dataclass


@dataclass
class LogEntry:
    round: int
    kind: str  # "move" | "attack" | "defeat" | "end"
    actor: str = ""  # who played
    target: str = ""  # who was attacked
    skill: str = ""  # skill used
    damage: int = 0  # how much damage
    tiles: int = 0  # how many tiles moved
    dest: tuple | None = None  # (col, row) destiny
    result: str = ""

    @property
    def message(self) -> str:
        if self.kind == "attack":
            return f"{self.actor} uses {self.skill} in {self.target}:"
        if self.kind == "move":
            plural = "tile" if self.tiles == 1 else "tiles"
            return f"{self.actor} moves {self.tiles} {plural} to ({self.dest[0]}, {self.dest[1]})"
        if self.kind == "defeat":
            return f"{self.target} was defeated"
        if self.kind == "end":
            return "Victory!" if self.result == "victory" else "Defeat..."
        return ""

    @property
    def damage_text(self) -> str:
        return f"-{self.damage} damage" if self.kind == "attack" else ""

    def __str__(self) -> str:
        return f"[R{self.round:02d}] {self.message} {self.damage_text}".strip()


class BattleLog:
    def __init__(self):
        self.entries: list[LogEntry] = []

    def add(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def print_all(self) -> None:
        for entry in self.entries:
            print(entry)
