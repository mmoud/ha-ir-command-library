"""Tests for pure command-model behavior."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ir_command_library"
    / "models.py"
)
SPEC = importlib.util.spec_from_file_location("ir_command_library_models", MODULE_PATH)
assert SPEC and SPEC.loader
MODELS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODELS
SPEC.loader.exec_module(MODELS)
IRCommand = MODELS.IRCommand


class IRCommandModelTests(unittest.TestCase):
    """Verify the privacy and identity guarantees of catalog records."""

    def test_command_round_trip_and_stable_key(self) -> None:
        command = IRCommand.create(
            controller="remote.living_room",
            area="Living Room",
            device="television",
            command="volume_up",
        )
        loaded = IRCommand.from_dict(command.as_dict())
        self.assertEqual(loaded, command)
        self.assertEqual(loaded.key, command.key)
        self.assertEqual(loaded.command_name, "Volume Up")

    def test_invalid_controller_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            IRCommand.create(
                controller="switch.remote",
                area="Living Room",
                device="television",
                command="power",
            )

    def test_payload_is_not_serialized(self) -> None:
        command = IRCommand.create(
            controller="remote.living_room",
            area="Living Room",
            device="television",
            command="power",
        )
        self.assertEqual(
            set(command.as_dict()), {"controller", "area", "device", "command"}
        )


if __name__ == "__main__":
    unittest.main()
