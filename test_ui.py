"""Qt slider regression test. Run with QT_QPA_PLATFORM=offscreen on CI."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import gc
import tracemalloc
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QObject, Qt, QPoint, QPointF, QCoreApplication, QEvent, QTimer, QProcess
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QColor, QIcon, QPalette, QWheelEvent
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QMenu, QScrollArea, QDialog, QDialogButtonBox, QLineEdit, QSystemTrayIcon
    from shiboken6 import isValid
    from app import panel_is_dark, IconPickerDialog, ClickToJumpSlider, TemperatureSlider, Wheel, TraySettingsDialog, ConnectionDialog, TokenPairingDialog, hub_action_svg, MainWindow
    from core import ALL_APPROVED, EnvironmentInfo, LightInfo
except ImportError:
    if os.environ.get('LYSNAV_REQUIRE_QT_TESTS') == '1':
        raise
    ClickToJumpSlider = None


def process_memory_bytes():
    """Current resident/working-set bytes, diagnostic only (not a leak verdict)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        stats = Counters()
        stats.cb = ctypes.sizeof(stats)
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(stats), stats.cb):
            return stats.WorkingSetSize
    elif sys.platform.startswith("linux"):
        try:
            return int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            pass
    return None


@unittest.skipUnless(ClickToJumpSlider is not None, 'PySide6 not installed (non-UI test environment)')
class SliderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_wheel_notifies_window_for_debounced_commit(self):
        slider = ClickToJumpSlider(Qt.Orientation.Horizontal)
        slider.setRange(1, 100)
        slider.setValue(50)
        slider.resize(300, 32)
        slider.show()
        seen = []
        slider.wheelAdjusted.connect(seen.append)
        center = QPointF(150, 16)
        event = QWheelEvent(center, center, QPoint(0, 0), QPoint(0, 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.ScrollUpdate, False)
        QApplication.sendEvent(slider, event)
        self.assertGreater(slider.value(), 50)
        self.assertEqual(seen, [slider.value()])
        slider.close()

    def test_temperature_gradient_is_static_and_clean_around_the_thumb(self):
        from PySide6.QtWidgets import QStyle, QStyleOptionSlider

        readout = QLabel()
        slider = TemperatureSlider(("lamp",), readout)
        self.addCleanup(slider.close)
        slider.setRange(2200, 6500)
        slider.resize(320, 32)
        palette = slider.palette()
        accent = QColor("#00ff00")
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        slider.setPalette(palette)
        slider.show()
        self.app.processEvents()

        def track_colours():
            option = QStyleOptionSlider()
            slider.initStyleOption(option)
            handle = slider.style().subControlRect(QStyle.ComplexControl.CC_Slider, option,
                                                   QStyle.SubControl.SC_SliderHandle, slider)
            pixmap = slider.grab()
            image, scale = pixmap.toImage(), pixmap.devicePixelRatio()
            y = round(handle.center().y() * scale)
            left_edge = round(handle.left() * scale)
            right_edge = round((handle.right() + 1) * scale)
            self.assertNotIn(accent, [image.pixelColor(x, y) for x in range(left_edge)])
            self.assertNotIn(accent, [image.pixelColor(x, y) for x in range(right_edge, image.width())])
            return (image.pixelColor(round(28 * scale), y),
                    image.pixelColor(round(290 * scale), y))

        slider.setValue(3400)
        warm, cool = track_colours()
        self.assertGreater(warm.red(), warm.blue())
        self.assertGreater(cool.blue(), cool.red())
        slider.setValue(5600)
        self.assertEqual(track_colours(), (warm, cool))
        self.assertEqual(readout.text(), "5600 K")

        rgb = LightInfo("lamp", "Desk", "room", "Study", True, ("colorTemperature",),
                        True, 50, 3400, 2200, 6500, 270, .7, "color")
        slider.update_from_lights([rgb])
        dim_warm, dim_cool = track_colours()
        self.assertLess(0, dim_warm.red() - dim_warm.blue())
        self.assertLess(dim_warm.red() - dim_warm.blue(), warm.red() - warm.blue())
        self.assertGreater(dim_cool.blue(), dim_cool.red())
        self.assertEqual(readout.text(), "RGB mode")
        QTest.keyClick(slider, Qt.Key.Key_Right)
        self.assertEqual(readout.text(), f"{slider.value()} K")
        self.assertEqual(track_colours(), (dim_warm, dim_cool))

    def test_colour_wheel_antialiases_the_disk_edge(self):
        wheel = Wheel(180, 1)
        self.addCleanup(wheel.close)
        palette = wheel.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("black"))
        wheel.setPalette(palette)
        wheel.setAutoFillBackground(True)
        wheel.show()
        pixmap = wheel.grab()
        image, scale = pixmap.toImage(), pixmap.devicePixelRatio()
        east = round((wheel.center + wheel.r) * scale)
        centre = round(wheel.center * scale)
        self.assertEqual(image.pixelColor(east + 2, centre), QColor("black"))
        self.assertEqual(image.pixelColor(east - 3, centre).red(), 255)
        self.assertTrue(any(0 < image.pixelColor(x, y).red() < 255
                            for x in range(east - 5, east + 2)
                            for y in range(centre, centre + round(22 * scale))))
        north = image.pixelColor(centre, round((wheel.center - wheel.r + 12) * scale))
        self.assertGreater(north.green(), north.red())
        self.assertGreater(north.green(), north.blue())

    def test_track_click_jumps_and_emits_commit(self):
        slider = ClickToJumpSlider(Qt.Orientation.Horizontal)
        slider.resize(300, 32)
        slider.setRange(1, 100)
        slider.setValue(10)
        slider.show()
        events = []
        slider.trackClicked.connect(events.append)
        QTest.mouseClick(slider, Qt.MouseButton.LeftButton, pos=QPoint(260, 16))
        self.assertEqual(len(events), 1)
        self.assertGreater(slider.value(), 65)
        self.assertEqual(events[0], slider.value())
        slider.close()


