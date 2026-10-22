"""Converte .spr + .act do Ragnarok Online em sprite sheet PNG + JSON de clips.

No RO, corpo, cabeça e arma são arquivos separados que o cliente junta em tempo real.
Este script faz o mesmo: a cabeça é encaixada pelos anchors do .act e a arma é
desenhada na origem do corpo. Cada clip é montado num canvas único, com os pés fixos.

Corpo + cabeça + arma (caminhos com ou sem extensão):

    python tools/ro_to_sheet.py art_source/novice/novice novice \\
        --head art_source/novice/novice_head --weapon art_source/novice/weapon

Só corpo (jogador sem cabeça, ou monstro):

    python tools/ro_to_sheet.py art_source/poring/poring poring --kind monster

Saída padrão: assets/sprites/<nome>/<nome>_sheet.png e <nome>.json
Use --preview prévia.png para gerar uma imagem com a grade dos frames para conferir.
"""
import argparse
import json
import struct
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from spr_to_frames import read_spr

# clip -> tipo de ação do RO (índice // 8). Jogadores e monstros têm layouts diferentes.
CLIP_TYPES = {
    "player": {"idle": 0, "walk": 1, "attack": 5, "hurt": 6, "dead": 8},
    "monster": {"idle": 0, "walk": 1, "attack": 2, "hurt": 3, "dead": 4},
}
# Jogador armado: o RO só desenha a arma em standby (4) e attack2 (10) neste arquivo de arma.
ARMED_TYPES = {"idle": 4, "attack": 10}
# No jogador, os 3 "frames" de stand(0)/sit(2) são variações da virada de cabeça, não animação.
STATIC_PLAYER_TYPES = {0, 2}

# Direção do RO (índice % 8). No tabuleiro isométrico: +col = SE, -col = NW, +row = SW, -row = NE
DIRECTIONS = {7: "se", 1: "sw", 3: "nw", 5: "ne"}
# Ordem de desenho das partes (da de trás para a da frente). Ajuste aqui se a arma
# ficar na frente/atrás errada em alguma direção.
DRAW_ORDER = {d: ("body", "head", "weapon") for d in DIRECTIONS.values()}

CLIP_RULES = {
    "idle": {"loop": True},
    "walk": {"loop": True},
    "attack": {"loop": False},
    "hurt": {"loop": False},
    "dead": {"loop": False, "hold_last": True},
}


def strip_ext(path: str) -> str:
    p = Path(path)
    return str(p.with_suffix("")) if p.suffix.lower() in (".spr", ".act") else str(p)


def read_act(path: str) -> list[dict]:
    """Ações -> motions -> layers (x, y, sprite, espelhado, xs, ys) + anchors [(x, y)]."""
    d = Path(path).read_bytes()
    if d[:2] != b"AC":
        raise ValueError(f"{path}: não é um arquivo ACT")
    ver = d[3] * 256 + d[2]
    n_actions = struct.unpack_from("<H", d, 4)[0]
    pos = 16
    actions = []
    for _ in range(n_actions):
        n_motions = struct.unpack_from("<I", d, pos)[0]; pos += 4
        motions = []
        for _ in range(n_motions):
            pos += 32
            n_layers = struct.unpack_from("<I", d, pos)[0]; pos += 4
            layers = []
            for _ in range(n_layers):
                x, y, spr, flags = struct.unpack_from("<iiiI", d, pos); pos += 16
                xs = ys = 1.0
                if ver >= 0x0200:
                    pos += 4                                  # cor
                    xs = ys = struct.unpack_from("<f", d, pos)[0]; pos += 4
                    if ver >= 0x0204:
                        ys = struct.unpack_from("<f", d, pos)[0]; pos += 4
                    pos += 8                                  # rotação + tipo de sprite
                    if ver >= 0x0205:
                        pos += 8
                layers.append((x, y, spr, bool(flags & 1), xs, ys))
            anchors = []
            if ver >= 0x0200:
                pos += 4                                      # id de evento
            if ver >= 0x0203:
                n_anchors = struct.unpack_from("<i", d, pos)[0]; pos += 4
                for _ in range(n_anchors):
                    _, ax, ay, _ = struct.unpack_from("<iiii", d, pos); pos += 16
                    anchors.append((ax, ay))
            motions.append({"layers": layers, "anchors": anchors})
        actions.append({"motions": motions, "delay_ms": 150.0})
    if ver >= 0x0201:
        pos += 4 + 40 * struct.unpack_from("<I", d, pos)[0]
    if ver >= 0x0202:
        for a in actions:
            a["delay_ms"] = struct.unpack_from("<f", d, pos)[0] * 25; pos += 4
    return actions


