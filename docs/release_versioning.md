# Release Versioning Policy

LexiChess uses semantic versioning for tagged releases.

## Format

`MAJOR.MINOR.PATCH`

- `MAJOR` for breaking changes to public APIs, CLI behavior, or documented workflows
- `MINOR` for backward-compatible features
- `PATCH` for backward-compatible fixes, tooling improvements, or documentation corrections

## Current Stage Guidance

While the project is still pre-1.0:

- breaking changes are expected
- tags should still follow semantic structure
- release notes should clearly call out user-visible changes and migration steps

## Tagging Rules

- create an annotated git tag for each release
- record the release in `CHANGELOG.md`
- note verification steps used for the release