@unittest.skipUnless(ClickToJumpSlider is not None, 'PySide6 not installed (non-UI test environment)')
class TraySettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_restore_and_cancel_are_staged(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "custom.svg"
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48">'
                            '<rect width="48" height="48" fill="#176a95"/></svg>')
            default = QIcon(str(Path(__file__).parent / "assets" / "tray-dark-on.svg"))
            dialog = TraySettingsDialog(parent, str(path), "r1", {"r1": "Room"},
                                        default_icon=lambda selection: default)
            self.addCleanup(dialog.deleteLater)
            self.assertTrue(dialog.restore_button.isEnabled())
            self.assertEqual(dialog.icon_status.text(), "Dynamic lighting status disabled")
            self.assertEqual(dialog.icon_preview.pixmap().toImage().pixelColor(24, 24).name(),
                             "#176a95")
            self.assertIn("Custom icons do not reflect", dialog.icon_notice.text())
            dialog.restore_button.click()
            self.assertEqual(dialog.icon_name, "")
            self.assertFalse(dialog.restore_button.isEnabled())
            self.assertEqual(dialog.icon_status.text(), "Dynamic lighting status enabled")
            self.assertEqual(dialog.icon_preview.pixmap().toImage().pixelColor(24, 19).name(),
                             "#fe8019")
            self.assertEqual(dialog.room.currentData(), "r1")
            dialog.reject()
            self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_picker_selection_updates_preview_but_cancel_keeps_selection(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "custom.svg"
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48">'
                            '<rect width="48" height="48" fill="#176a95"/></svg>')
            dialog = TraySettingsDialog(parent, "", "", {})
            self.addCleanup(dialog.deleteLater)
            self.assertFalse(dialog.restore_button.isEnabled())
            with patch("app.IconPickerDialog") as picker:
                picker.return_value.chosen = str(path)
                picker.return_value.exec.return_value = QDialog.DialogCode.Accepted
                dialog.browse_button.click()
                self.assertEqual(dialog.icon_name, str(path))
                self.assertTrue(dialog.restore_button.isEnabled())
                self.assertEqual(dialog.icon_label.text(), "custom.svg")
                self.assertEqual(dialog.icon_status.text(), "Dynamic lighting status disabled")
                picker.return_value.chosen = ""
                picker.return_value.exec.return_value = QDialog.DialogCode.Rejected
                dialog.browse_button.click()
                self.assertEqual(dialog.icon_name, str(path))
            dialog.restore_button.click()
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
            self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
            self.assertEqual(dialog.icon_name, "")

    def test_icon_action_buttons_have_equal_unclipped_height_and_clearance(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        # Cover larger fonts as well as the usual desktop font size.
        for larger in (False, True):
            with self.subTest(larger_font=larger):
                font = self.app.font()
                if larger:
                    if font.pointSize() > 0:
                        font.setPointSize(font.pointSize() + 6)
                    else:
                        font.setPixelSize(max(1, font.pixelSize()) + 8)
                parent.setFont(font)
                dialog = TraySettingsDialog(parent, "", "r1", {"r1": "Room"})
                self.addCleanup(dialog.deleteLater)
                dialog.show()
                self.app.processEvents()
                browse, restore = dialog.browse_button, dialog.restore_button
                self.assertFalse(restore.isEnabled())
                # Check both the normal opening geometry and the smallest
                # permitted dialog. Compare in one coordinate system because
                # the buttons and notice now have different parent widgets.
                for size in (dialog.size(), dialog.minimumSizeHint()):
                    dialog.resize(size)
                    for enabled in (False, True):
                        restore.setEnabled(enabled)
                        dialog.layout().activate()
                        self.app.processEvents()
                        self.assertEqual(browse.height(), restore.height())
                        header_bottom = max(
                            widget.mapTo(dialog, QPoint(0, widget.height())).y()
                            for widget in (dialog.icon_preview, dialog.icon_label, dialog.icon_status))
                        notice_top = min(
                            widget.mapTo(dialog, QPoint(0, 0)).y()
                            for widget in (dialog.icon_notice, dialog.icon_notice_symbol))
                        for button in (browse, restore):
                            self.assertGreaterEqual(button.height(), 32)
                            self.assertGreaterEqual(button.height(), button.fontMetrics().height() + 12)
                            self.assertGreaterEqual(button.height(), button.sizeHint().height())
                            top = button.mapTo(dialog, QPoint(0, 0)).y()
                            self.assertGreaterEqual(top - header_bottom, 12)
                            self.assertGreaterEqual(notice_top - top - button.height(), 12)
                dialog.close()

    def test_long_room_name_does_not_widen_tray_settings(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        font = parent.font()
        font.setPointSize(18)
        parent.setFont(font)
        full_name = "A long room name with a floor and wing description " * 8
        dialog = TraySettingsDialog(parent, "", "r", {"r": full_name})
        self.addCleanup(dialog.deleteLater)
        dialog.resize(400, 330)
        dialog.show()
        self.app.processEvents()
        self.assertEqual(dialog.room.currentData(), "r")
        self.assertEqual(dialog.room.toolTip(), full_name)
        self.assertLessEqual(dialog.width(), 400)
        scroll = dialog.findChild(QScrollArea)
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        dialog.reject()

    def test_diagnostics_accessible_from_tray_settings_without_closing(self):
        class FakeMain(QWidget):
            def __init__(self):
                super().__init__()
                self.requested_from = None

            def show_tray_diagnostics(self, dialog_parent=None):
                self.requested_from = dialog_parent

        parent = FakeMain()
        dialog = TraySettingsDialog(parent, 'weather-clear', 'r1', {'r1': 'Room'})
        matches = [b for b in dialog.findChildren(QPushButton)
                   if b.text() == 'Input diagnostics…']
        self.assertEqual(len(matches), 1)
        matches[0].click()
        self.assertIs(parent.requested_from, dialog)
        self.assertEqual(dialog.result(), 0)
        dialog.close()
        parent.close()


@unittest.skipUnless(ClickToJumpSlider is not None, 'PySide6 not installed')
class ConnectionDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_generate_button_requires_valid_hub_address(self):
        dialog = ConnectionDialog(None, {})
        self.assertFalse(dialog.generate_button.isEnabled())
        dialog.ip.setText('not a valid hub')
        self.assertFalse(dialog.generate_button.isEnabled())
        dialog.ip.setText('192.168.1.20')
        self.assertTrue(dialog.generate_button.isEnabled())
        dialog.ip.setText('192.168.1.999')
        self.assertFalse(dialog.generate_button.isEnabled())
        dialog.close()

    def test_access_token_visibility_copy_and_new_token_masking(self):
        token = "test-token-only-" + "a" * 40
        dialog = ConnectionDialog(None, {"ip": "192.168.1.20", "token": token})
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.token.echoMode(), QLineEdit.EchoMode.Password)
        self.assertTrue(dialog.copy_token_button.isEnabled())
        with patch("app.QApplication.clipboard") as clipboard:
            dialog.copy_token_button.click()
            clipboard.return_value.setText.assert_called_once_with(token)
        self.assertEqual(dialog.token.echoMode(), QLineEdit.EchoMode.Password)
        dialog.show_token_button.click()
        self.assertEqual(dialog.token.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(dialog.show_token_button.text(), "Hide")
        dialog.show_token_button.click()
        self.assertEqual(dialog.token.echoMode(), QLineEdit.EchoMode.Password)
        dialog.show_token_button.click()
        with patch("app.TokenPairingDialog") as pairing:
            pairing.return_value.exec.return_value = QDialog.DialogCode.Accepted
            pairing.return_value.generated_token = "new-test-token-" + "b" * 40
            dialog.generate_button.click()
            pairing.return_value.deleteLater.assert_called_once()
        self.assertEqual(dialog.token.echoMode(), QLineEdit.EchoMode.Password)
        self.assertFalse(dialog.show_token_button.isChecked())
        self.assertTrue(dialog.token.text().startswith("new-test-token-"))
        self.assertIn("DHCP reservation", dialog.ip_note.text())
        dialog.token.clear()
        self.assertFalse(dialog.copy_token_button.isEnabled())
        self.assertFalse(dialog.show_token_button.isEnabled())
        dialog.reject()

    def test_pairing_dialog_has_two_user_steps_and_private_status(self):
        dialog = TokenPairingDialog(None, "192.168.1.20")
        self.addCleanup(dialog.deleteLater)
        dialog._start_timer.stop()
        self.assertFalse(dialog.continue_button.isEnabled())
        self.assertIn("Preparing", dialog.status_title.text())
        dialog._started()
        self.assertTrue(dialog.continue_button.isEnabled())
        self.assertIn("helper started", dialog.status_title.text())
        self.assertIn(b"#FE8019", hub_action_svg(dialog.palette()))
        self.assertTrue(dialog.hub_illustration.grab().size().width() >= 156)
        dialog._show_failure("Pairing was not completed.")
        self.assertEqual(dialog.continue_button.text(), "Try again")
        self.assertTrue(dialog.continue_button.isEnabled())
        dialog._output.extend(b"private-test-output")
        dialog.reject()
        self.assertFalse(dialog._output)
        self.assertFalse(dialog._start_timer.isActive())

    def test_narrow_hub_and_pairing_dialogs_keep_wrapped_text_readable(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        font = parent.font()
        font.setPointSize(18)
        parent.setFont(font)
        connection = ConnectionDialog(parent, {"ip": "192.168.1.20", "token": "test-token"})
        pairing = TokenPairingDialog(parent, "192.168.1.20")
        pairing._start_timer.stop()
        pairing._set_status("The pairing request timed out",
                            "Check the hub address and make sure the hub is on the same network.", failed=True)

        for dialog in (connection, pairing):
            with self.subTest(dialog=dialog.windowTitle()):
                self.addCleanup(dialog.deleteLater)
                dialog.resize(425, 330)
                dialog.show()
                self.app.processEvents()
                self.assertLessEqual(dialog.width(), 425)
                self.assertLessEqual(dialog.height(), 330)
                scroll = dialog.findChild(QScrollArea)
                self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
                self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
                for label in scroll.widget().findChildren(QLabel):
                    if label.wordWrap():
                        self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()), label.text())
                if dialog is connection:
                    scroll.ensureWidgetVisible(connection.ip_note)
                    self.assertGreater(scroll.verticalScrollBar().value(), 0)
                    buttons = connection.findChild(QDialogButtonBox)
                    self.assertGreater(buttons.mapTo(dialog, QPoint()).y(), scroll.height())
                    self.assertTrue(buttons.button(QDialogButtonBox.StandardButton.Save).isVisible())
                dialog.reject()

    def test_pairing_instructions_stay_together_beside_illustration(self):
        dialog = TokenPairingDialog(None, "192.168.1.20")
        self.addCleanup(dialog.deleteLater)
        dialog._start_timer.stop()
        dialog.resize(680, 490)
        dialog.show()
        self.app.processEvents()
        first, second = [label for label in dialog.findChildren(QLabel)
                         if label.text().startswith(("<b>1.", "<b>2."))]
        first_bottom = first.mapTo(dialog, QPoint(0, first.height())).y()
        second_top = second.mapTo(dialog, QPoint()).y()
        self.assertGreaterEqual(second_top, first_bottom)
        self.assertLessEqual(second_top - first_bottom, first.fontMetrics().lineSpacing())
        dialog.reject()




@unittest.skipUnless(ClickToJumpSlider is not None, 'PySide6 not installed')
class PanelIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_all_four_tray_assets_have_exact_colours_and_transparency(self):
        assets = Path(__file__).resolve().parent / "assets"
        for mode, base in (("light", "#282828"), ("dark", "#ebdbb2")):
            for active in (False, True):
                with self.subTest(mode=mode, active=active):
                    suffix = "-on" if active else ""
                    icon = QIcon(str(assets / f"tray-{mode}{suffix}.svg"))
                    image = icon.pixmap(64, 64).toImage()
                    self.assertFalse(image.isNull())
                    self.assertEqual(image.pixelColor(32, 25).name(),
                                     "#fe8019" if active else base)
                    self.assertEqual(image.pixelColor(32, 50).name(), base)
                    self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual((assets / "io.github.alsiniz.Lysnav.svg").read_bytes(),
                         (assets / "lysnav-logo.svg").read_bytes())

    def test_explicit_plasma_theme_precedes_app_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "plasmarc").write_text("[Theme]\nname=test-dark\n")
            colours = root / "plasma" / "desktoptheme" / "test-dark" / "colors"
            colours.parent.mkdir(parents=True)
            colours.write_text("[Colors:Window]\nBackgroundNormal=32,32,32\n")
            with patch.dict(os.environ, XDG_CONFIG_HOME=folder,
                            XDG_DATA_HOME=folder, XDG_DATA_DIRS=folder):
                self.assertTrue(panel_is_dark(palette))
                colours.unlink()
                self.assertFalse(panel_is_dark(palette))

    def test_panel_modes_and_custom_override(self):
        self.enterContext(patch('app.panel_is_dark', side_effect=lambda p: p.window().color().lightness() < 128))
        settings = dict(ip='test', token='test', approved={}, approved_sensors={})
        with patch('app.read_config', return_value=settings), patch.object(MainWindow, 'start_worker'), \
                patch.object(MainWindow, '_create_native_tray'):
            window = MainWindow()
        self.addCleanup(window.deleteLater)

        def set_background(colour):
            palette = QPalette(window.palette())
            palette.setColor(QPalette.ColorRole.Window, QColor(colour))
            window.setPalette(palette)

        def centre():
            return window._selected_qicon().pixmap(32, 32).toImage().pixelColor(16, 16).name()

        set_background('#ffffff')
        self.assertEqual(centre(), '#282828')
        self.assertEqual(window.windowIcon().pixmap(64, 64).toImage().pixelColor(32, 20).name(), '#fe8019')
        set_background('#121212')
        self.assertEqual(centre(), '#ebdbb2')

        with TemporaryDirectory() as folder:
            path = Path(folder) / 'custom.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
                            '<rect width="16" height="16" fill="#176a95"/></svg>')
            with patch('app.discover_system_icons', return_value=('test', {})):
                picker = IconPickerDialog(window, '')
            with patch('app.QFileDialog.getOpenFileName', return_value=(str(path), '')):
                picker.choose_file()
            window.config['tray_icon'] = picker.chosen
            set_background('#ffffff')
            self.assertEqual(centre(), '#176a95')
            name, pixmaps = window._notifier_icon(window._selected_qicon())
            self.assertEqual(name, '')
            self.assertEqual(pixmaps[0], [16, 16, bytes.fromhex('ff176a95') * 256])

            window.config['tray_icon'] = 'my-installed-icon'
            with patch.object(QIcon, 'fromTheme', return_value=QIcon(str(path))):
                set_background('#121212')
                self.assertEqual(centre(), '#176a95')
                self.assertEqual(window._notifier_icon(window._selected_qicon())[0], 'my-installed-icon')

            picker.choose_default()
            window.config['tray_icon'] = picker.chosen
            window._apply_panel_icon()
            self.assertEqual(centre(), '#ebdbb2')
            with patch.object(QIcon, 'hasThemeIcon', return_value=True):
                self.assertEqual(window._notifier_icon(window._selected_qicon())[0], '')
            with patch.object(QIcon, 'hasThemeIcon', return_value=False), patch.dict(os.environ, FLATPAK_ID=''):
                name, pixmaps = window._notifier_icon(window._selected_qicon())
                self.assertEqual(name, '')
                self.assertTrue(pixmaps)


