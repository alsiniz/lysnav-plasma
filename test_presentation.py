"""Regression checks for test-build UI labels and text-only Plasma feedback.

These checks intentionally do not load a Qt session. Functional widget tests
remain in test_ui.py and must run with PySide6 in CI and on KDE Plasma.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from version import KOFI_URL, VERSION

ROOT = Path(__file__).resolve().parent


def literals(source: str) -> set[str]:
    return {node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)}


class PresentationTests(unittest.TestCase):
    def test_public_support_link_and_version(self):
        self.assertEqual(KOFI_URL, 'https://ko-fi.com/alsiniz')
        self.assertEqual(VERSION, '1.1.0')

    def test_brightness_osd_requests_no_icon(self):
        tree = ast.parse((ROOT / 'tray_sni.py').read_text())
        match = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Message':
                arguments = {k.arg: k.value for k in node.keywords}
                if isinstance(arguments.get('member'), ast.Constant) and arguments['member'].value == 'showText':
                    match.append(arguments)
        self.assertEqual(len(match), 1)
        body = match[0]['body']
        self.assertIsInstance(body, ast.List)
        self.assertEqual(len(body.elts), 2)
        self.assertIsInstance(body.elts[0], ast.Constant)
        self.assertEqual(body.elts[0].value, '')

    def test_ui_has_clean_button_labels_and_help(self):
        values = literals((ROOT / 'app.py').read_text())
        for label in ('Choose devices', 'Tray settings', 'Tray appearance',
                      'Support on Ko-fi', 'Mouse controls', 'Restore default dynamic icon'):
            self.assertIn(label, values)
        self.assertNotIn('Choose devices…', values)
        self.assertNotIn('Tray settings…', values)
        contents = (ROOT / 'app.py').read_text()
        self.assertIn('Toggle the selected approved lights together.', contents)
        self.assertIn('Adjust brightness by 5% per notch for approved lights already on.', contents)
        self.assertIn('Custom icons do not reflect whether your lights are on or off.', contents)
        self.assertIn('DHCP reservation', contents)
        self.assertIn('QDesktopServices.openUrl(QUrl(KOFI_URL))', contents)
        self.assertIn('https://github.com/alsiniz', contents)


if __name__ == '__main__':
    unittest.main()
