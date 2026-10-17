from dataclasses import dataclass


@dataclass
class LogEntry:
    round: int
    kind: str
    result: str = ""


class BattleLog:
    def __init__(self):
        self.entries: list[LogEntry] = []

    def add(self, entry: LogEntry) -> None:
        self.entries.append(entry)
