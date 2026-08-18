"""Standard-library terminal animations for The Resilience Matrix."""

from __future__ import annotations

import math
import os
import shutil
import sys
import time
from typing import Callable, List, Optional, TextIO, Tuple


class TerminalFX:
    """ANSI-aware terminal effects with a quiet non-TTY fallback.

    Interactive terminals use pseudo-3D wireframe scenes by default. The scenes
    run in the terminal's alternate screen buffer so normal