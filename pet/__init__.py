"""
Desktop Pet -- a lightweight animated mascot that lives on your taskbar.

The package is split into small, focused modules:

* :mod:`pet.config`     -- load/save user settings (settings.json)
* :mod:`pet.taskbar`    -- detect the Windows taskbar position/size
* :mod:`pet.animation`  -- a tiny sprite-frame animation player
* :mod:`pet.character`  -- load a character folder (frames + config + sounds)
* :mod:`pet.behavior`   -- the idle/walk/sleep/fall/drag state machine
* :mod:`pet.sound`      -- optional, non-blocking sound effects
* :mod:`pet.pet_widget` -- the transparent, click-through-free window itself
"""

__version__ = "1.0.0"
