# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add secure channel-owner OAuth authorization with canonical per-user storage,
  automation path overrides, and reusable refreshable credentials. (#2)

### Fixed

- Preserve stored credentials when reauthorization is denied or fails. (#15)
