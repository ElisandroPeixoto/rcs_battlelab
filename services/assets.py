import os
from config import ASSETS_DIR


def asset_file_exists(file_name: str) -> bool:
    return bool(file_name) and os.path.exists(os.path.join(ASSETS_DIR, file_name))
