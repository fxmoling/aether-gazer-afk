"""端到端测试: 连接深空之眼，截图，点击，断开"""

import sys
from pathlib import Path

# 确保能导入项目代码
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio

import cv2
import numpy as np
from loguru import logger
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum

from anime_game_afk.core.device import DeviceAdapter, MAX_HEIGHT
from anime_game_afk.core.types import DeviceConfig
from anime_game_afk.games.aether_gazer.ops.base import OpContext
from anime_game_afk.games.aether_gazer.ops.primitives import (
    ClickOp,
    ClickPxOp,
    ScreenshotOp,
)
from anime_game_afk.games.aether_gazer.ops.perception.identify_page import identify
from anime_game_afk.vision.ocr import ocr_once


def main() -> None:
    logger.info("=== E2E Test: Resolution-Agnostic Pipeline ===")

    config = DeviceConfig(
        window_title="AetherGazer",
        screencap_method=MaaWin32ScreencapMethodEnum.FramePool,
        mouse_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
        keyboard_method=MaaWin32InputMethodEnum.SendMessageWithCursorPos,
    )
    device = DeviceAdapter(config)

    # 1. 连接
    logger.info("Step 1: 连接游戏窗口")
    device.connect()
    assert device.connected
    actual = device.actual_resolution
    logger.info("连接成功: {}x{}", actual.width, actual.height)

    # 2. 截图 (proportional scaling, height <= MAX_HEIGHT)
    logger.info("Step 2: 后台截图")
    img = device.screenshot()
    h, w = img.shape[:2]
    assert h <= MAX_HEIGHT, f"Height {h} exceeds MAX_HEIGHT {MAX_HEIGHT}"
    actual_ratio = actual.width / actual.height
    img_ratio = w / h
    assert abs(actual_ratio - img_ratio) < 0.02, "Aspect ratio mismatch"
    logger.info("截图成功: {}x{}, aspect={:.3f}", w, h, img_ratio)

    output_path = Path("test_output")
    output_path.mkdir(exist_ok=True)
    cv2.imwrite(str(output_path / "e2e_screenshot.png"), img)

    # 3. resolution property
    res = device.resolution
    assert res == (w, h), f"resolution {res} != ({w}, {h})"
    logger.info("device.resolution = {}", res)

    # 4. 点击 (fractional coords)
    logger.info("Step 3: 后台点击 (0.5, 0.5)")
    device.click(0.5, 0.5)
    logger.info("点击成功")

    # 5. Op-level tests via OpContext
    logger.info("Step 4: Op-level tests")
    ctx = OpContext(device=device)

    async def _run_ops() -> None:
        snap = await ScreenshotOp().run(ctx)
        assert snap.success, f"ScreenshotOp failed: {snap.error}"
        assert isinstance(snap.data, np.ndarray)
        logger.info("  ScreenshotOp: {}", snap.data.shape)

        r = await ClickOp(x=0.5, y=0.5, wait=0.1).run(ctx)
        assert r.success, f"ClickOp failed: {r.error}"
        logger.info("  ClickOp: {}", r.data)

        r2 = await ClickPxOp(px=w // 2, py=h // 2, wait=0.1).run(ctx)
        assert r2.success, f"ClickPxOp failed: {r2.error}"
        assert abs(r2.data["fx"] - 0.5) < 0.01
        logger.info("  ClickPxOp: {}", r2.data)

    asyncio.run(_run_ops())

    # 6. Page identification
    logger.info("Step 5: 页面识别")
    page_id, confidence = identify(img)
    logger.info("  Page: {} (conf={:.3f})", page_id, confidence)

    # 7. OCR
    logger.info("Step 6: OCR扫描")
    ocr_result = ocr_once(img)
    if ocr_result:
        texts = [t.text for t in ocr_result.items[:5]]
        logger.info("  OCR: {} items, first 5: {}", len(ocr_result.items), texts)
        for item in ocr_result.items[:3]:
            r = item.region
            assert 0 <= r.x < w, f"OCR x={r.x} out of bounds"
            assert 0 <= r.y < h, f"OCR y={r.y} out of bounds"
        logger.info("  OCR coords in screenshot space ✓")
    else:
        logger.warning("  OCR returned no results")

    # 8. 断开
    logger.info("Step 7: 断开连接")
    device.disconnect()
    assert not device.connected
    logger.info("断开成功")

    logger.info("=== 所有测试通过 ===")


if __name__ == "__main__":
    main()
