# Changelog

All notable changes to shc-pulumi are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- README updated with maintenance mode notice
- NoDNS can be handled outside Pulumi via `shc nodns --ip <ip>` CLI
- New projects should use the TF Bridge instead of this native provider

## [0.5.0] — 2026-07-02

Initial release with:
- VM lifecycle (create/read/update/delete) with spec-encoding size names
- Snapshot, Backup, Firewall rule, rDNS resources
- NoDNS integration (nodns=True auto-publishes Nostr DNS)
- Credit pre-check before ordering
- 95 unit tests
