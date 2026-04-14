"""Click a named element on a page.

Looks up the element by English name (name_en) in the page's
element list, then clicks its coordinate. Refuses to click
unsafe elements unless force=True.

Composite Action: uses ClickOp primitive internally.
"""
from __future__ import annotations

from anime_game_afk.games.aether_gazer.knowledge.constants import CLICK_WAIT
from anime_game_afk.games.aether_gazer.knowledge.pages import find_element
from anime_game_afk.games.aether_gazer.ops.base import OpContext, OpResult
from anime_game_afk.games.aether_gazer.ops.primitives import ClickOp


class ClickElementAction:
    """Click a named element on a specified page."""

    def __init__(
        self,
        page_id: str,
        element_name_en: str,
        wait_after: float = CLICK_WAIT,
        force_unsafe: bool = False,
    ) -> None:
        self._page_id = page_id
        self._element_name = element_name_en
        self._wait = wait_after
        self._force = force_unsafe

    async def run(self, ctx: OpContext) -> OpResult:
        elem = find_element(self._page_id, self._element_name)
        if elem is None:
            return OpResult(
                success=False,
                error=f"Element '{self._element_name}' not found "
                      f"on page '{self._page_id}'",
            )

        if not elem.safe and not self._force:
            return OpResult(
                success=False,
                error=f"Element '{self._element_name}' is unsafe. "
                      f"Use force_unsafe=True to override.",
            )

        ctx.logger.info(
            f"Clicking {self._element_name} at "
            f"({elem.coord.x}, {elem.coord.y}) on {self._page_id}"
        )
        await ClickOp(x=elem.coord.x, y=elem.coord.y, wait=self._wait).run(ctx)
        return OpResult(
            success=True,
            data={"element": self._element_name, "page": self._page_id},
        )