class Part:
    def __init__(self, path: str):
        base = strip_ext(path)
        self.frames = read_spr(base + ".spr")
        self.actions = read_act(base + ".act")


def place(layer, frames):
    """(imagem já espelhada/escalada, x, y do canto sup. esq. relativo à origem) ou None."""
    x, y, spr, mirror, xs, ys = layer
    if not 0 <= spr < len(frames):
        return None                                           # layer vazio (índice -1)
    img = frames[spr]
    if mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if (xs, ys) != (1.0, 1.0):
        img = img.resize((max(1, round(img.width * xs)), max(1, round(img.height * ys))), Image.NEAREST)
    return img, x - img.width // 2, y - img.height // 2


def motion_of(part: Part, action: int, motion: int):
    if action >= len(part.actions) or not part.actions[action]["motions"]:
        return None
    motions = part.actions[action]["motions"]
    return motions[min(motion, len(motions) - 1)]


def first_anchor(motion):
    return motion["anchors"][0] if motion and motion["anchors"] else None


def render_parts(parts: dict, action: int, motion: int, order: tuple) -> list:
    """[(img, x, y)] relativos à origem (pés) do corpo, na ordem de desenho."""
    body_anchor = first_anchor(motion_of(parts["body"], action, motion))
    out = []
    for name in order:
        part = parts.get(name)
        m = motion_of(part, action, motion) if part else None
        if not m:
            continue
        dx = dy = 0
        if name == "head":                                    # cabeça = anchor do corpo - anchor da cabeça
            head_anchor = first_anchor(m)
            if body_anchor and head_anchor:
                dx, dy = body_anchor[0] - head_anchor[0], body_anchor[1] - head_anchor[1]
        for layer in m["layers"]:
            placed = place(layer, part.frames)
            if placed:
                img, x, y = placed
                out.append((img, x + dx, y + dy))
    return out