@unittest.skipUnless(ClickToJumpSlider is not None, 'PySide6 not installed')
class RefreshLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        config = dict(ip='test', token='test', approved={'lamp': 'room'}, approved_sensors={'sensor': 'room'},
                      tray_room='room')
        self.enterContext(patch('app.read_config', return_value=config))
        self.enterContext(patch.object(MainWindow, '_create_native_tray'))
        with patch.object(MainWindow, 'start_worker'):
            self.window = MainWindow()
        self.addCleanup(self.flush_deletions)
        self.addCleanup(self.window.deleteLater)
        self.light = LightInfo('lamp', 'Desk', 'room', 'Study', True, ('isOn', 'lightLevel'),
                               True, 50, None, None, None, 0, 1)
        self.sensor = EnvironmentInfo('sensor', 'Climate', 'room', 'Study', True, 20, 50, 90)

    def flush_deletions(self):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_failed_first_hub_read_retries_and_updates_tray_icon(self):
        window = self.window
        self.enterContext(patch("dirigera.Hub"))
        snapshot = self.enterContext(patch("app.snapshot", side_effect=TimeoutError("Hub unreachable")))
        self.enterContext(patch("app.environment_snapshot", return_value=[]))
        window.start_worker()
        self.addCleanup(window.worker.wait)
        self.addCleanup(window.worker.stop)
        self.addCleanup(window.refresh_timer.stop)

        for _ in range(200):
            if window.status.text().startswith("Request failed"):
                break
            QTest.qWait(10)
        self.assertIn("Hub unreachable", window.status.text())
        self.assertTrue(window.refresh_timer.isActive())

        snapshot.side_effect = None
        snapshot.return_value = [self.light]
        window.refresh_timer.setInterval(25)
        for _ in range(200):
            if not window._tray_state_stale:
                break
            QTest.qWait(10)
        self.assertFalse(window._tray_state_stale)
        image = window._selected_qicon().pixmap(64, 64).toImage()
        self.assertEqual(image.pixelColor(32, 25).name(), "#fe8019")

    def test_individual_temperature_stays_usable_in_rgb_mode(self):
        window = self.window
        rgb_light = replace(self.light, color_mode="color", temperature=2700,
                            temp_low=2200, temp_high=6500,
                            capabilities=self.light.capabilities + ("colorTemperature", "colorHue", "colorSaturation"))
        window.on_loaded(([rgb_light], [], ""))
        _, individual = window.tabs.findChildren(TemperatureSlider)
        self.assertEqual(individual.light_ids, (rgb_light.id,))
        self.assertTrue(individual.isEnabled())
        self.assertIn("Adjust to switch this light to white", individual.accessibleDescription())
        self.assertEqual(individual.readout.text(), "RGB mode")

        window.worker = MagicMock()
        QTest.keyClick(individual, Qt.Key.Key_End)
        window.flush_slider_wheel()
        window.worker.submit.assert_called_once_with("control", [rgb_light.id], "temperature", 6500)
        self.assertEqual(individual.readout.text(), "6500 K")
        self.assertTrue(individual._dimmed)
        window.on_failed("timeout")
        self.assertEqual(individual.readout.text(), "RGB mode")

        window.on_loaded(([replace(rgb_light, color_mode="temperature", temperature=6500)], [], ""))
        self.flush_deletions()
        _, individual = window.tabs.findChildren(TemperatureSlider)
        self.assertEqual(individual.readout.text(), "6500 K")
        self.assertEqual(individual.accessibleDescription(), "")
        self.assertFalse(individual._dimmed)

    def test_room_temperature_state_and_shared_command_range(self):
        window = self.window
        window.config["approved"]["lamp2"] = "room"
        window.worker = MagicMock()
        white = replace(self.light, color_mode="temperature", temperature=3000,
                        temp_low=2200, temp_high=6500,
                        capabilities=self.light.capabilities + ("colorTemperature",))
        other = replace(white, id="lamp2", temp_low=2700, temp_high=5000)
        unapproved = replace(white, id="unapproved", temp_low=3500, temp_high=4000)
        cases = [
            (white, other, "3000 K", False),
            (white, replace(other, temperature=4700), "Mixed temperatures", False),
            (white, replace(other, color_mode="color"), "Mixed modes", True),
            (replace(white, color_mode="color"), replace(other, color_mode="color"), "RGB mode", True),
            (replace(white, temperature=7000), other, "Mixed modes", True),
        ]
        for first, second, status, dimmed in cases:
            with self.subTest(status=status):
                window.on_loaded(([first, second, unapproved], [], ""))
                self.flush_deletions()
                room = next(slider for slider in window.tabs.findChildren(TemperatureSlider)
                            if slider.room_hint is not None)
                self.assertEqual(room.readout.text(), status)
                self.assertEqual(room._dimmed, dimmed)
                self.assertEqual(room.room_hint.isHidden(), not dimmed)
                self.assertEqual((room.minimum(), room.maximum()), (2700, 5000))
                self.assertTrue(room.isEnabled())
                if status == "Mixed modes":
                    QTest.keyClick(room, Qt.Key.Key_End)
                    window.flush_slider_wheel()
                    window.worker.submit.assert_called_once_with(
                        "control", ["lamp", "lamp2"], "temperature", 5000)
                    self.assertEqual(room.readout.text(), "5000 K")
                    self.assertTrue(room._dimmed)
                    window.worker.submit.reset_mock()

    def test_tray_selection_controls_icon_and_middle_click_targets(self):
        window = self.window
        window.worker = MagicMock()
        window.config["approved"].update({"other": "other-room", "relocated": "room"})
        unapproved = replace(self.light, id="unapproved")
        moved = replace(self.light, id="relocated", room_id="moved")
        off = replace(self.light, on=False)
        other_room = replace(self.light, id="other", room_id="other-room", room_name="Office")
        with patch('app.panel_is_dark', return_value=True):
            def shade():
                return window._selected_qicon().pixmap(64, 64).toImage().pixelColor(32, 25).name()
            def app_shade():
                return window.windowIcon().pixmap(64, 64).toImage().pixelColor(32, 20).name()

            window.on_loaded(([off, other_room, unapproved, moved], [], ""))
            self.assertEqual(shade(), "#ebdbb2")
            self.assertEqual(app_shade(), "#fe8019")
            window.on_tray_middle()
            window.worker.submit.assert_called_once_with("toggle", ["lamp"], "room")

            dialog = TraySettingsDialog(window, "", "room", window._approved_rooms(),
                                        default_icon=window._default_qicon)
            self.addCleanup(dialog.deleteLater)
            dialog.room.setCurrentIndex(dialog.room.findData(ALL_APPROVED))
            self.assertEqual(dialog.icon_preview.pixmap().toImage().pixelColor(24, 18).name(), "#fe8019")
            self.assertEqual(shade(), "#ebdbb2")

            window.worker.submit.reset_mock()
            with patch("app.write_config"):
                window.set_tray_room(ALL_APPROVED)
            self.assertEqual(shade(), "#fe8019")
            window.on_tray_middle()
            window.worker.submit.assert_called_once_with("toggle", ["lamp", "other"], ALL_APPROVED)
            window.on_failed("offline")
            self.assertEqual(shade(), "#fe8019")
            self.assertIn("last known", window._tray_tooltip())
            window.on_loaded(([off, unapproved, moved], [], ""))
            self.assertEqual(shade(), "#ebdbb2")
            self.assertNotIn("last known", window._tray_tooltip())
            window.on_loaded(([self.light], [], ""))
            window.config["approved"] = {}
            window.update_tray_tooltip()
            self.assertEqual(shade(), "#ebdbb2")
            self.assertEqual(app_shade(), "#fe8019")

    def test_memory_stress_dynamic_icons_refresh_and_dialogs(self):
        """Exercise thousands of updates; assert bounded live resources after warmup."""
        window = self.window
        mode = [False]
        states = (replace(self.light, on=False), self.light)
        # Exercise the Qt tray fallback and native pixmap creation without a real panel.
        window.tray = QSystemTrayIcon(window)
        from tray_sni import Item

        item = Item(window.tray_signals, "", "")
        class LocalNotifier:
            def update(self, *, icon=None, tooltip=None, pixmaps=None, menu_model=None):
                item.update(icon=icon, tooltip=tooltip, pixmaps=pixmaps)
        window.tray_sni = LocalNotifier()
        self.addCleanup(setattr, window, "tray_sni", None)
        window._apply_panel_icon(force=True)
        with TemporaryDirectory() as folder, patch("app.panel_is_dark", new=lambda palette: mode[0]):
            custom_paths = []
            for i in range(8):
                path = Path(folder) / f"custom-{i}.svg"
                path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
                                '<rect width="32" height="32" fill="#176a95"/></svg>')
                custom_paths.append(str(path))

            def drain():
                self.app.processEvents()
                self.flush_deletions()
                gc.collect()

            def exercise():
                # All four state combinations. Do not let a recording mock
                # itself accumulate thousands of call objects.
                for n in range(500):
                    mode[0] = bool(n & 2)
                    window.lights = [states[n & 1]]
                    window.update_tray_tooltip()
                for n in range(50):
                    mode[0] = bool(n & 2)
                    old = window.tabs.widget(0)
                    window.on_loaded(([states[n & 1]], [self.sensor], ""))
                    self.flush_deletions()
                    if old is not None:
                        self.assertFalse(isValid(old))
                for n in range(16):
                    path = custom_paths[n % len(custom_paths)]
                    window.config["tray_icon"] = path
                    window._apply_panel_icon()
                    dialog = TraySettingsDialog(window, "", "room", {"room": "Study"},
                            default_icon=window._default_qicon)
                    dialog.icon_name = path
                    dialog.update_icon_preview()
                    dialog.restore_default_icon()
                    dialog.reject()
                    dialog.deleteLater()
                    self.flush_deletions()
                    self.assertFalse(isValid(dialog))
                window.config["tray_icon"] = ""
                mode[0] = False
                window.lights = [states[0]]
                window.update_tray_tooltip()
                drain()

            # First batch fills Qt/font/icon caches and establishes steady state.
            exercise()
            baseline_objects = len(window.findChildren(QObject))
            self.assertEqual(len(window._panel_icon_cache), 4)
            before = process_memory_bytes()
            already_tracing = tracemalloc.is_tracing()
            if not already_tracing:
                tracemalloc.start()
            try:
                drain()
                baseline_python = tracemalloc.get_traced_memory()[0]
                samples = []
                for batch in range(4):
                    exercise()
                    current = tracemalloc.get_traced_memory()[0]
                    rss = process_memory_bytes()
                    objects = len(window.findChildren(QObject))
                    samples.append((batch + 1, current - baseline_python, rss, objects))
                    self.assertLessEqual(objects, baseline_objects + 4)
                    self.assertFalse(window.findChildren(TraySettingsDialog))
                    self.assertEqual(len(window._panel_icon_cache), 4)
                retained = tracemalloc.get_traced_memory()[0] - baseline_python
                print(f"MEMORY_STRESS: warmup=1 batch; measured=2000 icon updates, "
                      f"200 refreshes, 64 custom icon/dialog cycles; "
                      f"baseline_objects={baseline_objects}; baseline_rss_bytes={before}; "
                      f"samples(batch,python_delta_bytes,rss_bytes,qt_objects)={samples}; "
                      f"final_python_delta_bytes={retained}", flush=True)
                # A generous guard against sustained Python allocation growth;
                # RSS is reported, not gated because native allocators retain arenas.
                self.assertLess(retained, 2 * 1024 * 1024)
            finally:
                if not already_tracing:
                    tracemalloc.stop()
            self.assertEqual(len(window._panel_pixmap_cache), 4)
            self.assertTrue(all(len(pixmaps) == 5 for pixmaps in window._panel_pixmap_cache.values()))
            self.assertEqual(len(item.pixmaps), 5)


    def test_repeated_refresh_disposes_old_pages_and_reuses_menu(self):
        window = self.window
        welcome = window.tabs.widget(0)
        window.on_loaded(([self.light], [self.sensor], ''))
        room, climate = (window.tabs.widget(i) for i in range(2))
        window.tabs.setCurrentIndex(1)
        submenu, = window._tray_menu.findChildren(QMenu)
        all_lights, study = submenu.actions()
        for _ in range(20):
            window.on_loaded(([self.light], [self.sensor], ''))
            self.flush_deletions()
        self.assertFalse(any(isValid(page) for page in (welcome, room, climate)))
        self.assertEqual(window.tabs.currentIndex(), 1)
        self.assertEqual(len(window.tabs.findChildren(QScrollArea)), 2)
        self.assertEqual(window._tray_menu.findChildren(QMenu), [submenu])
        self.assertEqual(submenu.actions(), [all_lights, study])
        with patch('app.write_config'):
            study.trigger()
            self.assertEqual(window.config['tray_room'], 'room')
            self.assertTrue(study.isChecked())
            all_lights.trigger()
            self.assertEqual(window.config['tray_room'], ALL_APPROVED)
            self.assertTrue(all_lights.isChecked())
        window.on_loaded(([replace(self.light, room_name='Office')], [], ''))
        self.flush_deletions()
        self.assertEqual([a.text() for a in submenu.actions()], ['All approved lights', 'Office'])
        window.on_loaded(([], [], ''))
        self.flush_deletions()
        self.assertEqual(len(submenu.actions()), 1)
        self.assertFalse(window.tabs.findChildren(QScrollArea))
        self.assertEqual(window.tabs.count(), 1)

    def test_tray_settings_is_disposed_after_save_and_cancel(self):
        for dismiss in ('accept', 'reject'):
            QTimer.singleShot(0, lambda: getattr(self.app.activeModalWidget(), dismiss)())
            with patch('app.write_config'):
                self.window.change_tray_settings()
            self.flush_deletions()
            self.assertFalse(self.window.findChildren(TraySettingsDialog))


if __name__ == '__main__':
    unittest.main()
