# Stock robot Wi-Fi connection

Verified on Brodex, 2026-10-16. This is an agent-operated runbook. Read root
`AGENTS.md`, current hardware/firmware records and host `~/.config/NETWORK.md`
before changing a network. Do not make the operator repeat initial discovery.

## Verified outcome

The existing ESP-01 / ESP8266EX SoftAP was visible at full indicated signal on
channel 1 while the operator reported motor power OFF and USB reconnected.
Brodex joined it with Wi-Fi and sent only the stock echo frame over TCP port
65535: `80 00 81` returned exactly `80 01 81`. The socket was explicitly bound
to the robot-facing Wi-Fi address, not the Ethernet uplink, then closed.

This establishes actual wireless transport. USB was not used for the handshake
and no USB serial port was opened. In this test USB remained available to power
the controller/WLAN while motor power was off. Do not insist that USB is the
runtime command transport: the intended and now verified path is Wi-Fi.

No motion, calibration, install-state or power-switch command was sent, and no
firmware, EEPROM or fuse write occurred. The reported rear-right-leg fault remains unresolved. Stock
WPA2 association is not a new authenticated semantic gateway or local watchdog.

## Preserve remote access first

Brodex has one Wi-Fi radio. Its supported combination is at most one ordinary
managed client, with one concurrent radio channel. The original Internet Wi-Fi
and robot AP were on different channels. Joining the robot without another
uplink would interrupt Internet/Tailscale. Do not try that silently.

The operator plugged in Ethernet. **Before changing Wi-Fi**, the agent verified:

1. `enp3s0` connected using its existing `netplan-enp3s0` profile.
2. Two HTTPS requests explicitly bound with `curl --interface enp3s0 --noproxy '*'`
   returned HTTP 200 from independent public sites.
3. The preferred default route used Ethernet, metric 100.
4. Tailscale still reached the operator's MacBook. Existing SSH and Mosh sessions
   were bound to Tailscale addresses, not the removed Wi-Fi LAN address.

The Wi-Fi change used NetworkManager 1.46.0's documented checkpoint command:

```sh
sudo -n nmcli device checkpoint --timeout 120 -- \
  nmcli --wait 25 connection up id furbomek-bench-wifi ifname wlp2s0
```

This ran in an owned tmux session. **Only after** the wireless echo, Ethernet
HTTPS, Ethernet default route and Tailscale peer ping passed again did the agent
enter the requested `Yes` confirmation. A missing confirmation would have caused
automatic rollback. No checkpoint is left awaiting confirmation.

## Profile and connection state

`furbomek-bench-wifi` was created with `nmcli connection add save no`, using the
factory AP parameters from the official vendor reference. Preserve credentials
privately; do not put them, a private SSID, BSSID or connection UUID in this repo.
The runtime profile has:

```text
connection.autoconnect     no
ipv4.method                auto
ipv4.never-default         yes
ipv4.ignore-auto-dns       yes
ipv4.route-metric          700
ipv6.method                disabled
```

It is a volatile keyfile under `/run/NetworkManager/system-connections/`, not a
saved `/etc` profile or a reboot-persistent deployment. Do not commit that
keyfile. The original Internet Wi-Fi profile and Ethernet/netplan settings were
not edited. No firewall, Tailscale, SSH, Mosh, RustDesk, forwarding or NAT settings
were changed. The host's private network reference has the current addresses.

**Keep Ethernet connected while Wi-Fi serves the robot.** For a wireless-only
Internet uplink and simultaneous robot control, use a second Wi-Fi adapter or a
separately reviewed robot station-mode design; a virtual second ordinary Wi-Fi
client is not supported by this adapter's advertised combination.

## Recheck and rollback

Agents can inspect state without revealing the PSK:

```sh
nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
ip route
nmcli -f connection.id,connection.autoconnect,ipv4.never-default,ipv4.ignore-auto-dns,ipv6.method \
  connection show furbomek-bench-wifi
```

Use the private host network reference and pinned vendor client for the robot
address; do not mistake a successful TCP connect for an echo handshake. Send only
the allowlisted echo until a movement test is separately qualified.

To undo this change while retaining Ethernet, activate the pre-existing Internet
Wi-Fi profile on `wlp2s0`, verify the restored path, and then remove only the
runtime `furbomek-bench-wifi` profile. Select the existing profile from local
NetworkManager state, not a guessed SSID or UUID. Do not disconnect Ethernet
before restoring another verified Internet path. No robot firmware rollback is
needed: no device memory was changed.

## Supported-bench follow-up: do not repeat the wrong gate

The operator subsequently confirmed motor power OFF and all legs suspended. A
fresh C930e frame now shows the chassis on a rigid central black block, replacing
the earlier broad padded-case arrangement. Private frame/hash are recorded in
`hardware.json`. The stock wireless echo passed again and Ethernet remained the
Internet default route. Treat the repeated support-preparation step as completed
for this arrangement; do not ask for it again without evidence of a changed setup.

No powered movement check was performed. The remaining limitation is the control
implementation, not the wireless connection or the operator's compliance:
stock code has a relative leg request but no qualified local TTL/preemptive STOP;
the new project diagnostic is unflashed and has no actuator adapter. Do not imply
that another power cycle, camera angle or platform change installs that missing
software. Do not conclude that the working controller or all its gait code must
be replaced. Any targeted controller change or independent local gateway needs
its own acceptance; no whole-firmware replacement is authorized by an echo or by
bench preparation. Do not flash the actuator-disabled diagnostic as if it enabled
safe movement.

The [native Hermes MCP adapter](hermes-robot.md) is now registered and has been
invoked by an actual Hermes session for stock echo and supply reads. Motion
requests remain explicitly rejected; integration is real but a movement test has
not been performed. Existing hardware, firmware and remotes remain preserved.