def build(body, name, out_dir, head=None, weapon=None, kind="auto", idle=None, attack=None, preview=None):
    parts = {"body": Part(body)}
    if head:
        parts["head"] = Part(head)
    if weapon:
        parts["weapon"] = Part(weapon)
    n_actions = len(parts["body"].actions)
    if kind == "auto":                                        # ACT de jogador tem ~100 ações; monstro ~40
        kind = "monster" if n_actions <= 48 else "player"
    print(f"{n_actions} ações no .act do corpo -> tratado como {kind} | partes: {', '.join(parts)}")

    clip_types = dict(CLIP_TYPES[kind])
    if kind == "player" and weapon:
        clip_types.update(ARMED_TYPES)
    if idle is not None:
        clip_types["idle"] = idle
    if attack is not None:
        clip_types["attack"] = attack
    print("tipos de ação:", clip_types)

    # 1) lista de (clip, ação) e extensão máxima do corpo em torno da origem
    wanted = []
    for clip, type_id in clip_types.items():
        for dir_id, dir_name in DIRECTIONS.items():
            idx = type_id * 8 + dir_id
            if idx < n_actions and parts["body"].actions[idx]["motions"]:
                wanted.append((f"{clip}_{dir_name}", clip, type_id, dir_name, idx))

    def motions_for(clip, type_id, idx):
        count = len(parts["body"].actions[idx]["motions"])
        if kind == "player" and type_id in STATIC_PLAYER_TYPES:
            count = 1
        return range(count)

    left = right = top = bottom = 0
    for _, clip, type_id, dir_name, idx in wanted:
        for mi in motions_for(clip, type_id, idx):
            for img, ox, oy in render_parts(parts, idx, mi, DRAW_ORDER[dir_name]):
                left, right = min(left, ox), max(right, ox + img.width)
                top, bottom = min(top, oy), max(bottom, oy + img.height)
    half = max(-left, right)
    frame_w, frame_h = half * 2, bottom - top
    anchor_x, anchor_y = half, -top

    # 2) renderiza cada frame no canvas único
    rows, clips = [], {}
    for r, (clip_name, clip, type_id, dir_name, idx) in enumerate(wanted):
        row = []
        for mi in motions_for(clip, type_id, idx):
            canvas = Image.new("RGBA", (frame_w, frame_h))
            for img, ox, oy in render_parts(parts, idx, mi, DRAW_ORDER[dir_name]):
                canvas.alpha_composite(img, (anchor_x + ox, anchor_y + oy))
            row.append(canvas)
        rows.append(row)
        fps = round(1000 / parts["body"].actions[idx]["delay_ms"], 1)
        clips[clip_name] = {"row": r, "frames": len(row), "fps": fps, **CLIP_RULES[clip]}

    cols = max(len(r) for r in rows)
    sheet = Image.new("RGBA", (frame_w * cols, frame_h * len(rows)))
    for r, row in enumerate(rows):
        for c, frame in enumerate(row):
            sheet.paste(frame, (c * frame_w, r * frame_h))

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    sheet.save(out / f"{name}_sheet.png")
    meta = {
        "src": f"sprites/{name}/{name}_sheet.png",
        "frame_w": frame_w, "frame_h": frame_h, "cols": cols, "rows": len(rows),
        "anchor_x": anchor_x, "anchor_y": anchor_y,           # pés do personagem dentro do frame
        "clips": clips,
    }
    (out / f"{name}.json").write_text(json.dumps(meta, indent=2))
    print(f"frame {frame_w}x{frame_h} | sheet {sheet.size} | {len(clips)} clips | âncora ({anchor_x},{anchor_y})")

    if preview:
        bg = Image.new("RGBA", sheet.size, (40, 40, 50, 255))
        bg.alpha_composite(sheet)
        draw = ImageDraw.Draw(bg)
        for x in range(0, sheet.width + 1, frame_w):
            draw.line([(x, 0), (x, sheet.height)], fill=(255, 0, 0, 120))
        for y in range(0, sheet.height + 1, frame_h):
            draw.line([(0, y), (sheet.width, y)], fill=(255, 0, 0, 120))
        bg.save(preview)
        print("prévia salva em", preview)
    return sheet, meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Converte .spr + .act do RO em sprite sheet + JSON")
    ap.add_argument("body", help="corpo: caminho do .spr/.act, com ou sem extensão")
    ap.add_argument("name", help="nome da sheet (ex.: novice, poring)")
    ap.add_argument("--head", help="cabeça (.spr/.act, com ou sem extensão)")
    ap.add_argument("--weapon", help="arma (.spr/.act, com ou sem extensão)")
    ap.add_argument("--out", help="pasta de saída (padrão: assets/sprites/<name>)")
    ap.add_argument("--kind", choices=["auto", "player", "monster"], default="auto")
    ap.add_argument("--idle", type=int, help="força o tipo de ação do clip idle")
    ap.add_argument("--attack", type=int, help="força o tipo de ação do clip attack")
    ap.add_argument("--preview", help="salva uma prévia PNG com a grade dos frames")
    a = ap.parse_args()
    build(a.body, a.name, a.out or f"assets/sprites/{a.name}", a.head, a.weapon,
          a.kind, a.idle, a.attack, a.preview)