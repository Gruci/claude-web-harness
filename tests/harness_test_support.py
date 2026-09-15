"""Temporary project roots with unittest-managed cleanup for harness tests."""

import tempfile
import unittest
from pathlib import Path


class TemporaryRootTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temporary_root = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_root.cleanup)
        self.root = Path(temporary_root.name)
