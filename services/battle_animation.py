"""Animação por sprite sheet: carrega o JSON, guarda o clip atual da unidade
e calcula qual frame desenhar a partir do tempo (função pura)."""
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from config import ASSETS_DIR

DEFAULT_ANIM = "idle"
DEFAULT_FACING = "se"


@dataclass(frozen=True)
class Clip:
    row: int
    frames: int
    fps: float = 8
    loop: bool = True
    hold_last: bool = False

    @property
    def duration(self) -> float:
        return self.frames / self.fps


@dataclass(frozen=True)
class SpriteSheet:
    src: str
    frame_w: int
    frame_h: int
    cols: int
    rows: int
    anchor_x: int      # pés do personagem dentro do frame
    anchor_y: int
    clips: dict


@lru_cache(maxsize=None)
def get_sheet(name: str) -> SpriteSheet:
    path = Path(ASSETS_DIR) / "sprites" / name / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    clips = {key: Clip(**value) for key, value in data.pop("clips").items()}
    return SpriteSheet(**data, clips=clips)


def _find_clip(sheet: SpriteSheet, anim: str, facing: str) -> Clip:
    """Clip pedido; se não existir, idle na mesma direção; por último, o primeiro clip."""
    for key in (f"{anim}_{facing}", f"{DEFAULT_ANIM}_{facing}"):
        if key in sheet.clips:
            return sheet.clips[key]
    return next(iter(sheet.clips.values()))


def play(unit: dict, anim: str) -> None:
    """Começa um clip ("attack", "hurt", "dead"...). Unidade morta não troca mais de clip."""
    if unit.get("anim") == "dead":
        return
    unit["anim"] = anim
    unit["anim_started"] = time.monotonic()


def face_towards(unit: dict, to_col: int, to_row: int) -> None:
    """Vira a unidade para o tile de destino. +col=SE, -col=NW, +row=SW, -row=NE."""
    delta_col, delta_row = to_col - unit["col"], to_row - unit["row"]
    if delta_col == 0 and delta_row == 0:
        return
    if abs(delta_col) >= abs(delta_row):
        unit["facing"] = "se" if delta_col > 0 else "nw"
    else:
        unit["facing"] = "sw" if delta_row > 0 else "ne"


def current_frame(unit: dict, now: float | None = None) -> tuple[int, int]:
    """(linha, coluna) do frame atual na sheet. Não altera a unidade."""
    sheet = get_sheet(unit["sheet"])
    now = time.monotonic() if now is None else now
    facing = unit.get("facing", DEFAULT_FACING)
    clip = _find_clip(sheet, unit.get("anim", DEFAULT_ANIM), facing)
    elapsed = max(0.0, now - unit.get("anim_started", 0.0))
    index = int(elapsed * clip.fps)

    if clip.loop:
        return clip.row, index % clip.frames
    if index < clip.frames:
        return clip.row, index
    if clip.hold_last:
        return clip.row, clip.frames - 1

    # clip de uma vez só terminou: volta para idle
    idle = _find_clip(sheet, DEFAULT_ANIM, facing)
    idle_index = int((elapsed - clip.duration) * idle.fps)
    return idle.row, idle_index % idle.frames