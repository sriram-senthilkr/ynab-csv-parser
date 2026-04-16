# Upload UI Design

## Summary

Build a local browser-based single-page UI for the YNAB CSV parser. The UI should let the user:

- load available YNAB budgets from the API
- choose a budget
- load accounts for that budget into a dropdown
- upload a bank CSV file
- preview parsed transactions on the same page
- click `Review and Upload` to send the parsed transactions directly to the selected YNAB account

The app should reuse the existing Python parser, conversion, configuration, and YNAB API code wherever practical.

## Goals

- Keep the interaction on one page with no page-to-page navigation.
- Pull budgets and accounts live from the YNAB API using the configured token.
- Parse uploaded files in memory and show a preview before upload.
- Upload transactions directly to the specific YNAB account selected in the UI.
- Preserve the existing CLI-based processing and upload workflow.

## Non-Goals

- Building a separate frontend application or JavaScript framework project
- Adding authentication beyond the existing `.env`-based YNAB token
- Supporting banks beyond the existing parser set in this implementation
- Persisting upload history or storing uploaded files long-term

## User Experience

The app is a single-page local web app.

### Page layout

1. Header
- app title
- short status text describing the configured environment

2. Budget selection section
- budget dropdown
- loading and error state for budget fetch

3. Account selection section
- account dropdown
- disabled until a budget is selected
- loading and error state for account fetch

4. File upload section
- file picker
- optional drag-and-drop target if straightforward within the same implementation
- helper text naming supported bank formats

5. Preview section
- detected bank
- uploaded file name
- number of valid parsed transactions
- warning count for skipped or invalid rows
- preview table with normalized YNAB-style columns

6. Action section
- `Review and Upload` button
- disabled until budget, account, and valid preview data are ready

7. Result section
- inline success summary
- inline validation or API error details
- retry remains possible without leaving the page

### Interaction flow

1. User opens the local UI.
2. App loads budgets from YNAB.
3. User selects a budget.
4. App loads accounts for that budget.
5. User selects an account.
6. User uploads a CSV file.
7. Server detects the bank format, parses the file, and returns a preview.
8. User reviews the preview.
9. User clicks `Review and Upload`.
10. App uploads the previewed transactions to the selected YNAB account and displays the outcome inline.

## Architecture

### Approach

Implement a lightweight Python web server in the existing package. Use server-rendered HTML plus small client-side JavaScript for dropdown population, preview refresh, and upload actions.

This approach is preferred because:

- the repository is already Python-first
- the parser and YNAB integration code already exist in Python
- it keeps the runtime simple
- it avoids introducing a separate frontend toolchain

### New components

#### 1. Local web server entry point

Add a small web app module under `src/ynab_parser` with:

- a route for the main page
- JSON endpoints for budgets, accounts, preview parsing, and upload
- a CLI-accessible launch command

Recommended shape:

- `src/ynab_parser/webapp.py` for the server entry point
- `templates/` and `static/` directories under `src/ynab_parser` or a similarly compact structure

#### 2. UI service layer

Add a focused service layer that:

- fetches budgets and accounts through `YNABClient`
- detects bank type for an uploaded CSV
- parses rows into normalized preview records
- stores short-lived preview sessions in memory
- converts preview rows into YNAB transactions for a chosen account

Recommended shape:

- `src/ynab_parser/ui_service.py`

This layer should isolate the web routes from parsing and upload details.

#### 3. Preview session store

Use a short-lived in-memory store keyed by a generated preview ID.

Each preview session contains:

- original filename
- detected bank
- normalized parsed rows
- parse warning count and warning messages

The preview store should be process-local only. Restarting the app clears it.

## Data Flow

### Load budgets

1. Browser loads the single page.
2. Frontend calls `GET /api/budgets`.
3. Server reads token from `.env` via existing config code.
4. Server fetches budgets through `YNABClient.get_budgets()`.
5. Frontend populates the budget dropdown.

### Load accounts

1. User selects a budget.
2. Frontend calls `GET /api/budgets/<budget_id>/accounts`.
3. Server fetches accounts through `YNABClient.get_accounts(budget_id)`.
4. Frontend populates the account dropdown.

### Parse preview

