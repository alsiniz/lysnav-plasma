# Changelog

## [1.1.0] - 2026-11-28

- Colour temperature sliders use a fixed warm-to-cool gradient. RGB mode dims the track while keeping the slider usable.
- Room controls identify mixed temperatures and mixed modes. Adjusting the room slider switches all approved lights in that room to white within their shared temperature range.
- The temperature track and thumb have clean edges, and the live colour wheel is antialiased at the display's scale.

## [1.0.5] - 2026-11-28

- Dialogs adapt to font size and available screen space. Long forms scroll with their action buttons visible.
- Hub settings gives the DHCP note room to wrap. The two pairing instructions stay together beside the hub illustration.
- The existing colour temperature slider shows the selected Kelvin value as a live tint. Its track is muted in RGB mode, and keyboard adjustments use the existing temperature command.

## [1.0.4] - 2026-11-28

- Redesigned Hub settings and token pairing with token reveal/copy controls, a two-action pairing guide, palette-adaptive vector illustration, and static IP/DHCP reservation guidance.
- Separated tray appearance controls and disclaimer into independent layout rows with reserved vertical clearance, including at the dialog's minimum size.
- Prevented vertically compressed tray appearance buttons with a shared minimum height that accounts for native font and style metrics.
- Redesigned Tray settings into room selection, tray appearance and aligned mouse controls. Added an icon preview, a clear custom-icon status disclaimer and a one-click restore-default action; changes are applied only on Save.
- The default tray lamp turns orange when any approved light in the tray selection is on. Choose one room or All approved lights for the indicator, middle-click and brightness scrolling.
- Automatic refresh retries after the first hub check fails.
- Full-colour Lysnav logo is used for application windows, launchers and package icons; raster package icons are generated from the canonical SVG.

## [1.0.3] - 2026-11-27

- Published the first stable AppImage under the Lysnav name. It includes the table lamp logo, monochrome panel icons, custom icon support, and the v1.0.1 tray memory fix.
- Added the 256-pixel lamp icon used for the AppImage in file managers.
- Updated the download instructions and documented when the AppImage reads the old configuration and where it saves subsequent changes.

## 1.0.2 (CI build only, 2026-11-27)

- Includes the refresh-time memory fix from 1.0.1 for long-running tray sessions.
- Adopted the Table Lamp logo and monochrome light- and dark-panel icons. KDE keeps saved overrides and accepts theme icons or local image files.
- Renamed the app to Lysnav for KDE Plasma. The README and About view now identify Lysnav as an independent third-party app.
- Renamed the executable to `lysnav` and the Flatpak and desktop ID to `io.github.alsiniz.Lysnav`. Native installs read existing pairing and device approvals on upgrade. The new Flatpak ID has its own sandbox.
- Future AppImage downloads use the `Lysnav-Plasma-` prefix. Published releases retain their original filenames and checksums.

## [1.0.1] - 2026-11-26

- Fixed memory growth during the 30-second hub refresh. Replaced room and climate pages now release their widgets, including while the window is hidden in the tray.
- Reused the tray menu and its room submenu across refreshes. The list of room actions updates when the approved rooms change.
- Released the Tray Settings dialog after both Save and Cancel.
- Added Qt regression tests for repeated refreshes, room selection, and dialog disposal.

## [1.0.0] - 2026-11-23

First stable release, distributing the **x86_64 AppImage**. Verified on Bazzite KDE Plasma with fresh in-app DIRIGERA pairing and local lighting controls.

- Native Plasma tray scroll-to-dim, middle-click toggle, right-click actions, climate tooltip and brightness OSD.
- Per-room and per-light controls, live colour wheel, supported colour-temperature changes, and explicit device approval for shared homes.
- GUI-only token authorization and active KDE icon-theme integration.
- Improved room/individual-control visual hierarchy and main-window identity.
- AppImage packaging fixes for host Fontconfig and Wayland tooltip warnings; a nonfatal portal registration warning may remain during direct portable execution.
- Flatpak built in CI, **held for runtime validation** and not included in this release.

## Unreleased development build 1.0.0-dev.7 (2026-11-22)

- Added a **Generate token** button beside the masked Access token field in
  Hub settings. It stays disabled for blank and malformed hub addresses.
- Built an asynchronous, cancelable GUI pairing flow around the existing
  local `dirigera` authentication helper. Press DIRIGERA's physical action
  button, click Continue, and the generated token populates the field. The
  user explicitly saves it; no terminal, shell, clipboard, or token log.
- Enlarged Hub settings to avoid clipping the DHCP reservation guidance.
- Credited **alsiniz** as project creator and maintainer, linking to the
  project repository from the About dialog.
- Left the known-working Plasma native tray menu, wheel and middle-click
  implementation untouched. Remains an unreleased test build.

## Unreleased development build 1.0.0-dev.6 (2026-11-22)

- Tidied main-window buttons: **Choose devices** and **Tray settings** no
  longer end with ellipses.
- Renamed **Tray icon** to **App icon** in system tray settings and added a
  dedicated shortcut explanation covering scroll-to-dim and middle-click toggle.
