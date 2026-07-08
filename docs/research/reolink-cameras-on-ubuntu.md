# Research: Viewing 4 Reolink WiFi cameras (with Reolink Home Hub) on Ubuntu Linux — all 4 on one screen

> Produced 2026-07-08 by a three-track research workflow (multi-source web research + adversarial fact-check). Refuted claims are flagged below — treat them as corrections.

## Recommendation

Pull all four streams over RTSP from the Reolink Home Hub itself (not the individual cameras) and view them as a 2x2 grid in the browser via go2rtc. This is the best fit because (a) Reolink officially documents that every Home Hub model (Home Hub, Home Hub Pro, Home Hub Mini) provides CGI/RTSP/ONVIF access for ALL connected cameras — even battery/WiFi models that have no RTSP of their own — at rtsp://user:pass@HUB_IP:554/Preview_NN_main (NN = channel 01..04); (b) cameras joined to the hub's own hidden WiFi have no IP on your LAN, so the hub proxy is the only path anyway; (c) go2rtc is a single static binary that installs to ~/.local/bin with no sudo, runs as a user service, and its built-in page http://localhost:1984/stream.html?src=cam1&src=cam2&src=cam3&src=cam4 shows all four cameras in one browser window with low-latency WebRTC — something plain VLC cannot do without juggling 4 windows or the arcane mosaic module. VLC absolutely does work for a single camera (the user is right, and Reolink documents it officially) and is the perfect 30-second connectivity test before setting up the grid. If the user later wants 24/7 recording and motion/AI detection, Frigate (Docker, one-time sudo) is the upgrade path and uses the exact same hub URLs.

## Options considered

### VLC or ffplay pointed at the Home Hub RTSP (quick test / single camera)

**How:** Enable RTSP+ONVIF+HTTP ports in the Reolink app on the HUB device (Hub settings > Advanced Network Settings > Server Settings — per Reolink, ports for hub-connected cameras are opened on the hub, not on each camera). Then: vlc "rtsp://admin:PASSWORD@HUB_IP:554/Preview_01_main" (channels Preview_01..04, _main = full res, _sub = low res). ffplay equivalent: ffplay -rtsp_transport tcp "rtsp://admin:PASSWORD@HUB_IP:554/Preview_01_sub". For 4-at-once you must open 4 VLC/ffplay windows and tile them manually on GNOME.

**Pros:** Officially documented by Reolink; zero configuration; confirms the user's 'you can do it with VLC' hunch; VLC/ffmpeg are in Ubuntu repos.

**Cons:** No native grid — 4 separate windows to arrange by hand; VLC mosaic module is painful; battery cameras drop the RTSP session after 5 minutes and need a re-request; VLC needs TCP timeout raised to ~20 s for sleeping battery cams; passwords with special characters break the URL.

### go2rtc browser grid (RECOMMENDED)

**How:** Single static Go binary from github.com/AlexxIT/go2rtc releases into ~/.local/bin (no sudo). YAML config lists 4 streams pointing at the hub: cam1: rtsp://admin:PASS@HUB_IP:554/Preview_01_sub ... cam4: .../Preview_04_sub. Open http://localhost:1984/stream.html?src=cam1&src=cam2&src=cam3&src=cam4&mode=webrtc — all four render in one page (multi-src grid is a documented go2rtc feature, GitHub issue #129). Autostart with a systemd --user unit.

**Pros:** One window, real 2x2 grid, F11 fullscreen kiosk; WebRTC = sub-second latency; no sudo at any step; can also re-serve streams to other devices; same tool Frigate uses internally, so it is a stepping stone to a full NVR.

**Cons:** One extra binary + a 10-line YAML to maintain; browser tab must stay open (no recording, no motion detection); main-stream H.265 4K may need MSE mode instead of WebRTC in some browsers — sub streams avoid this.

### Home Hub local web UI in Firefox/Chromium (zero install)

