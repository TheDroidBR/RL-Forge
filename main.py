"""
RL Swapper — main entry point.
"""

import sys
import os
from core.utils import get_base_dir

sys.path.insert(0, str(get_base_dir()))

from gui.app import RLSwapperApp

if __name__ == "__main__":
    app = RLSwapperApp()
    app.mainloop()
