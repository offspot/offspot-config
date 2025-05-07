# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.1] - 2025-05-07

### Changed

- [captive-portal] Using [1.5.3](https://github.com/offspot/captive-portal/blob/1.5.3/CHANGELOG.md) with regression (1.5.2) fix

## [2.6.0] - 2025-05-07

### Added

- [builder] New `public_version` param allowing any string as advertised version in About

## [2.5.4] - 2025-05-07

### Changed

- [captive-portal] Using [1.5.2](https://github.com/offspot/captive-portal/blob/1.5.2/CHANGELOG.md) with better wording
- [dashboard] Using [1.6.2](https://github.com/offspot/dashboard/blob/1.6.2/CHANGELOG.md) with fixed `mul` exclusion

## [2.5.3] - 2025-03-25

### Fixed

- [runtime] iptables-restore service detection

## [2.5.2] - 2025-03-15

### Changed

- [captive-portal] Using [1.5.1](https://github.com/offspot/captive-portal/blob/1.5.1/CHANGELOG.md) with fixed post-reg page in FR/ES android

## [2.5.1] - 2025-03-08

### Changed

- [dashboard] Using 1.6.1 with fixed menu

## [2.5.0] - 2025-03-07

### Changed

- [dashboard] Using 1.6.0 with updated UI (About page)
- [reverse-proxy] Using 1.11 with custom kiwix external link block page

## [2.4.2] - 2025-03-07

### Fixed

- [kiwix] Fixed dashboard links still broken in 2.4.1

## [2.4.1] - 2025-03-07

### Fixed

- [branding] Eventually settled on no-padding branding
- [kiwix] Fixed links and NO_HOME broken in 2.4.0
- [dashboard] Added offspot-config version as hotspot version for dashboard 1.5

## [2.4.0] - 2025-02-18

### Changed

- [branding] Updated logos to use new (case) version and removed dark-mode versions (now same as light)
- [captive-portal] Using 1.5.0 with updated branding
- [dashboard] Using 1.5.0 with updated branding and removed size filter
- [kiwix-serve] Using 3.7.0-2
- [kiwix-serve] Kiwix-serve subdomain changed from `kiwix` to `browse`
- [reverse-proxy] Using 1.10 with updated Caddy

## [2.3.2] - 2025-01-20

### Added

- [catalog] Added Af&Rica files packages in FR, EN, AR.

### Changed

- [catalog] Update name and description for file-manager.offspot.kiwix.org (now File Manager)

## [2.3.1] - 2024-10-17

### Changed

- [catalog] Domain names now uses dashes instead of underscores:
  - `com.kylecorry.trail_sense.offspot.kiwix.org`
  - `org.hlwd.bible_multi_the_life.offspot.kiwix.org`


## [2.3.0]

### Changed

- [builder] Updated dashboard version to 1.4.8 (from 1.3)

## [2.2.6]

### Added

- [branding] Added dark versions of square and horizontal logos
- [branding] Added light+dark enabled square and horizontal SVG logos

### Changed

- [branding] Updated light PNG logos in accordance to Branding guidelines

### Removed

- [catalog] `eleda.offspot.kiwix.org` package as it is available as a ZIM

## [2.2.5] - 2024-05-21

### Added

- [utils.dashboard] New `Reader.to_dashboard_dict()` returning dashboard-transformed download URL

### Fixed

- [builder] Reader download link using local URL

## [2.2.4] - 2024-05-01

### Changed

- [builder] Using captive-portal 1.4.3 fixing 2.2.1 regression

## [2.2.3] - 2024-04-26

### Fixed

- branding folders were mounted inside another volumes in kiwix service

## [2.2.2] - 2024-04-25

### Fixed

- original branding incorrectly set as url

## [2.2.1] - 2024-04-25

### Fixed

- YAML repr of Checksum (#42)

### Changed

- Using captive-portal 1.4.2 with branding support

## [2.2.0] - 2024-04-24

### Added

- [inputs.file] `File.is_base64_encoded` if `via` is `base64`
- [utils.misc] `b64_encode()` and `b64_decode()` for reproducible base64 transport
- [branding] `branding` folder in `offspot_config` containing official/original offspot branding files
- [constants] `INTERNAL_BRANDING_PATH` pointing to code-reachable folder of branding files
- [builder] `ORIGINAL_BRANDING_PATH` constant for '/data/branding`
- [builder] `BRANDING_PATH` constant for `/data/contents/branding`

### Changed

- [builder] Using kiwix-serve 3.7.0-1
- [builder] Using reverse-proxy 1.8
- [builder] Original branding files copied to `ORIGINAL_BRANDING_PATH`
- [builder] Creating empty `BRANDING_PATH` for hotspot-specific branding
- [builder] Added mounts for `BRANDING_PATH` (and `ORIGINAL_BRANDING_PATH`) on all internal apps
- [builder] Catalog apps can mount `${BRANDING_PATH}` or `${ORIGINAL_BRANDING_PATH}`

## [2.1.0] - 2024-04-18

### Added

- [inputs.checksum] `Checksum` gets a `to_dict()` method
- [dashboard] `Reader` gets an optional `checksum`

### Changed

- [builder] Removed useless download.kiwix.org special behavior for reader checksum. Checksum now on Reader
- [builder] Using captive-portal 1.4.1
- [inputs.base] Version-only base image def now targets uncompressed URL
- [inputs.base] BaseConfig gets an optional `checksum` and populates base_file accordingly
- [inputs.base] Version-only base image def now also retrieves Checksum via expected .md5 endpoint

## [2.0.0] - 2024-04-16

### Added

- [inputs.file] File now includes a `checksum` property (optional)
- [inputs.checksum] Checksum now includes an `as_aria` property (`algo=digest` formatted string)

### Changed ⚠️ BREAKING

- [inputs] API refactored into an empty `inputs` module with many sub-modules (breaking change)

## [1.14.0] - 2024-04-11

### Added

- [utils.download] `get_payload_from` to retrieve small bit of data from a URL
- [utils.download] `read_checksum_from` to retrieve digest-looking string from a URL
- [inputs] `Checksum` type that describe a checksum with its algo (several supported) and includes mechanism for later-resolution via URL URL retrieval
- [inputs] Packages (Files, App, Zim) gets an optional `download_checksum` param that is passed to FileConfig
- [builder] Readers get an automatically fetched checksum if URL is on download.kiwix.org
- [builder] `add_file()` takes an optional `checksum` param

### Changed

- [catalog] All Catalog entries now have download_checksum if applicable
- [zim] `get_zim_package` now includes a live-fetched MD5 checksum


## [1.13.0] - 2024-04-01

### Added

- [utils.dashboard] Reader struct to ease passing `readers` to dashboard YAML
- [utils.dashboard] Link struct to ease passing `links` to dashboard YAML
- [builder] `add_dashboard()` param: `readers` to automatically add and offer Kiwix readers in dashboard (1.4+)
- [builder] `add_dashboard()` param: `links` to add arbitrary links to dashboard (1.4+)

## Changed

- [builder] `resolved_variable()` can now be used without a Package

## [1.12.2] - 2024-03-14

### Fixed

- [catalog] magoe update wasn't included

## [1.12.1] - 2024-03-05

### Changed

- [catalog] Updated magoe package

## [1.12.0] - 2024-02-21

### Added

- [zim] `get_libkiwix_humanid()` to get kiwix-serve BookName from a filename

### Changed

- [packages] `ZimPackage.get_url()` now uses libkiwix's human ID

## [1.11.0] - 2024-02-17

### Added

- [zim] `to_ident()` and `from_ident()` functions to consistently work on idents
- [zim] `ZimIdentTuple` type, returned by `from_ident()`

### Changed

- [packages] `ZimPackage.filename` now returns an ident-based one preventing conflicts on files with different flavours

## [1.10.1] - 2024-02-12

### Changed

- [builder] Using dashboard:1.3.1

## [1.10.0] - 2024-02-11

### Added

- [firmware] New `firmware` top level config for runtime to change WiFi firmware

### Fixed

- [builder] Welcome FQDN properly set (goto.kiwix)
- [catalog] file-manager URL (no trailing slash)

### Changed

- [builder] Using captive-portal:1.4 with offline fix
- [builder] Using reverse-proxy:1.7 with welcome_fqdn
- [catalog] Using file-manager:1.3 with metrics headers

## [1.9.0] - 2024-02-09

### Added

- [builder] AP welcome_domain now settable (defaulting to `goto.kiwix`)
- [ap] `captured-address` allows setting the DNS fallback target for when offline

## Changed

- [ap] Auto `spoof` dnsmasq switcher now toggles by uncommenting what's commented and commenting what's not.
- [ap] `no-resolv` and `dhcp-athoritative` added to DNSmasq config
- [ap] Upstream `server` for DNSmasq only set when Online

## [1.8.2] - 2024-02-05

### Changed

- [builder] Using reverse-proxy 1.6

## [1.8.1] - 2024-02-05

### Changed

- [builder] Using metrics 0.3.0

## [1.8.0] - 2024-01-30

### Added

- `Package.size` informing overall package size (image and download_size)

### Changed

- [builder] Using metrics 0.3.0

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
CHANGELOG.md