- Added DHCP reservation advice to Hub settings to keep DIRIGERA's local address stable.
- Added an About dialog **Support on Ko-fi** button linking to
  https://ko-fi.com/alsiniz. No embedded browser or automatic network requests.
- Removed the brightness OSD's unnecessary icon by passing an empty icon name
  to Plasma's `showText` method; kept text and command timing unchanged.
- Preserved dev.5's working native Plasma right-click menu, wheel and middle-click,
  the MIT license, and approved-device safety model. Public release still paused.


## Unreleased development build 1.0.0-dev.5 (2026-11-22)

- Fixed the native D-BusMenu `GetLayout` serialization failure reported by
  Bazzite/Python 3.15: `dbus-next` requires lists for D-Bus STRUCT values,
  including those nested inside `Variant('(ia{sv}av)', ...)`.
- Fixed `GetGroupProperties` to return nested list structs as well, avoiding
  a related failure when Plasma inspects menu-item properties.
- Removed the top-level **System tray** menu bar and placed **Input diagnostics…**
  inside **Tray settings…**. Removed the redundant diagnostics action from
  the native tray menu, while retaining its accessible settings entry.
- Added regression checks for nested D-Bus struct types, submenu properties,
  and access to the diagnostics button inside the settings dialog.
- Preserved the working tray wheel/middle-click, MIT license, approved-light
  safety checks, and clear token-security notice. Not a public release.

## Unreleased development build 1.0.0-dev.4 (2026-11-22)

- **Not release-ready:** Native right-click now works on the tester's KDE Plasma,
  but tray wheel events are regressed. This is an investigation build, **not** a
  claimed scroll fix. Middle-click still works.
- Added D-Bus-side Scroll call count and last-delta diagnostics, separate from
  the Qt GUI scroll-event record. This distinguishes Plasma not forwarding the
  wheel from the application failing to process a forwarded event.
- Icon picker now reads the selected KDE icon theme from `kdeglobals`, scans
  user/system-installed theme files and inherited themes, and uses Qt's
  theme-native rendering when available. No icon pack is bundled.
- Retained the native Plasma menu, per-device controls, slider wheel behavior,
  MIT License and user-friendly hub-token security wording.
- GitHub and Flatpak/AppImage publication remain paused.

# Changelog

## Unreleased development build 1.0.0-dev.2 (2026-11-22)

- Fixed mouse-wheel changes to brightness and Kelvin sliders not reaching DIRIGERA. Commands are debounced (250 ms) and retain per-device approval checks.
- Disabled unreliable D-BusMenu import by default using KDE's `/NO_DBUSMENU` convention, making native right-click call `ContextMenu` and open a compositor-positioned tray-actions window instead of off-screen QMenu popups.
- Added D-BusMenu self-test and menu request diagnostics; native Plasma right-click remains under real-device verification.
- Corrected D-BusMenu root node properties for compatibility.
- Replaced the proposed noncommercial source-available license with the standard MIT License.
- Rewrote the About dialog's access-token security note in plain language.
- Paused all public release and binary packaging until menu and slider behavior are confirmed on KDE Plasma.

# Changelog

## [1.0.0-rc.1] - 2026-11-22

First public release candidate, renamed **DIRIGERA Plasma**.

### Added
- Plasma-rendered native D-BusMenu for right-click actions, replacing the Qt
  popup's unreliable Wayland positioning.
- About dialog with version, third-party dependencies, protocol credits and
  independent-project disclaimer.
- Repository documentation, issue template, offline/Qt tests, experimental Flatpak and AppImage build workflows, and release notes.
- Automatic one-time migration of the previous `dirigera-desktop` configuration
  (hub token, device/sensor approvals, room and icon selection).

### Changed
- Brightness scroll notifications now show the target percentage without the
  word "pending"; command debouncing remains at 600 ms.
- Display name, desktop entry and configuration path use DIRIGERA Plasma.
- Clicks on the brightness and temperature slider tracks now send commands, while dragging still applies on release.
- Source license restricts commercialized derivatives (not an OSI open-source license).
- Ctrl+Q cleanly quits the app even if the tray menu is inaccessible.

### Retained from the private 0.x prototypes
- Separate per-device and approved-room controls; live HSV colour wheel.
- Kelvin, brightness, and on/off controls subject to bulb capabilities.
- Temperature and humidity readings from related TIMMERFLOTTE endpoints.
- Tray wheel brightness, middle-click toggle, and Breeze icon selection.
- Deny-by-default device ID + room ID validation before lighting commands.

### Known limitations
- The local DIRIGERA API is undocumented and may change in hub firmware.
- Native D-BusMenu has not yet been tested in the user's running Plasma session;
  this version is a release **candidate** until that regression is confirmed fixed.
- Changes to different bulbs are not atomic; interruption during a group write
  can leave partially changed lighting states.
- The stored token is plaintext in a user-private (0600) file and has hub-wide
  privileges; app authorization is a safety constraint, not a hub permission.
