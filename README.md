# Fire TV Integration for Unfolded Circle Remote Two/3

![firetc](https://img.shields.io/badge/Fire-TV-red)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-firetv?style=flat-square)](https://github.com/mase1981/uc-intg-firetv/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-firetv?style=flat-square)](https://github.com/mase1981/uc-intg-firetv/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://community.unfoldedcircle.com/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-firetv)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-firetv/total)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA)](https://github.com/sponsors/mase1981/button)

Control your Amazon Fire TV devices directly from your Unfolded Circle Remote Two/3 using the official **Fire TV REST API** - ultra-fast control with **no ADB required!**

Perfect companion to the [ADB Fire TV integration](https://github.com/unfoldedcircle/integration-androidtv) for lightning-fast navigation and app launching.

---

## 🌟 Why This Integration?

### Fast REST API vs Slow ADB

| Feature | This Integration (REST API) | ADB Integration |
|---------|----------------------------|-----------------|
| **Response Time** | ⚡ Instant (~50ms) | 🐌 Slow (~500-2000ms) |
| **Navigation** | ✅ Lightning fast | ⏳ Noticeable lag |
| **App Launch** | ✅ Instant | ⏳ 1-3 seconds |
| **Setup** | ✅ Simple PIN auth | ⚠️ ADB pairing required |
| **Media Player** | ❌ Not supported | ✅ Supported |
| **Power Control** | ❌ Not supported | ✅ Supported |

### 💡 Best Practice: Use Both!

Combine this integration with the ADB integration for the ultimate experience:

- **REST API (This)**: Fast navigation, instant app launching, responsive UI control
- **ADB Integration**: Media player entity, power control, playback state feedback

Together they provide the complete Fire TV experience with maximum performance!

---

## ✨ Features

- 🚀 **Ultra-Fast REST API Control** - Instant response (~50ms vs 500-2000ms with ADB)
- 🎮 **Complete Navigation** - D-Pad, Home, Back, Menu controls
- ▶️ **Media Controls** - Play/Pause, Fast Forward, Rewind
- 📱 **Instant App Launching** - Quick launch 30+ streaming apps
- 🎯 **Physical Button Mapping** - Control with UC Remote hardware buttons
- 📺 **Multi-Page UI** - Navigation, Streaming Apps, Music, Utilities
- 🔒 **Secure Authentication** - PIN-based token authentication

---

## ⚠️ Important Limitations

### What This Integration Does NOT Support

The Fire TV REST API has inherent limitations:

#### ❌ No Power Control
- **Cannot turn Fire TV on or off**
- REST API doesn't expose power commands
- **Solution**: Use IR blaster, HDMI-CEC, or [ADB integration](https://github.com/unfoldedcircle/integration-androidtv)

#### ❌ No Media Player Entity
- **Cannot create media player entity** - only remote entity
- REST API doesn't provide playback state or media info
- Cannot see what's playing or playback position
- **Solution**: Use [ADB integration](https://github.com/unfoldedcircle/integration-androidtv) for media player

#### ❌ No Volume Control
- Volume controlled by TV/AVR, not Fire TV
- **Solution**: Use TV integration or HDMI-CEC

#### ❌ No State Feedback
- Cannot query current state
- Remote entity is **command-only**
- Cannot detect current app
- This is a REST API limitation, not integration

### 💡 Recommended: Use Both Integrations

For the **best Fire TV experience**:

#### REST API Integration (This) - Speed
- ✅ Ultra-fast navigation
- ✅ Instant app launching  
- ✅ Responsive controls
- ✅ Physical button mapping

#### ADB Integration - Features
- ✅ Media Player entity
- ✅ Power on/off
- ✅ Playback state
- ✅ Current app detection

**Example Setup:**
```
1. Use ADB to power ON Fire TV
2. Use REST API to navigate & launch Netflix (instant!)
3. Use ADB media player for playback with state
4. Use REST API for D-Pad while watching (fast!)
5. Use ADB to power OFF Fire TV
```

This gives you **instant speed** with **full features**!

---

## 📋 Requirements

### Hardware
- Fire TV 4K Max Gen 2 or compatible with REST API
- Unfolded Circle Remote Two or Remote 3
- Same local network

### Software
- Fire TV with REST API enabled (default on 4K Max Gen 2)
- UC Remote firmware 1.7.0+

---

## 🚀 Installation

### Option 1: GitHub Release (Recommended)

1. Download latest `.tar.gz` from [Releases](https://github.com/mase1981/uc-intg-firetv/releases)
2. Open UC Remote configurator: `http://your-remote-ip/configurator`
3. **Integrations** → **Add Integration** → **Upload driver**
4. Select downloaded file
5. Follow setup wizard

### Option 2: Docker
```bash
docker run -d --name uc-intg-horizon --restart unless-stopped --network host -v $(pwd)/data:/data -e UC_CONFIG_HOME=/data -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e UC_DISABLE_MDNS_PUBLISH=false ghcr.io/mase1981/uc-intg-horizon:latest
```
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
python -m uc_intg_firetv.driver
```

---

## ⚙️ Setup

### Step 1: Find Fire TV IP

1. Fire TV: **Settings** → **Network** → Note IP address

### Step 2: Add Integration

1. UC Remote configurator → **Integrations** → **Add**
2. Select **Fire TV**
3. Enter Fire TV IP
4. Click **Next**

### Step 3: Enter PIN

1. **4-digit PIN appears on TV**
2. Enter PIN in UC Remote (within 60 seconds)
3. Click **Complete**

### Done! ✅

- Fire TV Remote entity appears
- Config saved permanently
- No re-authentication needed

---

## 🎮 Controls

### Navigation
- D-Pad (↑↓←→), Select, Home, Back, Menu

### Media  
- Play/Pause, Fast Forward, Rewind

### Apps (30+)
Netflix, Prime Video, YouTube, Disney+, Hulu, Max, Apple TV+, Spotify, Plex, and more

---

## 🎯 Activity Usage

All commands available as simple commands:

- `DPAD_UP`, `SELECT`, `HOME`, `BACK`
- `PLAY_PAUSE`, `FAST_FORWARD`, `REWIND`
- `LAUNCH_NETFLIX`, `LAUNCH_YOUTUBE`, etc.

**Example Activity:**
```yaml
1. LAUNCH_NETFLIX
2. Wait 2 seconds
3. DPAD_DOWN
4. SELECT
```

---

## 🐛 Troubleshooting

### Fire TV Not Found
- Verify IP address
- Check same network
- Fire TV powered on
- Test ping
- Check AP isolation

### No PIN Displayed
- Wake Fire TV
- Check TV input
- Wait 10 seconds
- Restart setup
- Check Fire TV model compatibility

### Commands Not Working
- Fire TV powered on
- Check network
- Try HOME button
- View logs
- Restart integration

### Entity Shows OFF/Unknown
- Check logs
- Restart UC Remote
- Reconfigure if needed

---

## 🔬 Testing with Simulator

```bash
# Terminal 1
cd tools
python firetv_simulator.py

# Terminal 2
python -m uc_intg_firetv.driver

# Setup: IP: 127.0.0.1, PIN: 1234
```

---

## 📊 Technical Details

- **Protocol**: REST API / HTTPS:8080
- **Auth**: PIN-based token (persistent)
- **Entity**: Remote only (command-only)
- **Speed**: ~50ms response time

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/v1/FireTV/pin/display` | Request PIN |
| `/v1/FireTV/pin/verify` | Verify & get token |
| `/v1/FireTV?action=` | Navigation |
| `/v1/media?action=` | Media control |
| `/v1/FireTV/app/{pkg}` | Launch app |

---

## 🛠️ Development

### Add Apps

Edit `uc_intg_firetv/apps.py`:

```python
FIRE_TV_APPS = {
    'your_app': {
        'name': 'Your App',
        'package': 'com.example.app',
        'category': 'streaming',
    },
}
```

### Build Release

```bash
git tag v0.2.0
git push origin v0.2.0
# GitHub Actions builds automatically
```

---

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Test with simulator
4. Submit PR

[Report Bug](https://github.com/mase1981/uc-intg-firetv/issues) · [Request Feature](https://github.com/mase1981/uc-intg-firetv/issues)

---

## 💰 Support

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/mase1981)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/meiremiyara)

Your support helps maintain this integration. Thank you! ❤️

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

## 🙏 Credits

- **Developer**: [Meir Miyara](https://github.com/mase1981)
- **Framework**: [Unfolded Circle ucapi](https://github.com/unfoldedcircle/integration-python-library)

---

## 📞 Support & Links

- 🐛 [GitHub Issues](https://github.com/mase1981/uc-intg-firetv/issues)
- 💬 [Discussions](https://github.com/mase1981/uc-intg-firetv/discussions)
- 👥 [UC Forum](https://unfolded.community/)

### Related
- [ADB Integration](https://github.com/unfoldedcircle/integration-androidtv) - Companion for media player
- [WiiM Integration](https://github.com/mase1981/uc-intg-wiim)
- [UC Developer Docs](https://github.com/unfoldedcircle/core-api)

---

## ⚠️ Disclaimer

Unofficial integration. Not affiliated with Amazon or Unfolded Circle.

- Fire TV is a trademark of Amazon.com, Inc.
- Unfolded Circle and Remote Two/3 are trademarks of Unfolded Circle ApS
- Use at your own risk
- No warranty provided

---

<div align="center">

Made with ❤️ by [Meir Miyara](https://www.linkedin.com/in/meirmiyara/)

⭐ Star this repo if you find it useful!

[Report Bug](https://github.com/mase1981/uc-intg-firetv/issues) · [Request Feature](https://github.com/mase1981/uc-intg-firetv/issues) · [Discussions](https://github.com/mase1981/uc-intg-firetv/discussions)

</div>