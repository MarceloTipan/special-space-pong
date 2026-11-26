"""Where the game is running: desktop, or a web browser (pygbag)."""

import sys

#: True when running in the browser. pygbag runs Python compiled to
#: WebAssembly through Emscripten, which reports this platform.
WEB = sys.platform == "emscripten"

#: The webcam control needs OpenCV, which can't reach the camera from a browser.
CAMERA_SUPPORTED = not WEB
