# ehpa desktop icons (2026-10-29)

Desktop / shortcut icons for the billing pages, drawn from the ehpa brand (the healthcare-cross ring open on the right; Claimocity palettes).

| Icon | Scheme | Files | Opens |
|---|---|---|---|
| ehpa Billing Button | Midnight ground, sky→magenta gradient mark, magenta run badge | `ehpa_billing_button.svg` (source), `.ico` (256/128/64/48/32/16), `_512.png` | https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ |
| Claimocity Feed Monitoring | Light scheme (white, dark-blue mark, #0054e9 bars, magenta live dot) | `claimocity_feed_monitoring_light.svg`, `.ico`, `_512.png` | https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk |

Rebuild: render the SVG at 1024 px with a transparent background (Playwright/Chromium screenshot with omitBackground) and pack the ICO with Pillow
(`Image.save(..., sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])`). Windows shortcut: right-click the shortcut → Properties → Change Icon → Browse → the .ico.
macOS: open the PNG in Preview, Select All, Copy; Get Info on the alias; click the icon top-left; Paste.
