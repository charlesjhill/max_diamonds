from functools import lru_cache
from typing import NamedTuple


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

    id: int = 0

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

