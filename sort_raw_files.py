from pathlib import Path
import re 

from util import mkdir_if_not_exists

def sort_files(directory: Path):
    # pattern to find the date from a filename
    pattern = '20[0-9]{6}'
    for file in directory.iterdir():
        name = file.name
        # Get the last match [-1], take the first 4 digits [:4]
        # Should be the year it was taken
        year = re.findall(pattern, name)[-1][:4]

        yeardir = mkdir_if_not_exists(directory / year)
        file.move_into(yeardir)
