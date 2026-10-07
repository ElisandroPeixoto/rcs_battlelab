BOARD_DIMENSIONS = {
    "cols": 10,
    "rows": 10,
    "tile_w": 96,
    "tile_h": 48,
    "origin_x": 540,  # Centro do Tile. Posição (0,0)
    "origin_y": 200,
    "blocked": []
    }


def grid_to_screen(col: int, row: int, cfg: dict):
    x = cfg["origin_x"] + (col - row) * cfg["tile_w"] / 2
    y = cfg["origin_y"] + (col + row) * cfg["tile_h"] / 2

    return x, y

def screen_to_grid(x, y, cfg: dict):
    dx = (x - cfg["origin_x"]) / (cfg["tile_w"] / 2)
    dy = (y - cfg["origin_y"]) / (cfg["tile_h"] / 2
                                  )
    return round((dx + dy) / 2), round((dy-dx) / 2)

if __name__ == "__main__":
    print(grid_to_screen(9, 9, BOARD_DIMENSIONS))
    print(screen_to_grid(540, 632, BOARD_DIMENSIONS))
