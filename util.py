from pathlib import Path

def mkdir_if_not_exists(relPath: str):
    if not (dir := Path(relPath).resolve()).exists(): dir.mkdir()
    return dir
