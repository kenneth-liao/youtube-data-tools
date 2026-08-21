# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add secure channel-owner OAuth authorization with canonical per-user storage,
  automation path overrides, and reusable refreshable credentials. (#2)
- Add generic synchronous channel analytics queries with named JSON rows and
  actionable Google API errors. (#3)
- Add explicit CSV output for analytics queries, including header-only empty
  results. (#4)
- Add explicit enrichment of analytics video rows with current authorized
  YouTube Data API metadata. (#5)
- Add predefined channel and owned-video analytics snapshots with authoritative
  period aggregates, daily trends, and actual returned ranges. (#6)
- Compare analytics snapshots with the preceding equal-length period by default,
  including explicit absolute and percentage changes. (#7)
- Add authorized Reporting API report-type discovery with paginated,
  agent-selectable JSON output and reach-report identification. (#9)
- Add asynchronous reporting-job creation, listing, and explicit deletion by
  stable upstream identity. (#10)
- Add paginated generated-file discovery for selected reporting jobs with
  preserved download identity and explicit pending availability. (#11)
- Add authorized streaming downloads to explicit atomic destinations with
  opt-in replacement and identity-rich suggested filenames. (#12)
- Add a non-blocking thumbnail reach workflow that discovers the current report
  type, reuses or creates its job, lists all files, and downloads explicit
  selections. (#13)

### Fixed

- Preserve stored credentials when reauthorization is denied or fails. (#15)
