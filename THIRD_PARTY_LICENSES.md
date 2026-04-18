# Third-Party Licenses

anime-game-afk uses the following open-source libraries.
We are grateful to their authors and contributors.

## Python Dependencies

| Package | License | URL |
|---------|---------|-----|
| MaaFw (MaaFramework) | LGPL-3.0 | https://github.com/MaaXYZ/MaaFramework |
| loguru | MIT | https://github.com/Delgan/loguru |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy |
| opencv-python-headless | Apache-2.0 | https://github.com/opencv/opencv-python |
| PyYAML | MIT | https://github.com/yaml/pyyaml |
| pywebview | BSD-3-Clause | https://github.com/nicegui-kr/pywebview |
| PyInstaller | GPL-2.0 (with bootloader exception) | https://github.com/pyinstaller/pyinstaller |
| rapidocr-onnxruntime | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| onnxruntime | MIT | https://github.com/microsoft/onnxruntime |

## Frontend Dependencies

| Package | License | URL |
|---------|---------|-----|
| Vue.js 3 | MIT | https://github.com/vuejs/core |
| Vite | MIT | https://github.com/vitejs/vite |

## Bundled Binary Components

The distributed release includes binary components from:

### MaaFramework (LGPL-3.0)

MaaFramework DLLs (`maa/bin/`) are redistributed under the
GNU Lesser General Public License v3.0. The complete source code is
available at https://github.com/MaaXYZ/MaaFramework.

As required by LGPL-3.0:
- The MaaFramework library is dynamically linked.
- Users may replace the included MaaFramework DLLs with their own builds.
- The full LGPL-3.0 license text is available at
  https://www.gnu.org/licenses/lgpl-3.0.html

### ONNX Runtime (MIT)

Included as part of the MaaFramework or rapidocr-onnxruntime package.
Source: https://github.com/microsoft/onnxruntime

### OpenCV (Apache-2.0)

Included as part of the MaaFramework distribution.
Source: https://github.com/opencv/opencv

---

If you believe any attribution is missing or incorrect, please open an issue.
