import time
from dataclasses import dataclass
from functools import total_ordering
from typing import NamedTuple

from models import State, Pack, Blueprint


@dataclass
class Stats:
    # Track statistics about runtime
    states_visited: int = 0
    cache_hits: int = 0
    cache_attempts: int = 0
    futile_hits: int = 0

    def detect_futile(self):
        self.futile_hits += 1

    def missed_cache(self):
        self.cache_attempts += 1

    def hit_cache(self):
        self.cache_attempts += 1
        self.cache_hits += 1

    @property
    def cache_misses(self):
        return self.cache_attempts - self.cache_hits

    @property
    def cache_hit_rate(self):
        return self.cache_hits / (self.cache_misses + 1e-6)

    def visit_node(self):
        self.states_visited += 1

    def reset(self):
        self.states_visited = 0
        self.cache_hits = 0
        self.cache_attempts = 0
        self.futile_hits = 0


class AllowedOptions(NamedTuple):
    """An overkill object to track what can be built"""
    ore: bool
    clay: bool
    obsidian: bool
    diamond: bool


@total_ordering
@dataclass
class BestObserved:
    """Did I say overkill? how about an integer with a built-in max function"""

    value: int = -1

    def update(self, v):
        self.value = max(self.value, v)
    
    def reset(self):
        self.value = 0

    def __eq__(self, other):
        return self.value == other
    
    def __lt__(self, other):
        return self.value < other
    
    def __gt__(self, other):
        return self.value > other


# Singletons
stats = Stats()
cache = {}
best = BestObserved()

def solve(
    state: State, bp: Blueprint, _allowed_options=AllowedOptions(True, True, True, True)
):
    stats.visit_node()

    if state.remaining_turns == 0:
        # Check for termination
        return state.pack.diamonds

    if state.pack in cache:
        best_result, remaining_turns = cache[state.pack]
        # More permissive caching -
        #  Instead of hitting the cache if we encounter the same pack at the same time
        #  step, we will also bail if the stored state was from earlier in the game.
        if state.remaining_turns < remaining_turns:
            stats.hit_cache()
            return -1
        elif state.remaining_turns == remaining_turns:
            stats.hit_cache()
            return best_result
    stats.missed_cache()

    if state.upper_bound_diamonds < best:
        # Futility check - if it is impossible to beat the best observed score, give up
        stats.detect_futile()
        return -1

    diamond_res = 0
    ob_res = 0
    clay_res = 0
    ore_res = 0

    if (can_build_diamond := state.can_build_diamond(bp)) and _allowed_options.diamond:
        diamond_res = solve(state.build_diamond(bp), bp)
        best.update(diamond_res)

    if (
        (can_build_ore := state.can_build_ore(bp))
        and _allowed_options.ore
        and state.pack.ore_bots < bp.max_ore
    ):
        ore_res = solve(state.build_ore(bp), bp)
        best.update(ore_res)

    if (
        (can_build_clay := state.can_build_clay(bp))
        and _allowed_options.clay
        and state.pack.clay_bots < bp.max_clay
    ):
        clay_res = solve(state.build_clay(bp), bp)
        best.update(clay_res)

    if (
        (can_build_obsidian := state.can_build_obsidian(bp))
        and _allowed_options.obsidian
        and state.pack.obsidian_bots < bp.max_obsidian
    ):
        ob_res = solve(state.build_obsidian(bp), bp)
        best.update(ob_res)

    wait_res = solve(
        state.wait(),
        bp,
        # Performing action X is strictly better than performing wait+X for X != "wait".
        # Therefore, if the agent could have built a bot on _this_ turn, but chooses
        # to wait, that bot cannot be built on the next turn.
        AllowedOptions(
            ore=not can_build_ore,
            clay=not can_build_clay,
            obsidian=not can_build_obsidian,
            diamond=not can_build_diamond,
        ),
    )
    best.update(wait_res)

    best_res = max(diamond_res, ob_res, clay_res, ore_res, wait_res)
    cache[state.pack] = (best_res, state.remaining_turns)
    return best_res


def reset():
    global BEST_OBSERVED
    cache.clear()
    stats.reset()
    BEST_OBSERVED = -1


if __name__ == "__main__":
    for num_steps in [50]:
        bp = Blueprint()  # Use the default blueprint for the time being.
        initial_state = State(pack=Pack(ore_bots=1), remaining_turns=num_steps)

        start_time = time.process_time()
        print("Max Steps: ", num_steps)
        print("Solution: ", solve(initial_state, bp))
        print(f"[*] Duration: {time.process_time() - start_time:g} seconds")
        print(f"[*] Num States Visited: {stats.states_visited}")
        print(f"[*] Cache Hit Rate: {stats.cache_hit_rate:.2%}")
        print(f"[*] Num Futile Hits: {stats.futile_hits}")
        print("------------------------------------------")

        reset()