1. User uploads a CSV.
2. Frontend sends the file to `POST /api/preview`.
3. Server inspects the CSV content and determines which parser can handle it.
4. Server parses the file in memory.
5. Server returns:
- preview ID
- detected bank
- normalized transaction rows
- warning counts and details
6. Frontend updates the preview section and enables `Review and Upload` if valid rows exist.

### Upload

1. User clicks `Review and Upload`.
2. Frontend sends `preview_id`, `budget_id`, and `account_id` to `POST /api/upload`.
3. Server loads the preview session from memory.
4. Server converts preview rows into YNAB `Transaction` objects using the selected account ID.
5. Server uploads them through `YNABClient.create_transactions(...)`.
6. Frontend shows inline success or failure details.

## Reuse Of Existing Code

### Keep and reuse

- `ConfigManager` for token and defaults
- `YNABClient` for budget, account, and transaction API calls
- existing bank parser classes for file parsing
- existing transaction models and conversion logic where useful

### Required adaptation

The current CLI uploader is based on filename-derived account mapping. The UI upload flow needs direct account targeting from a user-selected YNAB account ID. That means the UI path should not depend on filename-based mapping.

Add a targeted conversion/upload path that accepts:

- parsed preview rows
- explicit `account_id`
- explicit `budget_id`

This should live in the service layer or a small helper class rather than overloading the existing batch uploader logic.

## API Endpoints

### `GET /`

Returns the single HTML page.

### `GET /api/budgets`

Returns:

- list of budgets with `id` and `name`
- configuration error if token is missing or invalid

### `GET /api/budgets/<budget_id>/accounts`

Returns:

- list of accounts with `id`, `name`, and useful display metadata

### `POST /api/preview`

Multipart form upload with one CSV file.

Returns:

- `preview_id`
- `file_name`
- `bank`
- `row_count`
- `warning_count`
- `warnings`
- `transactions` preview rows

### `POST /api/upload`

JSON body:

- `preview_id`
- `budget_id`
- `account_id`

Returns:

- upload success count
- upload response summary
- error details if the YNAB API rejects the request

## Error Handling

### Configuration errors

If `.env` is missing, incomplete, or the token is invalid:

- show an inline error on the page
- keep the rest of the page visible
- do not allow budget loading to fail silently

### Budget or account fetch failures

- show the error near the relevant dropdown
- leave the page usable
- do not reset unrelated UI state

### Unsupported file format

- show a parse error inline
- keep `Review and Upload` disabled
- do not clear the budget or account selections

### Partial parse

If some rows fail to parse:

- show the valid rows in preview
- show warning counts and a short warning summary
- still allow upload of the valid rows

### Upload failure

- show the YNAB API error inline
- preserve the preview so the user can retry
- avoid clearing the selected budget, account, or uploaded preview automatically

## Testing Strategy

### Unit tests

- budget/account fetch wrappers
- bank detection logic
- preview parsing for OCBC and POSB samples
- conversion of preview rows into YNAB transactions using a selected account ID

### Route tests

- page load
- budget fetch success and config failure
- account fetch success and API failure
- preview upload success and unsupported file failure
- upload success and upload API failure

### Manual checks

- launch local web app
- select budget and account
- upload an OCBC file and preview rows
- upload a POSB file and preview rows
- confirm `Review and Upload` stays disabled until valid state exists
- verify successful upload flow with dry-run-style safety during development

## CLI Integration

Add a CLI entry to launch the local UI.

Recommended user-facing command:

- `python -m ynab_parser ui`

Optional package entry point:

- `ynab-ui`

The command should start the local server and print the local URL clearly.

## File Plan

Expected additions:

- `src/ynab_parser/webapp.py`
- `src/ynab_parser/ui_service.py`
- `src/ynab_parser/templates/...`
- `src/ynab_parser/static/...`
- tests for the new UI service and routes

Expected updates:

- `src/ynab_parser/cli.py`
- `setup.py`
- `README.md`
- small adjustments in shared upload/conversion helpers to support explicit account selection

## Open Decisions Resolved

- UI type: local web app in browser
- page model: one page only
- selection flow: budget dropdown first, then account dropdown
- upload timing: preview first, explicit `Review and Upload` button

## Implementation Boundaries

This design intentionally keeps the first version focused:

- one-page app
- no separate frontend framework
- no persistent database
- no background job system
- no multi-user session management beyond local temporary in-memory preview state

That keeps the feature aligned with the current repo and small enough for a single implementation plan.
