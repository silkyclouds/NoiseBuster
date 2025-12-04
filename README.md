<div align="center">

# ⚠️ PROJECT DISCONTINUED ⚠️

<img width="256" height="256" alt="mute_logo" src="https://github.com/user-attachments/assets/8c2ab422-d2ff-4f68-b901-bddbd6840996" />

### NoiseBuster has been discontinued and replaced by **mute**

<p>
  <img src="https://img.shields.io/badge/Status-Discontinued-d95030?style=flat-square" alt="Discontinued">
  <img src="https://img.shields.io/badge/Replaced%20by-mute-5b9a9a?style=flat-square" alt="Replaced by mute">
</p>

<p>
  <a href="https://github.com/silkyclouds/mute"><img src="https://img.shields.io/badge/🚀_New_Project-mute-5b9a9a?style=for-the-badge" alt="mute"></a>
  <a href="https://dash.muteq.eu"><img src="https://img.shields.io/badge/📊_Dashboard-dash.muteq.eu-d95030?style=for-the-badge" alt="Dashboard"></a>
  <a href="https://discord.com/invite/m7RGZy6YmZ"><img src="https://img.shields.io/badge/💬_Discord-Join_Us-5865F2?style=for-the-badge" alt="Discord"></a>
</p>

</div>

---

## 📢 Important Notice

**NoiseBuster is no longer maintained.** The project was complex to configure and required significant technical knowledge from users. 

We've built something better — **[mute](https://github.com/silkyclouds/mute)** is the future of acoustic monitoring!

---

## 🔗 Quick Links

| | |
|---|---|
| 🚀 **New Project** | [github.com/silkyclouds/mute](https://github.com/silkyclouds/mute) — The successor to NoiseBuster |
| 📊 **Dashboard** | [dash.muteq.eu](https://dash.muteq.eu) — Live noise monitoring & analytics |
| 🌐 **Website** | [muteq.eu](https://muteq.eu) — Learn more about MUTEq |
| 💬 **Discord** | [Join our community](https://discord.com/invite/m7RGZy6YmZ) — Get help & share your builds |

---

## 🎯 Why the change?

NoiseBuster served its purpose, but it had limitations:

| NoiseBuster ❌ | mute ✅ |
|---|---|
| Complex configuration | Simple Docker setup |
| Manual device IDs & API keys | Automatic onboarding |
| Limited dashboard | Full-featured cloud dashboard |
| Difficult MQTT setup | MQTT auto-discovery |
| Technical knowledge required | User-friendly for everyone |

---

## ⚡ Meet mute

**mute** is a lightweight USB noise monitoring client that connects your DIY **Mute Box** to the official MUTEq dashboard. It's everything NoiseBuster wanted to be, but simpler and more powerful.

<p align="center">
  <img src="https://img.shields.io/badge/Open%20Source-✓-5b9a9a?style=flat-square" alt="Open Source">
  <img src="https://img.shields.io/badge/Privacy--first-✓-5b9a9a?style=flat-square" alt="Privacy-first">
  <img src="https://img.shields.io/badge/Home%20Assistant-ready-5b9a9a?style=flat-square" alt="Home Assistant ready">
  <img src="https://img.shields.io/badge/Docker-supported-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

### Key Features

- 📈 **Real-time noise level streaming** to the cloud dashboard
- 🌤️ **Weather data correlation** (temperature, humidity, conditions)
- 🏠 **Local Home Assistant integration** via MQTT
- 📊 **Advanced analytics**, alerts, and reporting
- 🔒 **Privacy-first** — Only dB levels, never audio recordings

---

## 🚀 Get Started with mute

The recommended way to run mute is via Docker. **No API keys, no tokens, no manual device IDs!**

```bash
docker run -d \
  --name mute-client \
  --restart=unless-stopped \
  --device /dev/bus/usb:/dev/bus/usb \
  -v /path/to/config:/config \
  meaning/mute:client-latest
```

Then check the logs for your onboarding URL:

```bash
docker logs mute-client
```

**That's it!** Complete the simple web-based onboarding and you're done.

👉 **[Full documentation on GitHub](https://github.com/silkyclouds/mute)**

---

## 🤝 Join the Community

We'd love to see you in our Discord community! Get help, share your builds, and connect with other acoustic monitoring enthusiasts.

<p align="center">
  <a href="https://discord.com/invite/m7RGZy6YmZ"><img src="https://img.shields.io/badge/💬_Join_Discord-5865F2?style=for-the-badge" alt="Join Discord"></a>
</p>

---

## 👤 Author

Developed with ❤️ by **Raphaël Vael**

---

## 📜 License

<a href="https://creativecommons.org/licenses/by-nc/4.0/"><img src="https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg" alt="CC BY-NC 4.0"></a>

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License** ([CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)).

> 💡 **Intellectual Property Notice:** The MUTEq concept is registered with the [Benelux Office for Intellectual Property (BOIP)](https://www.boip.int/).

---

<div align="center">

<img width="128" height="128" alt="mute_logo" src="https://github.com/user-attachments/assets/8c2ab422-d2ff-4f68-b901-bddbd6840996" />

**MUTEq** — Acoustic intelligence for everyone.

Open-source · Community-powered · Privacy-first

<p>
  <a href="https://github.com/silkyclouds/mute">GitHub</a> •
  <a href="https://dash.muteq.eu">Dashboard</a> •
  <a href="https://muteq.eu">Website</a> •
  <a href="https://discord.com/invite/m7RGZy6YmZ">Discord</a>
</p>

<sub>© 2024 Raphaël Vael · Licensed under CC BY-NC 4.0</sub>

</div>