**How:** Enable HTTP/HTTPS ports on the hub in the Reolink app, then browse to https://HUB_IP and log in with the hub admin account. Reolink's support docs ('How to Access Reolink Cameras/NVRs/Home Hub Locally via Web Browsers') show the hub web client with a multi-channel live-view grid, like the NVR web UI.

**Pros:** Literally nothing to install on Ubuntu; official Reolink UI with PTZ/talk/playback controls; works on Wayland trivially since it is just a browser page.

**Cons:** Web client is the least polished Reolink surface (their own Troubleshooting-Web-Client article exists for a reason); LAN-local only; historically feature-limited vs the Windows/macOS Client, which Reolink confirms does not run on Linux at all.

### Frigate NVR in Docker (full NVR: 24/7 recording + AI detection)

**How:** One-time sudo to install Docker (user runs printed commands), then Frigate container with go2rtc restream inside. Community-proven Home Hub config: use the hub's FLV stream ffmpeg:http://HUB_IP/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=PASS (FLV channels are 0-based; RTSP Preview_NN channels are 1-based — a documented gotcha), or plain rtsp://...:554/Preview_NN_main wrapped in ffmpeg:. View all cameras on Frigate's dashboard/Birdseye page in the browser.

**Pros:** Recording, motion/object detection, event review, and a proper multi-camera dashboard; HTTP-FLV input sidesteps historical hub RTSP instability; huge Reolink user base in Frigate community.

**Cons:** Heaviest option: Docker + config + storage; needs sudo once; hub HTTP (unencrypted) must be enabled for FLV; overkill if the goal is only live viewing.

### Neolink RTSP bridge (only needed WITHOUT a hub)

**How:** github.com/QuantumEntangledAndy/neolink (maintained fork of thirtythreeforty/neolink) speaks Reolink's proprietary Baichuan protocol (TCP/UDP port 9000) and re-serves it as standard RTSP — for cameras that have no native RTSP standalone (B800, E1, older Lumus hw IPC_325C7, battery Argus/Altas models).

**Pros:** Unlocks RTSP on battery/entry models with no extra hardware; works with VLC/Frigate/ZoneMinder downstream.

**Cons:** Unnecessary here — the user's Home Hub already does this job in supported firmware; keeps battery cameras awake (heavy battery drain, GitHub issue #204); community reverse-engineering, so firmware updates can break it. ZoneMinder/Shinobi are alternative Linux NVRs but, like Frigate, they still just consume the same hub RTSP URLs and offer no Reolink-specific advantage.

### Reolink Cloud (NOT a live-view solution)

**How:** Subscription cloud storage: motion-triggered clips upload to cloud.reolink.com; you can log in from any browser (including on Ubuntu) to play back and download recordings.

**Pros:** OS-independent browser playback of recorded events; off-site backup if cameras are stolen.

**Cons:** Does not provide live view of the cameras in the browser — playback of motion recordings only; subscription cost; camera/region eligibility limits; irrelevant to the 'see all 4 live on one screen' goal.

## Setup steps (recommended method)

1. Update the Home Hub firmware first (Reolink app > hub > Settings > Firmware, or reolink.com Download Center). A Sept 2025 Home Hub Pro firmware (v3.3.0.369_25090486) fixed a confirmed bug where hub-proxied RTSP sub-streams were laggy/unusable — older firmware will make any RTSP method look broken.

2. In the Reolink app, open the HUB device's settings (not the cameras') > Advanced Network Settings > Server Settings, and enable the RTSP, ONVIF, HTTP and HTTPS ports. Reolink docs are explicit: for cameras added to a Home Hub, ports are opened on the hub, and the hub then serves RTSP for every attached camera. Note the hub's LAN IP from the app's network info page (or your router's DHCP table); give it a DHCP reservation.

3. Map cameras to channel numbers from the Ubuntu box: curl "http://HUB_IP/api.cgi?cmd=GetChannelstatus&user=admin&password=YOURPASS" — the JSON lists each camera name with a 0-based channel; ADD 1 to get the RTSP channel (channel 0 -> Preview_01, channel 3 -> Preview_04). Use the hub's admin credentials; avoid special characters in the password (Reolink's own warning) or create a dedicated user account for streaming.

