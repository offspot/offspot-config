# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2024-01-30

### Added

- `Package.size` informing overall package size (image and download_size)

## [1.7.5] - 2024-01-29

### Fixed

- [builder] Fix metrics environment to find logs

## [1.7.4] - 2024-01-26

### Fixed

- [builder] Use same image version for file-manager and zim-manager (workaround image-creator#28)

## [1.7.3] - 2024-01-26

### Fixed

- [builder] Fix typo in metrics image URL

## [1.7.2] - 2024-01-26

### Changed

- [builder] Using metrics 0.2.1

## [1.7.1] - 2024-01-15

### Changed

- [catalog] Using file-manager 1.1

## [1.7.0] - 2024-01-15

### Added

- [catalog] App `file-manager.offspot.kiwix.org` to replace Edupi
- [catalog] FilesApp TrailSense
- [catalog] FilesApp Survival Manual
- [catalog] FilesApp The Life
- [builder] `add_file()`'s `to` can now use `${APP_DIR:<ident>}` to target any app's home
- [builder] Use reverse-proxy 1.5 with single-service fix

### Removed

- [catalog] Removed `edupi.offspot.kiwix.org` package. See `file-manager.offspot.kiwix.org`

## [1.6.0] - 2024-01-08

### Changed

- [builder] Setting default `hostname` on runtime-config using `domain`
- [builder] Fixed missing dashboard entries for catalog apps
- [builder] Updated Captive Portal to 1.3, hwclock to 1.2, dashboard to 1.3
- [builder] Shared handling of touched files
- [builder] Fixed ZIM auto-discovery: folder not mounted
- [builder] Adding zim-manager (automatically with kiwix)
- [catalog] Fixed WikiFundis missing a link to self via proxy for visualeditor
- [catalog] Added Magoe App
- [catalog] Added an icon for Edupi App
- [catalog] Updated Nomad Files app
- [catalog] Removed Edupi favicon branding mount (not supported yet)
- [catalog] Updated Edupi to 1.2
- [tests] Added basic JSON parsing test for catalog

## [1.5.2] - 2023-12-23

### Changed

- Fixed typo in catalog JSON

## [1.5.1] - 2023-12-23

### Added

- [builder] Ability to specify mirror URL for ZIM downloads

### Changed

- [catalog] Fixed WikiFundi entries: file extract, removed dev protect and applied FR conf to all

## [1.5.0] - 2023-12-23

### Added

- [config] `write_config` now handled, adding config to /data/image.yaml

### Changed

- [runtime] Fixed installed dnsmasq-spoof service (was not using venv-aware path)
- [catalog] Fixed typo in JSON rendering catalog unreadable
- [catalog] Renamed `icon` to `icon_url` to make it clearer about expected content
- [builder] Dashboard yaml config size properly reported
- [builder] now disables kiwix-serve homepage (redirect to fqdn)
- [builder] enabling captive portal now sets dhcp-range automatically and enabled as-gateway
- [builder] writting base64-encoded icon to dashboard yaml
- [builder] fixed zim-download subservice to `zim-download.{FQDN}`
- [builder] Files Packages now copied to /data/content (was /data/content/files)
- [builder] Files service now bound to /data/content (was /data/content/files)
- [builder] Using dashboard 1.2 (with ZIM discovery and healthcheck)
- [builder] Using reverse-proxy 1.4
- [builder] Using captive-portal 1.2
- [builder] Using hwclock 1.1
- [builder] Using filebrowser 1.1
- [builder] Added metrics support
- [zim] removed hack to circumvent libkiwix#1004 which has been fixed

## [1.4.6] - 2023-12-07

### Added

- `utils.sizes.get_sd_hardware_margin_for()` for std SDcard margin use
- `utils.sizes.ONE_GB` and `utils.sizes.ONE_GiB`
- Eleda packages (files and android) to catalog

### Changed

- Default read-from location for offspot.yaml in `/boot/firmware` (base-image 1.2)
- Changed get_bin() in offspot_runtime to accomodate in-venv offspot-runtime
- Country Code `00` for `ap` not accepted anymore (hostapd). Defaults to `US`
- Dashboard entry now contains `ident` of package as well
- Now developping on py3.11 as its default on base-image (bookworm)
- Using updated images (captive-portal:1.1 and kiwix-serve:3.6.0)

## [1.4.5] - 2023-10-24

### Changed

- Fixed placeholder not empty (not allowed)

## [1.4.4] - 2023-10-23

### Changed

- Adding placeholder files to prevent binding to non-existent files/folder in compose

## [1.4.3] - 2023-10-19

### Added

- Support for LVM Device Mapper in xattr_support check

## [1.4.2] - 2023-10-18

### Added

- Hack around libkiwix#1004 when checking ZIM existence

### Changed

- Fixed builder when not using reverse-proxy
- Fixed based image URL when using version only

## [1.4.1] - 2023-10-13

### Changed

- Fixed package access in AppCatalog

## [1.4.0] - 2023-10-04

### Added

- Added Builder
- Added Sizes computation
- Using dashboard:1.1
- Including JSON catalog in lib

# [1.3.0] - 2023-08-21

### Added

- Now bundling `offspot_config` module as well

## [1.2.0] - 2023-03-07

### Added

- `checks` module to test YAML configuration file values
  - most checks more resilient as checking input types
  - timezones actualy checked for existence instead of vague timezone-looking regex
  - compose checking now includes (optional) image presence checking and exposure of ports
  - ipv4 addresses are now checked for being actual IPv4 addresses with a flag to check if usable
  - network checks now checks for valid network strings and compatibility with related IP address
  - WiFi country code now checked for being an actual country code.
  - Added support (and as default) for 00 country code meaning less-permissive radio options
  - dhcp-range checks now checking for actual IP ranges with netwmask and host IP. ttl is also checked
- unit tests for checks module (100% covered)
- test workflow

### Changed

- fixed setup.py using a static `1.0` version instead of version reported to scripts
- renamed module from `offspot_runtime_config` to `offspot_runtime`
- renamed `offspot_config_lib` sub-module to `configlib`
- Fixed disabling auto-spoof apparently failing due to lack of return code
- `ap.dhcp_range_for()` now calculates an actual range instead of replacing strings
- updated QA worflow
- fixed program name in usage of scripts

# [1.1.0] - 2022-11-16

## Added

- `auto` option for `spoof` param in `ap` to adjust based on internet connectivity

## [1.0.0] - 2022-10-05

- initial version
