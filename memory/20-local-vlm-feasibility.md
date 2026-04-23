# Local VLM Feasibility Report (2025-07)

## Executive Summary

**Verdict: NOT VIABLE for production use.** Local VLMs (4B-8B) cannot reliably identify game pages. Template matching + dedicated OCR remains the correct approach.

## Test Environment

- **GPU**: RTX 4070 SUPER (12GB VRAM)
- **CPU**: i5-13600KF
- **RAM**: 32GB DDR5
- **Ollama**: v0.21.1 (Windows)
- **Test images**: 7 real game screenshots (hub, shop, battle, intel_shards, guild, mail, amusement)

## Models Tested

| Model | Size | VRAM (loaded) | Cold Start | Warm Latency |
|-------|------|---------------|------------|--------------|
| gemma3:4b | 3.3 GB | ~4 GB | ~35s | ~3-4s |
| qwen2.5vl:7b | 6.0 GB | ~7 GB | ~15-20s | ~5-15s |
| minicpm-v (8B) | 5.5 GB | ~6 GB | ~33s | ~2.5-3.5s |

3 models total = **13.8 GB disk**.

## Test Results

### 1. Page Identification (Critical Task)

The primary use case: given a screenshot, identify which game page it is.

| Model | Accuracy | Notes |
|-------|----------|-------|
| gemma3:4b | **1/7** (14%) | Only hub correct (by luck), heavy hallucination |
| qwen2.5vl:7b | **0/7** (0%) | Systematic bias: ALL pages answered "main_hub" |
| minicpm-v | **0/6** (0%) | Vague answers: "main interface", wrong game name |

**Conclusion**: No model can reliably distinguish between game pages. Multi-choice prompts don't help — models are biased toward first option or default to vague descriptions.

### 2. OCR (Chinese Text Reading)

| Model | Quality | Examples |
|-------|---------|----------|
| gemma3:4b | **Poor** | Heavy hallucination, repeated "角色" endlessly |
| qwen2.5vl:7b | **Moderate** | Best of 3: reads 修正者/商店/公会/主线剧情/联合特勤 correctly |
| minicpm-v | **Sparse** | Reads some text (2026/4/23, UID) but misses most UI elements |

**vs PaddleOCR**: Dedicated OCR engines are far more reliable and 100x faster (~5ms vs 3-15s).

### 3. Bottom Navigation Bar Reading

| Model | hub | shop | battle | task_intel |
|-------|-----|------|--------|------------|
| qwen2.5vl:7b | WRONG | OK (修正者/探测/商店/公会) | OK (NONE) | OK |
| minicpm-v | WRONG (NONE) | Close but wrong chars | OK (情报/常驻/物资/挑战) | Close but wrong |

**Best approach found**: qwen2.5vl bottom nav reading was most reliable, but still inconsistent.

## Latency Comparison

| Method | Latency | Notes |
|--------|---------|-------|
| cv2.matchTemplate | **~50ms** | Current approach |
| PaddleOCR | **~5ms** | Dedicated OCR |
| gemma3:4b | ~3-4s | 60-80x slower than template |
| minicpm-v | ~2.5-3.5s | 50-70x slower |
| qwen2.5vl:7b | ~5-15s | 100-300x slower |
| qwen2.5vl (describe) | ~50s | Unusable for automation |

## Hardware Requirements for End Users

### Minimum (4B model)
- GPU: 6GB VRAM (RTX 3060, RTX 4060)
- RAM: 16GB
- Disk: +5GB for Ollama + model

### Recommended (7B model)
- GPU: 8GB+ VRAM (RTX 3070, RTX 4060 Ti)
- RAM: 16GB+
- Disk: +8GB

### Our test machine
- RTX 4070 SUPER 12GB — 7B model uses 8.5/12 GB VRAM (71%)
- **Many users won't have this level of GPU**

## Reference Project Analysis

| Project | Uses Local LLM? | Approach |
|---------|-----------------|----------|
| MAA (MaaAssistantArknights) | **No** | Template matching + PaddleOCR + ONNX |
| BetterGI | **No** | Template + YOLO (custom trained BetterGI-model) |
| ok-ww | **No** | Template matching |
| M9A | **No** | MaaFramework pipeline (CV only) |

**No major game automation project has integrated local VLMs.** All rely on CV-only approaches.

## Key Findings

1. **Page identification fails**: 0-14% accuracy across all models. Template matching with masks achieves >95%.
2. **Latency is prohibitive**: 3-15s per inference vs 50ms. A daily task pipeline makes 50+ page checks — VLM would add 3-12 minutes.
3. **Hardware barrier**: Requires modern GPU with 6-12GB VRAM. Many automation users run on laptops or older desktops.
4. **OCR is not competitive**: PaddleOCR is faster, more accurate, and works on CPU.
5. **Cold start penalty**: First inference takes 15-35s for model loading. Unacceptable for user experience.
6. **Disk footprint**: 5-8GB per model on top of game installation.

## When to Revisit

- **2026+**: When 20B+ VLMs can run at 1s latency on consumer GPUs with <4GB VRAM
- **Cloud API approach**: If cloud VLM costs drop below .001/image (currently ~.01-0.05)
- **YOLO approach**: Train a custom YOLO model on game screenshots (like BetterGI) — faster, smaller, more accurate for known UI
- **Hybrid approach**: Use template matching for known pages, VLM for unknown/ambiguous states only

## Recommendation

**Do NOT integrate local VLMs now.** Continue with:
1. cv2.matchTemplate for page identification (fast, reliable)
2. PaddleOCR for text reading (fast, accurate on Chinese)
3. If more robustness needed, consider YOLO-based UI detection (BetterGI approach)

## Installation Notes (for future reference)

Ollama installed at: `C:\Users\Administrator\AppData\Local\Programs\Ollama`
Models stored at: `~\.ollama\models\` (13.8 GB for 3 models)
API endpoint: `http://localhost:11434`
Test script: `.tmp/vlm_test/test_mc.py`