4. Quick sanity test with VLC (this is the 'VLC method' confirmed by Reolink's official guide): user runs 'sudo apt install vlc ffmpeg' (printed for manual run — no sudo in automation), then: vlc "rtsp://admin:YOURPASS@HUB_IP:554/Preview_01_main". If any of the 4 are battery cameras, first raise VLC's Tools > Preferences > All > Input/Codecs > TCP connection timeout to 20000 ms, and expect each session to drop after 5 minutes (hub-enforced for battery models).

5. Install go2rtc without sudo: mkdir -p ~/.local/bin && curl -L -o ~/.local/bin/go2rtc https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_amd64 && chmod +x ~/.local/bin/go2rtc (pick go2rtc_linux_arm64 on ARM).

6. Create ~/.config/go2rtc/go2rtc.yaml with the four hub channels (use _sub streams for a smooth grid; switch any tile to _main when you need full resolution):
streams:
  cam1: rtsp://admin:YOURPASS@HUB_IP:554/Preview_01_sub
  cam2: rtsp://admin:YOURPASS@HUB_IP:554/Preview_02_sub
  cam3: rtsp://admin:YOURPASS@HUB_IP:554/Preview_03_sub
  cam4: rtsp://admin:YOURPASS@HUB_IP:554/Preview_04_sub

7. Run it: ~/.local/bin/go2rtc -config ~/.config/go2rtc/go2rtc.yaml, then open in Firefox/Chromium: http://localhost:1984/stream.html?src=cam1&src=cam2&src=cam3&src=cam4&mode=webrtc — all four cameras appear on one page; press F11 for a fullscreen wall. (If a main-stream tile stays black, it is likely H.265: change mode=webrtc to mode=mse, or keep sub streams.) The go2rtc dashboard at http://localhost:1984/ lets you multi-select streams and generates this URL for you.

8. Autostart on login (still no sudo) with a systemd user unit at ~/.config/systemd/user/go2rtc.service:
[Unit]
Description=go2rtc camera bridge
After=network-online.target
[Service]
ExecStart=%h/.local/bin/go2rtc -config %h/.config/go2rtc/go2rtc.yaml
Restart=always
[Install]
WantedBy=default.target
Then: systemctl --user daemon-reload && systemctl --user enable --now go2rtc. Optionally add the stream.html URL as a pinned browser tab or a GNOME web-app shortcut.


## Caveats

- Whether the 4 cameras keep their own direct RTSP depends on HOW they joined the hub: cameras connected to the hub's own hidden WiFi get no IP on your LAN, so ONLY the hub URLs work; cameras kept on the house WiFi but 'added' to the hub remain directly reachable at their own IPs too (community-confirmed). Either way the hub URLs always work, which is why the recommendation targets the hub.
- If the cameras are battery models (Argus/Altas/battery doorbell): they never have standalone RTSP, and even via the hub each RTSP session is capped at 5 minutes before the camera sleeps (official Reolink limit) — a permanent 4-up live wall will constantly reconnect and will chew battery. For continuous viewing you really want mains-powered/plug-in WiFi models; for battery cams treat the grid as on-demand, or rely on the hub's recordings.
- 4G LTE Reolink cameras (Go series, TrackMix LTE, Duo 2 LTE) support no CGI/RTSP/ONVIF at all — not even via the hub (official compatibility matrix). Non-issue for WiFi cams, but worth knowing.
- Hub RTSP had real bugs before late-2025 firmware (laggy/failing Fluent streams, HA issue #147399, fixed by v3.3.0.369_25090486 on Hub Pro). If RTSP misbehaves after updating, the hub's HTTP-FLV streams (http://HUB_IP/flv?port=1935&app=bcs&stream=channel0_sub.bcs&user=...&password=...) are the proven workaround — note FLV channels are 0-based while RTSP Preview_NN is 1-based.
- Security: RTSP/FLV URLs embed credentials in plain text and hub HTTP is unencrypted — keep everything LAN-only, never port-forward 554/80/1935 to the internet, and use a dedicated low-privilege user account for streaming if the firmware supports it.
- Reolink's password guidance: avoid special characters in the account used in RTSP URLs (they break URL parsing); percent-encoding sometimes works but plain alphanumerics are safest.
- Model verified pieces I could not test against the user's actual hardware: their exact camera models, hub model (Hub vs Pro vs Mini) and firmware level — channel numbers and battery-cam limits should be confirmed with the GetChannelstatus curl in step 3.


## Fact-check verdicts on this track's load-bearing claims

- **CONFIRMED** — go2rtc's stream.html accepts multiple src parameters (e.g. stream.html?src=cam1&src=cam2&src=cam3&src=cam4) and renders all streams on one page — confirmed in AlexxIT/go2rtc issue #129 discussing the multi-stream page feature, and go2rtc ships as a single static Linux binary requiring no root.
  - Evidence: Verified against primary sources on 2026-07-07. (1) Multi-src support confirmed in the CURRENT master source of www/stream.html (https://github.com/AlexxIT/go2rtc/blob/master/www/stream.html, checked at commit dc1685e): the script runs `const streams = params.getAll('src')`, creates one <video-stream> element per src, and applies a flex-wrap grid ('flex' class) when streams.length > 1 — so stream.html?src=cam1&src=cam2&src=cam3&src=cam4 renders all four on one page; per-stream mode is set via repeated `mode` params (params.getAll('mode')). (2) Issue #129 exists and matches: https://github.com/AlexxIT/go2rtc/issues/129, titled 'New Multiple Stream on Page Option: Questions' (Dec 2022, closed by AlexxIT), explicitly shows URLs like http://192.168.100.60:1984/stream.html?src=deck&src=garage&mode=webrtc,mse,mp4,mjpeg. Minor nuance: it is a user Q&A about the then-new feature, not the feature announcement, and in that 2022 version the working selector param was 'stream=' rather than 'mode=' — current code uses 'mode='. (3) Single-binary/no-root confirmed: latest release v1.9.14 (2026-01-19, https://github.com/AlexxIT/go2rtc/releases/tag/v1.9.14) ships raw un-zipped Linux binaries (go2rtc_linux_amd64 ~5.7 MB, plus arm/arm64/armv6/i386/mipsel) — a statically compiled Go binary; its default listeners (API :1984, RTSP :8554, WebRTC :8555) are all unprivileged ports, so it runs as a normal user with no root/sudo. One caveat irrelevant to video playback: since v1.9.14 the config-editor UI loads some JS libs from cdn.jsdelivr.net, but stream.html itself only references the local ./video-stream.js (plus cosmetic go2rtc.org icons), so multi-camera viewing works LAN-only.
- **CONFIRMED** — Battery-powered Reolink WiFi cameras (Argus, Altas, battery doorbell) have no standalone RTSP/ONVIF and must go through a Home Hub or NVR; via hub/NVR their RTSP preview sessions last max 5 minutes before the camera sleeps, and Reolink recommends a ≥20 s RTSP/TCP timeout — same official article 900000630706.
  - Evidence: Official Reolink support article 900000630706 "Introduction to RTSP" (https://support.reolink.com/articles/900000630706-Introduction-to-RTSP/, fetched live 2026-07-08) contains both cited facts verbatim in its "Notes of Battery-powered WiFi cameras": (1) "On Reolink NVR and Reolink Home Hub, each preview session of battery-powered WiFi cameras can only last up to 5 minutes. After 5 minutes, the battery-powered WiFi cameras enter sleep mode and the RTSP connection is disconnected"; (2) "It is recommended to set the RTSP request timeout to at least 20s" (VLC TCP connection timeout 20000 ms example). The no-standalone-RTSP/ONVIF part is confirmed by the current companion article "Which Reolink Products Support CGI/RTSP/ONVIF" (https://support.reolink.com/articles/900000617826-Which-Reolink-Products-Support-CGI-RTSP-ONVIF/), which marks Argus series, Altas series (incl. Altas PT Ultra), and Doorbell Battery D340B as not supporting CGI/RTSP/ONVIF on their own — access only through a connected Home Hub/NVR — and by https://support.reolink.com/articles/360004441753-Can-Reolink-Battery-Powered-Cameras-Work-with-3rd-Party-Software/ ("standalone... does not support RTSP, RTMP, ONVIF" due to hardware limitations). Adversarial searches (Reddit r/reolinkcam, Reolink community forum, Home Assistant community thread "Support for Reolink Battery Devices as of 2026.6" https://community.home-assistant.io/t/support-for-reolink-battery-devices-as-of-2026-6/1012766) found no firmware or 2025-2026 change granting standalone RTSP to battery models; the only hub-less path is the unofficial Neolink bridge. One nuance: the compatibility table's condition for battery WiFi cameras says "Must connect to Reolink Home Hub" (NVR listed as the condition for NVR-kit cameras), but article 900000630706 itself applies the 5-minute rule to battery cameras "On Reolink NVR and Reolink Home Hub", so the claim's "Hub or NVR" phrasing matches the cited source.
- **CONFIRMED** — Reolink officially documents that all Home Hub models (Home Hub, Home Hub Pro, Home Hub Mini, HH1/HH2/HH3) provide CGI/RTSP/ONVIF access for their connected cameras at the hub's IP, format rtsp://user:pass@HUB_IP:554/Preview_<NN>_main|sub with hub credentials, where NN = (GetChannelstatus channel + 1) — checkable at support.reolink.com articles 900000630706 and 900000617826.
  - Evidence: Verified directly on both cited official pages (live as of 2026-07-07). (1) https://support.reolink.com/articles/900000617826-Which-Reolink-Products-Support-CGI-RTSP-ONVIF/ contains the table row "All Home Hubs | e.g., Home Hub Pro, Home Hub, Home Hub Mini, HH1/HH2/HH3... | provides CGI/RTSP/ONVIF access for connected cameras" (blue-dot markers for all three protocols). (2) https://support.reolink.com/articles/900000630706-Introduction-to-RTSP/ documents the URL format rtsp://<username>:<password>@<IP address>/Preview_<channel number>_<stream type> (default port 554), states for Home Hubs "The username and password in the URL should be the ones for Home Hub", and explicitly documents the CGI command GetChannelstatus (http://HUB_IP/api.cgi?cmd=GetChannelstatus&user=...&password=...) with the rule that returned channel values start at 0 while RTSP URL channels start at 1, so "the returned channel needs to be added by 1" — example: doorbell at channel 2 maps to Preview_03_main. Adversarial cross-checks found no contradicting evidence: Home Assistant's Reolink integration (https://www.home-assistant.io/integrations/reolink/) lists Home Hub, Home Hub Mini, and Home Hub Pro as tested with battery cameras, and Reolink's own retail listings confirm battery cameras gain RTSP/ONVIF/CGI only via a Home Hub/Mini. Caveats (do not refute the documentation claim): battery-camera RTSP sessions through the hub are limited to ~5 minutes before the camera sleeps and need re-requesting, Reolink recommends a >=20 s RTSP timeout for wake-up, and Reddit reports (e.g. reddit.com/r/reolinkcam/comments/1dysazm, 1sjq4mt) note stream stability/frame-ordering issues on some hub firmware — so keep hub firmware current for 4 simultaneous streams.
- **CONFIRMED** — go2rtc's stream.html accepts multiple src parameters (e.g. stream.html?src=cam1&src=cam2&src=cam3&src=cam4) and renders all streams on one page — confirmed in AlexxIT/go2rtc issue #129 discussing the multi-stream page feature, and go2rtc ships as a single static Linux binary requiring no root.
  - Evidence: All three parts check out against primary sources, current as of master (commit dc1685e). (1) Official docs at https://github.com/AlexxIT/go2rtc/blob/master/www/README.md state: "www/stream.html - universal viewer with support params in URL: multiple streams on page src=camera1&src=camera2..." plus mode= technology autoselection and width= sizing — so 4 Reolink streams on one page via stream.html?src=cam1&src=cam2&src=cam3&src=cam4 is officially supported today. (2) Issue #129 is real and on-topic: https://github.com/AlexxIT/go2rtc/issues/129 titled "New Multiple Stream on Page Option: Questions" (opened 2022-12-07, closed as completed by AlexxIT), containing working example URLs like http://192.168.100.60:1984/stream.html?src=deck&src=garage&mode=webrtc,mse,mp4,mjpeg. Minor nuance: in that 2022 issue the user found stream= vs mode= parameter behavior confusing at the time; current docs standardize on mode=. (3) The main README (https://github.com/AlexxIT/go2rtc#go2rtc-binary) describes go2rtc as a "zero-dependency small app for all OS" with a per-arch static release binary go2rtc_linux_amd64 (https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_amd64) needing only chmod +x; its default ports 1984 (API/web), 8554 (RTSP), 8555 (WebRTC) are all unprivileged (>1024), so it runs as a normal user without root — compatible with the no-sudo automated setup constraint.


## Sources

- [Reolink Support — Introduction to RTSP (URL format, Home Hub channels, battery-cam 5-min limit, GetChannelstatus CGI)](https://support.reolink.com/articles/900000630706-Introduction-to-RTSP/)
- [Reolink Support — Which Reolink Products Support CGI/RTSP/ONVIF (full model matrix: battery cams need hub, E1/Lumus exceptions, 4G unsupported, hubs proxy all three protocols)](https://support.reolink.com/articles/900000617826-Which-Reolink-Products-Support-CGI-RTSP-ONVIF/)
- [Reolink Support — How to Live View Reolink Cameras via VLC Media Player (official VLC steps)](https://support.reolink.com/articles/360007010473-How-to-Live-View-Reolink-Cameras-via-VLC-Media-Player/)
- [Reolink Support — How to Configure Reolink Ports Settings (enable RTSP/ONVIF/HTTP on hub, not on hub-attached cameras)](https://support.reolink.com/articles/900000621783-How-to-Configure-Reolink-Ports-Settings/)
- [home-assistant/core issue #147399 — RTSP Stream Nearly Unusable with Reolink Home Hub (hub-WiFi cams have no LAN IP; FLV workaround; fixed in hub firmware v3.3.0.369_25090486, Sept 2025)](https://github.com/home-assistant/core/issues/147399)
- [AlexxIT/go2rtc — single-binary stream server (releases used for no-sudo install)](https://github.com/AlexxIT/go2rtc)
- [AlexxIT/go2rtc issue #129 — multiple streams on one stream.html page (grid view syntax)](https://github.com/AlexxIT/go2rtc/issues/129)
- [thirtythreeforty/neolink — RTSP bridge for non-RTSP Reolink cameras (Baichuan protocol); maintained fork: QuantumEntangledAndy/neolink](https://github.com/thirtythreeforty/neolink)
- [Reolink Community — Linux client support (no Linux client; browser access instead)](https://community.reolink.com/topic/737/linux-client-support)
- [Reolink Support — How to Access Reolink Cameras/NVRs/Home Hub Locally via Web Browsers (zero-install browser option)](https://support.reolink.com/articles/360003452893-How-to-Access-Reolink-Cameras-NVRs-Home-Hub-Locally-via-Web-Browsers/)
- [Reolink Support — How to Play Back and Download Reolink Cloud Recordings (cloud = recordings playback in browser, not live view)](https://support.reolink.com/articles/360015912514-How-to-Play-Back-and-Download-Reolink-Cloud-Recordings/)
- [Frigate Docs — Configuring go2rtc (restream pattern used for the Frigate option)](https://docs.frigate.video/guides/configuring_go2rtc/)
