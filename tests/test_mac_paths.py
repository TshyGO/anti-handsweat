from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from platform_paths import discover_exiftool

class MacPathsTests(unittest.TestCase):
    def test_explicit_path_is_respected(self):
        # Path normalizes separators on Windows. Verify the selected path,
        # not a Unix-only spelling, and ensure it never falls back to PATH.
        with patch('platform_paths.shutil.which') as search:
            self.assertEqual(discover_exiftool('/missing/custom exiftool'),
                             str(Path('/missing/custom exiftool')))
            search.assert_not_called()
    def test_expands_user_home(self):
        self.assertEqual(discover_exiftool('~/exiftool'),str(Path.home()/'exiftool'))
    def test_local_tool_is_found(self):
        with tempfile.TemporaryDirectory(prefix='test mac spaces ') as d:
            root=Path(d);(root/'tools').mkdir();exe=root/'tools'/'exiftool'
            exe.write_text('#!/bin/sh\necho test\n');exe.chmod(0o755)
            self.assertEqual(discover_exiftool(root=root),str(exe))
    def test_path_tool_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            exe=Path(d)/'exiftool';exe.write_text('#!/bin/sh\n');exe.chmod(0o755)
            with patch('platform_paths.shutil.which',return_value=str(exe)):
                self.assertEqual(discover_exiftool(),str(exe))
    def test_nonexecutable_local_is_not_selected(self):
        if os.name=='nt': self.skipTest('Unix permission semantics')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'tools').mkdir();exe=root/'tools'/'exiftool';exe.write_text('text');exe.chmod(0o644)
            with patch('platform_paths.shutil.which',return_value=None),patch('platform_paths.sys.platform','linux'):
                self.assertEqual(discover_exiftool(root=root),'')
    def test_no_missing_tool_fabricated(self):
        with patch('platform_paths.shutil.which',return_value=None),patch('platform_paths.sys.platform','linux'):
            self.assertEqual(discover_exiftool(),'')
