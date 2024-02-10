# offspot-config

A library to read/write an Offspot runtime config and a collection of scripts to use it within [offspot/base-image](https://github.com/offspot/base-image).

[![CodeFactor](https://www.codefactor.io/repository/github/offspot/offspot-config/badge)](https://www.codefactor.io/repository/github/offspot/offspot-config)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![codecov](https://codecov.io/gh/offspot/offspot-config/branch/main/graph/badge.svg)](https://codecov.io/gh/offspot/offspot-config)
[![PyPI version shields.io](https://img.shields.io/pypi/v/offspot-config.svg)](https://pypi.org/project/offspot-config/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/offspot-config.svg)](https://pypi.org/project/offspot-config)

## Scripts Usage

Launched via `offspot-runtime-config-fromfile`, it:

- reads a YAML config file and changes the offspot configuration accordingly.
- starts associated services

Its primary goal is to allow one to change some key offspot configuration upon next boot by changing one file (stored in FAT32 `/boot/firmware` –so writable anywhere), following a descriptive format.

**Notes**:

- It is **not a configuration reference**. It only lists the changes requested (whatever the status of those settings) at next boot. In an already configured system the file should be an empty YAML document (`---`).
- While `-fromfile` reads a YAML file, it mostly runs individual, feature-specific scripts that takes parameters on the command-line.
- it's a configuration tool that must be ran as root.


```sh
offspot-runtime-config-fromfile --debug /boot/firmware/offspot.yaml
```

- `--debug` will show you what exact parameters were passed to individual scripts so you can manually launch them should there be an issue.
- this script is meant to be run automaticaly on boot (via systemd) **before `docker-compose.service`**.
- It returns `0` on success, `1` on general failures and `2` on misconfiguration (invalid parameter). Same goes for individual scripts.
- it starts `hostapd`, `dnsmasq` and `iptables-restore` automatically. If you start it on boot, disable them (`systemctl disable hostapd dnsmasq`)

## Installation

**⚠️ Warning**: only tested on offspot base-image (raspiOS bookworm)

```sh
apt install hostapd dnsmasq dhcpcd5 python3-yaml python3-pip
systemctl unmask hostapd
systemctl disable hostapd dnsmasq
pip3 install offspot-config
```

## Library usage

```sh
pip3 install offspot-config
```

```py
from offspot_runtime.checks import is_valid_ipv4

# CheckResponse can be treated as a boolean
if is_valid_ipv4("10.0.0.1"):
   …

# CheckResponse exposes `.passed` (`bool`) and `.help_text` (`str`)
check = is_valid_ipv4("10.0.0.a")
if not check.passed:
    raise SystemExit(check.help_text)

# Directly raise a `ValueError` exception
is_valid_ipv4("10.0.0.a").raise_for_status()
```

---

## `offspot.yaml` format

`offspot.yaml` is composed of a single `object` with predefined candidate members.

- No member is required.
- Unknown members are simply ignored.
- No relation between first-level members.

### Valid first-level members

| Member       | Kind      | Function                                               |
|--------------|-----------|--------------------------------------------------------|
| `firmware`   | `string`  | Set WiFi firmware to use                               |
| `timezone`   | `string`  | Set Host timezone                                      |
| `hostname`   | `string`  | Set machine's hostname (not domain, see `ap`).         |
| `ethernet`   | `object`  | Set network configuration for ethernet interface       |
| `ap`         | `object`  | Set WiFi AP configuration for wireless interface       |
| `containers` | `object`  | Builds the docker-compose file                         |

### `firmware`

`firmware` is itself a single `object`.

| Member       | Kind      | Required | Function                                             |
|--------------|-----------|----------|------------------------------------------------------|
| `brcm43455`  | `string`  | no       | Firmware to use for `brcm43455` chipset (Pi 3B+/4/5) |
| `brcm43430`  | `string`  | no       | Firmware to use for `brcm43430 ` chipset (Pi 0W/3    |

Chipsets included in RaspiOS have limitations on the number of WiFi clients that can connect to it.
Using this, you can change the version of the firmware to use for your chipset.

Each chipset supports a different set of firmwares.

#### `brcm43455` chipset firmwares

| Firmware                            | Comment                                                                        |
|-------------------------------------|--------------------------------------------------------------------------------|
| `raspios`                           | Supports 4/5 clients. Came with RaspiOS                                        |
| `supports-19_2021-11-30`            | Supports 19 clients. Can be used in AP+STA mode (not supported in Hotspot yet) |
| `supports-24_2021-10-05_noap+sta`   | Supports 24 clients. Can **not** be used in `AP+STA` mode                      |
| `supports-32_2015-03-01_unreliable` | Supports 32 clients. **Unreliable**. Available for tests only                  |

#### `brcm43430` chipset firmwares

| Firmware                            | Comment                                                                        |
|-------------------------------------|--------------------------------------------------------------------------------|
| `raspios`                           | Supports 4/5 clients. Came with RaspiOS                                        |
| `supports-30_2018-09-28`            | Supports 30 clients.                                                           |

**⚠️ Warning**: WiFi firmware update **requires a reboot** to be effective.

Example:

```yaml
---
firmware:
  brcm43455: raspios
  brcm43430: supports-30_2018-09-28
```

### `timezone`

Must be a valid timezone. Get a complete list with:

```sh
timedatectl list-timezones
```

**⚠️ Warning**: timezones are **case-sentitive**. `Africa/Bamako` works but `Africa/bamako` or `utc` doesn't.

Example:

```yaml
---
timezone: Europe/Berlin
```


### `hostname`

Must be alphanumeric string up to 63 characters. Can be composed of multiple (max 64) of those, separated by a single dot. Total length must be under 256 characters.

Example:

```yaml
---
hostname: library-lab-pi23
```

**Note**: this is not the domain name on the network. See `ap` for this. `hostname` is mostly useless.

### `ethernet`

`network` is itself a single `object`.

| Member       | Kind      | Required | Function   |
|--------------|-----------|----------|------------|
| `type    `   | `string`  | **yes**  | Either `dhcp` or `static`                   |
| `address`    | `string`  | **`static`** | Static IPv4 adress to set                |
| `routers`    | `string`  | **`static`** | Space-separated IPv4 addresses to use as gateways. Use any different address inside subnet if not using it. |
| `dns`        | `string`  | **`static`** | Space-separated IPv4 addresses to use as domain name servers. Use any different address inside subnet if not using it. |

Examples:

```yaml
---
ethernet:
  type: dhcp
```

```yaml
---
ethernet:
  type: static
  address: 192.168.5.1
  routers: 192.168.5.200
  dns: 192.168.5.200
```

#### Notes

If you need to mix this simple configuration tool with a more complex `dhcpcd.conf` file, use the following *armor* in your file:

```git
### config-network: start ###
### config-network: end ###
```

The script will set its properties in-between those lines, keeping the rest of your configuration.

Without an *armor*, configuration is appended at end of file, specifying `eth0` interface if missing (untouched `dhcpcd.conf`)

### `ap`

`ap` is itself an `object`.

| Member              | Kind       | Required | Function                                                                                                         |
|---------------------|----------- |----------|------------------------------------------------------------------------------------------------------------------|
| `ssid    `          | `string`   | **yes**  | SSID (Network Name)                                                                                              |
| `passphrase`        | `string`   | no       | Passphrase/password to connect to the network. Defaults to Open Network                                          |
| `address`           | `string`   | no       | IP address to set on the wireless interface. Defaults to 192.168.2.1                                             |
| `channel`           | `integer`  | no       | WiFi channel to use for the network (1-14). Defaults to `11`.                                                    |
| `country`           | `string`   | no       | Country-code to apply frequencies limitations for. Defaults to `FR`                                              |
| `hide`              | `boolean`  | no       | Hide SSID (Clients must know and enter its name to connect)                                                      |
| `interface`         | `string`   | no       | Interface to configure AP for. Defaults to `wlan0`                                                               |
| `dhcp-range`        | `string`   | no       | IP range for AP clients. `start,end,subnet,ttl` format. Default: `.100-.240` from address                        |
| `network`           | `[string]` | no       | Network to advertise DHCP on. Defaults to `.0/24` from address                                                   |
| `nodhcp-interfaces` | `[string]` | no       | Interfaces where the DHCP server will not run                                                                    |
| `dns`               | `[string]` | no       | DNS to set via DHCP when working as Internet gateway. Defaults to `8.8.8.8`, `1.1.1.1`                           |
| `captured-address`  | `string`   | no       | IP address to set DNS fallback to when offline (all domains but locals are sent to it). Default:  `198.51.100.1` |
| `as-gateway`        | `boolean`  | no       | Make this device act as a gateway to Internet (wired) for AP (wireless) clients (when/if `eth0` has connectivity)|
| `tld`               | `string`   | no       | Search (top-level) *domain* to set via DHCP. Defaults to `offspot`                                               |
| `domain`            | `string`   | no       | Domain name to direct to the offspot. Defaults to `generic` (resolved as `generic.{tld}`                         |
| `welcome`           | `string`   | no       | Additional domain to direct to offspot. Defaults to `goto.kiwix` (resolved as `goto.generic.{tld}`               |
| `spoof`             | `boolean`* | no       | Whether to direct all DNS requests to the offspot. Useful for captive-portal without Internet bridge^1.          |

- ^1: Special value `auto` triggers it when the hotspot is offline and disables it when it is connected to Internet

#### notes

- `iptables` is not persistent. `ap` will write rules to `/etc/iptables/*.rules`. If you don't use `offspot-runtime-config-fromfile` on start, manually reload them via a script or service:

```sh
/usr/bin/find /etc/iptables/ -name '*.rules' -exec /sbin/iptables-restore {} \;
```

### `containers`

`containers` is the full docker-compose.yaml you want to use. It will be written to `/etc/docker/compose.yml`.

```yaml
---
containers:
  services:
    kiwix:
      container_name: kiwix
      image: ghcr.io/offspot/kiwix-serve:dev
      command: /bin/sh -c "kiwix-serve /data/*.zim"
      volumes:
        - "/data/zims:/data:ro"
      expose:
        - "80"
      restart: always
```
