from collections import namedtuple
import time
from dataclasses import dataclass
from typing import NamedTuple
from functools import lru_cache, total_ordering


@dataclass
class Stats:
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


class Pack(NamedTuple):
    ore: int = 0
    clay: int = 0
    obsidian: int = 0
    diamonds: int = 0
    ore_bots: int = 0
    clay_bots: int = 0
    obsidian_bots: int = 0
    diamond_bots: int = 0

    def produce(self):
        return self._replace(
            ore=self.ore + self.ore_bots,
            clay=self.clay + self.clay_bots,
            obsidian=self.obsidian + self.obsidian_bots,
            diamonds=self.diamonds + self.diamond_bots,
        )

    def build_ore(self, bp: "Blueprint"):
        ore_cost, clay_cost, ob_cost, diamond_cost = bp.ore

        return self._replace(
            ore=self.ore - ore_cost,
            clay=self.clay - clay_cost,
            obsidian=self.obsidian - ob_cost,
            diamonds=self.diamonds - diamond_cost,
            ore_bots=self.ore_bots + 1,
        )

    def build_clay(self, bp: "Blueprint"):
        ore_cost, clay_cost, ob_cost, diamond_cost = bp.clay

        return self._replace(
            ore=self.ore - ore_cost,
            clay=self.clay - clay_cost,
            obsidian=self.obsidian - ob_cost,
            diamonds=self.diamonds - diamond_cost,
            clay_bots=self.clay_bots + 1,
        )

    def build_obsidian(self, bp: "Blueprint"):
        ore_cost, clay_cost, ob_cost, diamond_cost = bp.obsidian

        return self._replace(
            ore=self.ore - ore_cost,
            clay=self.clay - clay_cost,
            obsidian=self.obsidian - ob_cost,
            diamonds=self.diamonds - diamond_cost,
            obsidian_bots=self.obsidian_bots + 1,
        )

    def build_diamond(self, bp: "Blueprint"):
        ore_cost, clay_cost, ob_cost, diamond_cost = bp.diamond

        return self._replace(
            ore=self.ore - ore_cost,
            clay=self.clay - clay_cost,
            obsidian=self.obsidian - ob_cost,
            diamonds=self.diamonds - diamond_cost,
            diamond_bots=self.diamond_bots + 1,
        )

    def can_build(self, bot_kind, bp: "Blueprint"):
        ore_cost, clay_cost, ob_cost, diamond_cost = getattr(bp, bot_kind)

        return (
            self.ore >= ore_cost
            and self.clay >= clay_cost
            and self.obsidian >= ob_cost
            and self.diamonds >= diamond_cost
        )


class State(NamedTuple):
    """State of the simulation"""

    pack: Pack = Pack()
    remaining_turns: int = 100

    def _step(self):
        return self._replace(
            pack=self.pack.produce(), remaining_turns=self.remaining_turns - 1
        )

    def wait(self):
        return self._step()

    def build_ore(self, bp: "Blueprint"):
        return self._replace(pack=self.pack.build_ore(bp))._step()

    def build_clay(self, bp: "Blueprint"):
        return self._replace(pack=self.pack.build_clay(bp))._step()

    def build_obsidian(self, bp: "Blueprint"):
        return self._replace(pack=self.pack.build_obsidian(bp))._step()

    def build_diamond(self, bp: "Blueprint"):
        return self._replace(pack=self.pack.build_diamond(bp))._step()

    def can_build_ore(self, bp: "Blueprint"):
        return self.pack.can_build("ore", bp)

    def can_build_clay(self, bp: "Blueprint"):
        return self.pack.can_build("clay", bp)

    def can_build_obsidian(self, bp: "Blueprint"):
        return self.pack.can_build("obsidian", bp)

    def can_build_diamond(self, bp: "Blueprint"):
        return self.pack.can_build("diamond", bp)

    @property
    def upper_bound_diamonds(self):
        """Estimate the upper-bound on the diamonds achievable from this state"""
        return self.pack.diamonds + self.remaining_turns * (
            self.pack.diamond_bots + 0.5 * (self.remaining_turns + 1)
        )


class Blueprint(NamedTuple):
    """Blueprint of the bots"""

    # Each cost is a tuple of (ore, clay, obsidian, diamond) per.
    ore: tuple[int] = (4, 0, 0, 0)
    clay: tuple[int] = (2, 0, 0, 0)
    obsidian: tuple[int] = (2, 14, 0, 0)
    diamond: tuple[int] = (2, 0, 7, 0)

    @lru_cache
    def _max_resource(self, ind: int):
        return max(self.ore[ind], self.clay[ind], self.obsidian[ind], self.diamond[ind])

    @property
    def max_ore(self):
        return self._max_resource(0)

    @property
    def max_clay(self):
        return self._max_resource(1)

    @property
    def max_obsidian(self):
        return self._max_resource(2)

    @property
    def max_diamond(self):
        return self._max_resource(3)


class AllowedOptions(NamedTuple):
    ore: bool
    clay: bool
    obsidian: bool
    diamond: bool


@total_ordering
@dataclass
class BestObserved:
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
