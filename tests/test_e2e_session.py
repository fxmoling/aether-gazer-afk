"""端到端测试: 连接深空之眼，截图，点击，断开"""

import sys
from pathlib import Path

# 确保能导入项目代码
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
from loguru import logger

from anime_game_afk.core.session import GameSession
from anime_game_afk.games.aether_gazer.config import AETHER_GAZER_CONFIG


def main() -> None:
    logger.info("=== 端到端测试: GameSession ===")

    session = GameSession(AETHER_GAZER_CONFIG)

    # 1. 连接
    logger.info("Step 1: 连接游戏窗口")
    session.connect()
    assert session.connected
    logger.info("连接成功")

    # 2. 截图
    logger.info("Step 2: 后台截图")
    img = session.screenshot()
    assert img is not None
    assert img.shape == (720, 1280, 3)
    logger.info("截图成功: shape={}", img.shape)

    output_path = Path("test_output")
    output_path.mkdir(exist_ok=True)
    cv2.imwrite(str(output_path / "e2e_screenshot.png"), img)

    # 3. 点击空白区域（验证点击不报错）
    logger.info("Step 3: 后台点击 (屏幕中央)")
    session.click(640, 360)
    logger.info("点击成功")

    # 4. 按键（验证按键不报错）
    logger.info("Step 4: 后台按键 (无效键，只测试通道)")
    # 不按 ESC 避免弹退出对话框，按一个无害的键
    # VK_F13 = 0x7C，大多数游戏不响应
    session.press_key(0x7C)
    logger.info("按键成功")

    # 5. 再截一次图确认连接稳定
    logger.info("Step 5: 再次截图确认稳定性")
    img2 = session.screenshot()
    assert img2.shape == (720, 1280, 3)
    logger.info("第二次截图成功")

    # 6. 断开
    logger.info("Step 6: 断开连接")
    session.disconnect()
    assert not session.connected
    logger.info("断开成功")

    logger.info("=== 所有测试通过 ===")


if __name__ == "__main__":
    main()
