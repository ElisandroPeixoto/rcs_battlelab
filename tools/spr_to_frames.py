import struct
import sys
from pathlib import Path
from PIL import Image


def read_spr(path: str) -> list[Image.Image]:
    data = Path(path).read_bytes()
    if data[:2] != b"SP":
        raise ValueError("não é um arquivo SPR")

    minor, major = data[2], data[3]            # versão nos offsets 2-3 (2.1 => major=2, minor=1)
    version = major * 256 + minor
    pos = 4

    indexed_count = struct.unpack_from("<H", data, pos)[0]; pos += 2
    rgba_count = 0
    if version >= 0x0102:                      # >= v1.2 tem contagem de frames RGBA
        rgba_count = struct.unpack_from("<H", data, pos)[0]; pos += 2
    print(f"versão {major}.{minor} | indexados: {indexed_count} | rgba: {rgba_count}")

    indexed = []
    for _ in range(indexed_count):
        w, h = struct.unpack_from("<HH", data, pos); pos += 4
        if version >= 0x0201:                  # v2.1: RLE de zeros
            size = struct.unpack_from("<H", data, pos)[0]; pos += 2
            raw, out, i = data[pos:pos + size], bytearray(), 0
            while i < len(raw):
                b = raw[i]; i += 1
                if b == 0:
                    out += b"\x00" * raw[i]; i += 1
                else:
                    out.append(b)
            pos += size
        else:
            out = bytearray(data[pos:pos + w * h]); pos += w * h
        indexed.append((w, h, bytes(out)))

    rgba = []
    for _ in range(rgba_count):
        w, h = struct.unpack_from("<HH", data, pos); pos += 4
        px = data[pos:pos + w * h * 4]; pos += w * h * 4
        img = Image.frombytes("RGBA", (w, h), px, "raw", "ABGR")
        rgba.append(img.transpose(Image.FLIP_TOP_BOTTOM))

    palette = data[-1024:]                     # RGBA; índice 0 = transparente
    frames = []
    for w, h, idx in indexed:
        img = Image.new("RGBA", (w, h))
        img.putdata([(0, 0, 0, 0) if i == 0 else (*palette[i*4:i*4+3], 255) for i in idx])
        frames.append(img)
    return frames + rgba


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "novice.spr"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "art_source/novice/raw")
    out.mkdir(parents=True, exist_ok=True)
    frames = read_spr(src)
    for n, frame in enumerate(frames):
        frame.save(out / f"{n:03d}.png")
    print(f"{len(frames)} frames salvos em {out}")