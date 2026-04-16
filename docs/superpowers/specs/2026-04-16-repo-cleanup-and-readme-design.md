# Repo Cleanup And README Design

## Summary

Clean the repository so it contains only the files needed for the current app to run, and replace the README with a simple guide for a new user.

The cleanup should remove generated artifacts, stale outputs, legacy duplicate code paths, and abandoned structures that are no longer part of the active app. This is not a refactor. The goal is to reduce confusion, not change architecture.

## Goals

- Keep only the files needed to run and understand the current app
- Remove generated, stale, and duplicate files
- Remove legacy code paths that are no longer part of the active application
- Rewrite the README so a new user can get running quickly
- Verify the remaining repository still supports the current browser-based upload workflow

## Non-Goals

- Refactoring active code
- Adding new product features
- Preserving legacy scripts as historical reference
- Expanding documentation beyond a simple user-facing README

## Cleanup Strategy

Use a strict keep-only-what-runs approach.

If a file or folder does not contribute to:

- the active app under `src/ynab_parser`
- package/runtime metadata
- setup/install steps
- current user-facing documentation
- minimal helpful sample inputs for validation

then it should be removed.

## Keep Set

### Active code

- `src/ynab_parser/`

This is the source of truth for the current application and browser UI.

### Packaging and dependency files

- `setup.py`
- `requirements.txt`
- `.gitignore`

These are needed for installation and repository hygiene.

### Configuration example

- `.env.example`

This is needed so a new user knows how to configure the app.

### User-facing documentation

- `README.md`
- `docs/superpowers/specs/`

The README is required for the user. The specs are already part of the repo workflow and should remain unless there is a separate request to remove project documentation.

### Optional support script

- `scripts/setup_venv.sh`

Keep only if it still provides a simple setup shortcut consistent with the rewritten README. If it is stale or redundant, remove it.

### Validation inputs

- minimal files under `data/incoming/` that are required to validate active parsing behavior

These may remain if they are needed for basic manual verification and do not confuse the user.

## Remove Set

### Generated and cache artifacts

- all `__pycache__/` directories
- all `.pyc` files
- `.DS_Store`
- `build/`
- stale egg/build artifacts not required for editable install workflows

### Legacy top-level code

Remove old standalone or duplicate paths if they are no longer part of the active app, including likely candidates such as:

- `ynab_api.py`
- other top-level standalone scripts already superseded by `src/ynab_parser`

### Abandoned legacy package structure

Remove old top-level directories that are not used by the active package and only remain as remnants of a previous structure, such as:

- `api/`
- `cli/`
- `config/`
- `models/`
- `services/`

These directories appear to contain only compiled artifacts or dead code structure and should not remain if they are not part of the runtime path.

### Stale outputs

- old files in `results/`

The app should not ship with stale parsed output files unless they are intentionally part of the user workflow. In this project they create confusion and should be removed.

### Misleading leftover files

Remove any file whose presence suggests a supported workflow that is no longer the real path for the app.

## README Design

The new README should be short, simple, and aimed at a first-time user.

### Required sections

1. Project overview
- one short paragraph
- mention the one-page browser UI
- mention supported upload types: CSV and OFX

2. Requirements
- Python version
- YNAB API token

3. Setup
- create venv
- install package
- create `.env` from `.env.example`

4. Run the app
- one command to launch the browser UI
- mention the local URL

5. How to use
- select budget
- select account
- upload file
- review preview
- upload to YNAB

6. File behavior
- CSV uploads are reformatted before preview/upload
- OFX uploads are sent through without that reformatting

7. Troubleshooting
- missing or invalid API token
- budgets/accounts not loading
- unsupported file format

### Tone

- concise
- practical
- no deep architecture explanation
- no long command reference
- no old workflow descriptions unless still required

## Validation Plan

After cleanup and README replacement, verify:

1. The remaining package imports correctly
2. `python3 -m ynab_parser ui --help` still works
3. The UI service still previews sample CSV input correctly
4. The UI service still previews sample OFX input correctly
5. Removed files are not referenced by the active runtime path

## Risk Management

### Main risk

Deleting a file that still has a runtime reference.

### Mitigation

- search for file references before deletion
- remove only after confirming the active package does not import or depend on the file
- run targeted validation immediately after cleanup

## File Plan

### Files expected to be updated

- `README.md`
- possibly `.env.example`
- possibly `scripts/setup_venv.sh`

### Files expected to be removed

- generated/cache/build artifacts
- stale outputs in `results/`
- legacy top-level duplicate code and dead directories outside `src/ynab_parser`

## Implementation Boundaries

This task is intentionally narrow:

- delete unnecessary files
- keep the active app working
- replace the README with a simpler one

No refactoring or behavior changes are required as part of the cleanup itself.
