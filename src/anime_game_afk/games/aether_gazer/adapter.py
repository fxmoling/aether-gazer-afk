"""深空之眼适配器"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from anime_game_afk.config.models import TaskResult
from anime_game_afk.core.session import GameSession
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG


class AetherGazerAdapter:
    """深空之眼游戏适配器"""

    def __init__(self) -> None:
        self._session = GameSession(AETHER_GAZER_CONFIG)

    @property
    def session(self) -> GameSession:
        return self._session

    def connect(self) -> None:
        """连接游戏"""
        self._session.connect()

    def disconnect(self) -> None:
        """断开连接"""
        self._session.disconnect()

    def daily_login(self) -> TaskResult:
        """日常登录签到

        TODO: 实现 JSON 管线
        """
        logger.info("执行: 日常登录")
        # self._session.run_pipeline("DailyLogin")
        return TaskResult(success=True, task_name="daily_login")

    def collect_rewards(self) -> TaskResult:
        """领取奖励

        TODO: 实现 JSON 管线
        """
        logger.info("执行: 领取奖励")
        # self._session.run_pipeline("CollectRewards")
        return TaskResult(success=True, task_name="collect_rewards")
