# ui/ — GUI Layer (Layer 9)

PyWebView-based graphical interface for the automation framework.

## Files

| File | Purpose |
|------|---------|
| `api.py` | API class exposed to frontend via pywebview `js_api`. All public methods callable from JavaScript. |
| `app.py` | Main entry point. Creates pywebview window, detects/installs WebView2 Runtime, starts event loop. |
| `bridge.py` | `LogForwarder` — loguru sink forwarding logs to browser in real-time via `evaluate_js()`. Ring buffer (500 max). |
| `task_manager.py` | Bridges UI to Pipeline/Process system. Manages pipeline discovery, task state, background execution. |
| `worker.py` | Subprocess worker entry point for pipeline execution. JSON-line protocol on stdout, logs to stderr. |
| `web/` | Frontend build output (HTML, CSS, JS). **Do not edit directly** — build from `frontend/`. |

## Architecture

- Task/Process execution runs on background threads via `TaskManager`
- Heavy work runs in a **subprocess** (`worker.py`) so the GUI can `process.kill()` it
- Logs pushed to frontend in real-time via `LogForwarder`
- All API methods return JSON-serializable values

## Layer Rule

Layer 9 is the presentation layer — depends on all lower layers but nothing depends on it.
