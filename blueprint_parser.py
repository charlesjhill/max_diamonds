import os
import re
from pathlib import Path

from models import Blueprint

FILE_PATH = str | bytes | os.PathLike


def parse(txt_file: FILE_PATH) -> list[Blueprint]:
    pth = Path(txt_file)
    blueprint_strings = pth.read_text().splitlines()

    # N.B. No bots cost any geodes in any blueprint
    ore_pattern = re.compile(r"(\d+) ore")
    clay_pattern = re.compile(r"(\d+) clay")
    obsidian_pattern = re.compile(r"(\d+) obsidian")

    blueprints = []
    for blueprint_str in blueprint_strings:
        match = re.search(r"(\d+):\s(.+)", blueprint_str)
        id = int(match.group(1))

        # match.group(2).split(".") splits the blueprint string into sentences, where each sentence is the bot's total cost.
        #   This will take the form "Each X robot costs 2 A and 10 B and ..."
        # Pull out everything to the right of "costs" and remove the whitespace
        #   -> "2 A and 10 B ..."
        # Throw a filter clause around it to remove empty strings
        cost_clauses = filter(
            None, (c.split("costs")[-1].strip() for c in match.group(2).split("."))
        )

        this_bots_cost = []
        for cost_str in cost_clauses:
            ore_cost = 0
            clay_cost = 0
            ob_cost = 0

            ore_match = ore_pattern.search(cost_str)
            if ore_match:
                ore_cost = int(ore_match.group(1))

            clay_match = clay_pattern.search(cost_str)
            if clay_match:
                clay_cost = int(clay_match.group(1))

            obsidian_match = obsidian_pattern.search(cost_str)
            if obsidian_match:
                ob_cost = int(obsidian_match.group(1))

            this_bots_cost.append((ore_cost, clay_cost, ob_cost, 0))

        blueprints.append(Blueprint(*this_bots_cost, id=id))

    return blueprints


if __name__ == "__main__":
    parse("./blueprints.txt")
