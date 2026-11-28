# Packaging

## AppImage

The v1.1.0 release distributes `Lysnav-Plasma-v1.1.0-x86_64.AppImage` and its SHA-256 checksum through [GitHub Releases](https://github.com/alsiniz/lysnav-plasma/releases/tag/v1.1.0). Bazzite KDE Plasma is the distribution verified on a real desktop so far.

Build: `./packaging/appimage/build.sh`. CI runs `.github/workflows/release-appimage.yml`, uploads the AppImage and `SHA256SUMS.txt`, and tags the build commit with the version from `version.py`.

Lysnav releases use `Lysnav-Plasma-<tag>-x86_64.AppImage` and `SHA256SUMS.txt`.

A direct portable run may emit a nonfatal XDG desktop-portal app-ID warning because the AppImage is not installed as a registered desktop application.

## Flatpak (experimental)

The Flatpak CI build succeeds but has **not** been run and approved on a real KDE Plasma session. Do not distribute it until its integration is validated. It uses `io.github.alsiniz.Lysnav` with scoped networking and D-Bus permissions and separate sandboxed credentials.

Build locally: `./packaging/flatpak/build.sh`. Install an experimental bundle with `flatpak install --user ./lysnav.flatpak`.

## Minimum runtime checks

- Fresh install / GUI DIRIGERA hub authorization
- Explicit device approval and multi-resident household safeguards
- Per-room and per-device RGB, brightness, colour temperature and power
- Tray climate tooltip, scroll brightness, middle-click toggle, right-click native menu and Quit
- Theme integration, icon picker, and window title
- License/third-party notices and absence of stored credentials in build artifacts

Do not claim universal distro support from CI build success alone.
