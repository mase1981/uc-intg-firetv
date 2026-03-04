# Fire TV Integration for Unfolded Circle Remote Two/3

![Fire TV](https://img.shields.io/badge/Fire-TV-red)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-firetv?style=flat-square)](https://github.com/mase1981/uc-intg-firetv/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-firetv?style=flat-square)](https://github.com/mase1981/uc-intg-firetv/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads](https://img.shields.io/github/downloads/mase1981/uc-intg-firetv/total)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA)](https://github.com/sponsors/mase1981/button)

Control your Amazon Fire TV devices directly from your Unfolded Circle Remote Two/3 using the official **Fire TV REST API** with instant response times.

---

## Features

- **Instant Response** - REST API delivers ultra-fast command execution (~50ms)
- **Complete Navigation** - D-Pad, Home, Back, Menu controls
- **Power Control** - Sleep/Wake support
- **Media Controls** - Play/Pause, Fast Forward, Rewind
- **Number Keypad** - Send numbers 0-9 and text input
- **Quick Launch Apps** - One-tap access to popular streaming apps
- **Custom App Launcher** - Launch ANY Fire TV app using package name
- **Physical Button Mapping** - Map to UC Remote hardware buttons
- **Secure Authentication** - PIN-based token authentication

---

## Limitations

### No Volume Control
Volume is controlled by your TV/AVR, not Fire TV. Use your TV integration or HDMI-CEC.

### No State Feedback
The REST API cannot query current state - this is a command-only remote entity.

---

## Requirements

### Hardware
- Fire TV 4K Max Gen 2 or compatible device with REST API
- Unfolded Circle Remote Two or Remote 3
- Same local network

### Software
- Fire TV with REST API enabled (default on 4K Max Gen 2)
- UC Remote firmware 1.7.0+

---

## Installation

### Option 1: GitHub Release (Recommended)

1. Download latest `.tar.gz` from [Releases](https://github.com/mase1981/uc-intg-firetv/releases)
2. Open UC Remote configurator: `http://your-remote-ip/configurator`
3. **Integrations** → **Add Integration** → **Upload driver**
4. Select downloaded file
5. Follow setup wizard

### Option 2: Docker

```bash
docker run -d --name uc-intg-firetv \
  --restart unless-stopped \
  --network host \
  -v $(pwd)/data:/data \
  -e UC_CONFIG_HOME=/data \
  -e UC_INTEGRATION_INTERFACE=0.0.0.0 \
  -e UC_INTEGRATION_HTTP_PORT=9090 \
  -e UC_DISABLE_MDNS_PUBLISH=false \
  ghcr.io/mase1981/uc-intg-firetv:latest
```

Or with docker-compose:
```bash
git clone https://github.com/mase1981/uc-intg-firetv.git
cd uc-intg-firetv
docker-compose up -d
```

### Option 3: Development

```bash
git clone https://github.com/mase1981/uc-intg-firetv.git
cd uc-intg-firetv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m intg_firetv
```

---

## Setup

### Step 1: Find Fire TV IP
Fire TV: **Settings** → **Network** → Note IP address

### Step 2: Add Integration
1. UC Remote configurator → **Integrations** → **Add**
2. Select **Fire TV**
3. Enter Fire TV IP and port (default: 8080)
4. Click **Next**

### Step 3: Enter PIN
1. A 4-digit PIN appears on your TV
2. Enter PIN in UC Remote (within 60 seconds)
3. Click **Complete**

Done! Your Fire TV Remote entity is ready to use.

---

## Controls

### Navigation
- D-Pad (↑↓←→), Select, Home, Back, Menu

### Power
- **HOME** - Wakes Fire TV from sleep
- **SLEEP** - Puts Fire TV to sleep
- **POWER** - Power toggle

### Media
- Play/Pause, Fast Forward, Rewind

### Pre-configured Apps
- Netflix, Prime Video, Disney+, Plex, Kodi

### Custom App Launch
Launch any app using: `custom_app:com.package.name`

**Examples:**
- YouTube: `custom_app:com.amazon.firetv.youtube`
- Hulu: `custom_app:com.hulu.plus`
- HBO Max: `custom_app:com.wbd.stream`
- Apple TV+: `custom_app:com.apple.atve.amazon.appletv`
- Spotify: `custom_app:com.spotify.tv.android`

**Find Package Names:**
Fire TV **Settings** → **Applications** → **Manage Installed Applications** → Select app → Package name shown at bottom

---

## Activity Commands

### Navigation
`DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`, `SELECT`, `HOME`, `BACK`, `MENU`

### Power
`POWER`, `SLEEP`, `HOME` (also wakes device)

### Media
`PLAY_PAUSE`, `FAST_FORWARD`, `REWIND`

### Apps
`LAUNCH_NETFLIX`, `LAUNCH_PRIME_VIDEO`, `LAUNCH_DISNEY_PLUS`, `LAUNCH_PLEX`, `LAUNCH_KODI`

### Custom
`custom_app:com.package.name`

---

## Troubleshooting

### Fire TV Not Found
- Verify IP address is correct
- Ensure same network (check AP isolation)
- Fire TV must be powered on

### No PIN Displayed
- Wake Fire TV first
- Check correct TV input
- Verify Fire TV model supports REST API

### Commands Not Working
- Try HOME button to wake device
- Check network connectivity
- View integration logs

---

## Technical Details

| Property | Value |
|----------|-------|
| Protocol | REST API / HTTPS:8080 |
| Auth | PIN-based token (persistent) |
| Entity | Remote (command-only) |
| Response | ~50ms |

---

## Contributing

1. Fork repository
2. Create feature branch
3. Test changes
4. Submit PR

[Report Bug](https://github.com/mase1981/uc-intg-firetv/issues) · [Request Feature](https://github.com/mase1981/uc-intg-firetv/issues)

---

## Support

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/mase1981)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/meirmiyara)

---

## License

MPL-2.0 License - See [LICENSE](LICENSE) file

---

## Credits

- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara/)
- **Framework**: [Unfolded Circle ucapi](https://github.com/unfoldedcircle/integration-python-library)
- **REST API Discovery**: [SLC-Josh](https://github.com/SLC-Josh/)

---

## Links

- [GitHub Issues](https://github.com/mase1981/uc-intg-firetv/issues)
- [Discussions](https://github.com/mase1981/uc-intg-firetv/discussions)
- [UC Community Forum](https://unfolded.community/)

---

## Disclaimer

Unofficial integration. Not affiliated with Amazon or Unfolded Circle.

- Fire TV is a trademark of Amazon.com, Inc.
- Unfolded Circle and Remote Two/3 are trademarks of Unfolded Circle ApS

---

<div align="center">

Made with ❤️ by [Meir Miyara](https://www.linkedin.com/in/meirmiyara/)

⭐ Star this repo if you find it useful!

</div>
