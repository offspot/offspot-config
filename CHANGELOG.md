# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
