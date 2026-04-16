"""
Local single-page web UI for selecting a YNAB account and uploading a bank CSV.
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from .core.exceptions import APIError, ConfigurationError, ParserError
from .core.logging_config import get_logger, setup_logging
from .ui_service import UploadUIService

logger = get_logger("webapp")


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YNAB Upload UI</title>
  <style>
    :root {
      --bg: #f6f1e8;
      --panel: #fffaf2;
      --ink: #1e1b18;
      --muted: #6c6258;
      --line: #d8c8af;
      --accent: #0b6e4f;
      --accent-2: #c96f2d;
      --danger: #a62c2b;
      --shadow: 0 18px 48px rgba(60, 42, 18, 0.12);
      --radius: 18px;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(201,111,45,0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(11,110,79,0.14), transparent 24%),
        linear-gradient(180deg, #fbf6ee 0%, var(--bg) 100%);
      min-height: 100vh;
    }

    .shell {
      max-width: 1120px;
      margin: 0 auto;
      padding: 40px 20px 72px;
    }

    .hero {
      display: grid;
      gap: 14px;
      margin-bottom: 28px;
    }

    .eyebrow {
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }

    h1 {
      margin: 0;
      font-size: clamp(36px, 6vw, 62px);
      line-height: 0.95;
      font-weight: 700;
    }

    .subtitle {
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.45;
    }

    .grid {
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 22px;
      align-items: start;
    }

    .card {
      background: var(--panel);
      border: 1px solid rgba(216, 200, 175, 0.85);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 22px;
    }

    .card h2 {
      margin: 0 0 6px;
      font-size: 22px;
    }

    .card p.lead {
      margin: 0 0 18px;
      color: var(--muted);
    }

    .stack { display: grid; gap: 16px; }

    label {
      display: grid;
      gap: 8px;
      font-weight: 700;
      font-size: 14px;
    }

    select, input[type="file"], button {
      font: inherit;
    }

    select, input[type="file"] {
      width: 100%;
      min-height: 48px;
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      background: white;
      color: var(--ink);
    }

    button {
      min-height: 50px;
      border: none;
      border-radius: 999px;
      padding: 0 22px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease, background 120ms ease;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.45;
      transform: none;
    }

    button.primary {
      background: linear-gradient(135deg, var(--accent) 0%, #0a8f67 100%);
      color: white;
    }

    button.secondary {
      background: #efe0ca;
      color: var(--ink);
    }

    button:hover:not(:disabled) {
      transform: translateY(-1px);
    }

    .status {
      border-radius: 14px;
      padding: 14px 16px;
      font-size: 14px;
      line-height: 1.4;
      border: 1px solid transparent;
      white-space: pre-wrap;
    }

    .status.info {
      background: #f0f7f3;
      border-color: #b8d8ca;
      color: #154b39;
    }

    .status.warn {
      background: #fff4e8;
      border-color: #efc28a;
      color: #8b4a17;
    }

    .status.error {
      background: #fff0f0;
      border-color: #e7b3b3;
      color: var(--danger);
    }

    .preview-meta {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .metric {
      background: rgba(201,111,45,0.08);
      border-radius: 14px;
      padding: 14px;
    }

    .metric .k {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 6px;
    }

    .metric .v {
      font-size: 18px;
      font-weight: 700;
    }

    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 620px;
    }

    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid #eee2d1;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }

    th {
      position: sticky;
      top: 0;
      background: #fff8ef;
      z-index: 1;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .muted {
      color: var(--muted);
      font-size: 13px;
    }

    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }

    @media (max-width: 940px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">Local Browser Workflow</div>
      <h1>Upload bank CSVs straight into YNAB</h1>
      <p class="subtitle">Choose a budget, pick a target account, preview the parsed transactions, and then upload everything from one page.</p>
    </section>

    <div class="grid">
      <section class="card stack">
        <div>
          <h2>Upload Flow</h2>
          <p class="lead">The page stays put while the budget, account, preview, and upload state update in place.</p>
        </div>

        <div id="global-status" class="status info">Loading budgets from YNAB...</div>

        <label>
          Budget
          <select id="budget-select">
            <option value="">Loading budgets...</option>
          </select>
        </label>

        <label>
          Account
          <select id="account-select" disabled>
            <option value="">Select a budget first</option>
          </select>
        </label>

        <label>
          Bank CSV file
          <input id="file-input" type="file" accept=".csv,.ofx,text/csv,application/x-ofx">
        </label>

        <div class="muted">Supported today: OCBC and POSB/DBS CSV exports, plus OFX uploads.</div>

        <div class="actions">
          <button id="preview-button" class="secondary" disabled>Parse Preview</button>
          <button id="upload-button" class="primary" disabled>Review and Upload</button>
        </div>

        <div id="action-status" class="status info" hidden>Select a budget, account, and CSV file to begin.</div>
      </section>

      <section class="card stack">
        <div>
          <h2>Preview</h2>
          <p class="lead">Valid transactions appear here before anything is sent to YNAB.</p>
        </div>

        <div class="preview-meta">
          <div class="metric"><span class="k">Detected Bank</span><span id="meta-bank" class="v">-</span></div>
          <div class="metric"><span class="k">File Name</span><span id="meta-file" class="v">-</span></div>
          <div class="metric"><span class="k">Valid Rows</span><span id="meta-count" class="v">0</span></div>
          <div class="metric"><span class="k">Warnings</span><span id="meta-warnings" class="v">0</span></div>
        </div>

        <div id="preview-status" class="status info">No preview yet.</div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Payee</th>
                <th>Memo</th>
                <th>Outflow</th>
                <th>Inflow</th>
              </tr>
            </thead>
            <tbody id="preview-body">
              <tr><td colspan="5" class="muted">Upload a file to see parsed transactions here.</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>

  <script>
    const state = {
      budgets: [],
      accounts: [],
      previewId: "",
      previewRows: [],
      fileText: "",
      fileName: "",
    };

    const budgetSelect = document.getElementById("budget-select");
    const accountSelect = document.getElementById("account-select");
    const fileInput = document.getElementById("file-input");
    const previewButton = document.getElementById("preview-button");
    const uploadButton = document.getElementById("upload-button");
    const globalStatus = document.getElementById("global-status");
    const actionStatus = document.getElementById("action-status");
    const previewStatus = document.getElementById("preview-status");
    const previewBody = document.getElementById("preview-body");
    const metaBank = document.getElementById("meta-bank");
    const metaFile = document.getElementById("meta-file");
    const metaCount = document.getElementById("meta-count");
    const metaWarnings = document.getElementById("meta-warnings");

    function setStatus(el, kind, text, hidden = false) {
      el.hidden = hidden;
      el.className = "status " + kind;
      el.textContent = text;
    }

    function setPreviewMeta(data = {}) {
      metaBank.textContent = data.bank || "-";
      metaFile.textContent = data.file_name || "-";
      metaCount.textContent = String(data.row_count || 0);
      metaWarnings.textContent = String(data.warning_count || 0);
    }

    function renderTable(rows) {
      if (!rows.length) {
        previewBody.innerHTML = '<tr><td colspan="5" class="muted">No valid transactions available for preview.</td></tr>';
        return;
      }
      previewBody.innerHTML = rows.slice(0, 100).map((row) => `
        <tr>
          <td>${escapeHtml(row.date)}</td>
          <td>${escapeHtml(row.payee)}</td>
          <td>${escapeHtml(row.memo || "")}</td>
          <td>${escapeHtml(row.outflow || "")}</td>
          <td>${escapeHtml(row.inflow || "")}</td>
        </tr>
      `).join("");
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function updateButtons() {
      previewButton.disabled = !(budgetSelect.value && accountSelect.value && state.fileText);
      uploadButton.disabled = !(state.previewId && budgetSelect.value && accountSelect.value && state.previewRows.length);
    }

    async function requestJSON(url, options = {}) {
      const response = await fetch(url, options);
      const payload = await response.json().catch(() => ({ ok: false, error: "Invalid server response" }));
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || "Request failed");
      }
      return payload;
    }

    async function loadBudgets() {
      try {
        const payload = await requestJSON("/api/budgets");
        state.budgets = payload.budgets || [];
        if (!state.budgets.length) {
          budgetSelect.innerHTML = '<option value="">No budgets found</option>';
          setStatus(globalStatus, "warn", "Connected to YNAB, but no budgets were returned.");
          return;
        }
        budgetSelect.innerHTML = '<option value="">Choose a budget</option>' +
          state.budgets.map((budget) => `<option value="${budget.id}">${escapeHtml(budget.name)}</option>`).join("");
        setStatus(globalStatus, "info", "Budgets loaded. Choose a budget to load its accounts.");
      } catch (error) {
        budgetSelect.innerHTML = '<option value="">Unable to load budgets</option>';
        setStatus(globalStatus, "error", error.message);
      }
      updateButtons();
    }

    async function loadAccounts(budgetId) {
      accountSelect.disabled = true;
      accountSelect.innerHTML = '<option value="">Loading accounts...</option>';
      updateButtons();
      try {
        const payload = await requestJSON(`/api/budgets/${encodeURIComponent(budgetId)}/accounts`);
        state.accounts = (payload.accounts || []).filter((account) => !account.closed);
        accountSelect.innerHTML = '<option value="">Choose an account</option>' +
          state.accounts.map((account) => `<option value="${account.id}">${escapeHtml(account.name)}</option>`).join("");
        accountSelect.disabled = false;
        setStatus(globalStatus, "info", "Accounts loaded. Choose a target account, then preview your CSV.");
      } catch (error) {
        accountSelect.innerHTML = '<option value="">Unable to load accounts</option>';
        setStatus(globalStatus, "error", error.message);
      }
      updateButtons();
    }

    async function parsePreview() {
      setStatus(actionStatus, "info", "Parsing uploaded CSV...");
      try {
        const payload = await requestJSON("/api/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file_name: state.fileName,
            content: state.fileText,
          }),
        });
        state.previewId = payload.preview_id;
        state.previewRows = payload.transactions || [];
        setPreviewMeta(payload);
        renderTable(state.previewRows);
        if (payload.warning_count) {
          setStatus(previewStatus, "warn", payload.warnings.join("\\n"));
        } else {
          setStatus(previewStatus, "info", "Preview parsed successfully. Review the rows and upload when ready.");
        }
        setStatus(actionStatus, "info", "Preview ready. Nothing has been uploaded yet.");
      } catch (error) {
        state.previewId = "";
        state.previewRows = [];
        setPreviewMeta({});
        renderTable([]);
        setStatus(previewStatus, "error", error.message);
        setStatus(actionStatus, "error", "Preview failed. Fix the issue and try again.");
      }
      updateButtons();
    }

    async function uploadPreview() {
      setStatus(actionStatus, "info", "Uploading previewed transactions to YNAB...");
      try {
        const payload = await requestJSON("/api/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            preview_id: state.previewId,
            budget_id: budgetSelect.value,
            account_id: accountSelect.value,
          }),
        });
        setStatus(actionStatus, "info", `Upload complete. Sent ${payload.uploaded} transaction(s) to YNAB.`);
        if (payload.skipped) {
          setStatus(previewStatus, "warn", `Upload finished with ${payload.skipped} skipped row(s).`);
        } else {
          setStatus(previewStatus, "info", "Upload finished successfully.");
        }
      } catch (error) {
        setStatus(actionStatus, "error", error.message);
      }
    }

    budgetSelect.addEventListener("change", () => {
      state.previewId = "";
      state.previewRows = [];
      setPreviewMeta({});
      renderTable([]);
      if (!budgetSelect.value) {
        accountSelect.disabled = true;
        accountSelect.innerHTML = '<option value="">Select a budget first</option>';
        updateButtons();
        return;
      }
      loadAccounts(budgetSelect.value);
    });

    accountSelect.addEventListener("change", updateButtons);

    fileInput.addEventListener("change", async (event) => {
      const file = event.target.files[0];
      state.previewId = "";
      state.previewRows = [];
      setPreviewMeta({});
      renderTable([]);
      if (!file) {
        state.fileText = "";
        state.fileName = "";
        updateButtons();
        return;
      }
      state.fileName = file.name;
      state.fileText = await file.text();
      setStatus(actionStatus, "info", `Loaded ${file.name}. Ready to parse preview.`);
      updateButtons();
    });

    previewButton.addEventListener("click", parsePreview);
    uploadButton.addEventListener("click", uploadPreview);

    renderTable([]);
    loadBudgets();
  </script>
</body>
</html>
"""


class UploadUIHandler(BaseHTTPRequestHandler):
    """HTTP handler serving the single-page app and JSON endpoints."""

    service: Optional[UploadUIService] = None

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(HTML_PAGE)
            return

        if self.path == "/api/budgets":
            self._handle_json(self._api_budgets)
            return

        if self.path.startswith("/api/budgets/") and self.path.endswith("/accounts"):
            self._handle_json(self._api_accounts)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if self.path == "/api/preview":
            self._handle_json(self._api_preview)
            return

        if self.path == "/api/upload":
            self._handle_json(self._api_upload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)

    def _handle_json(self, callback) -> None:
        try:
            payload = callback()
            self._send_json({"ok": True, **payload})
        except (ConfigurationError, APIError, ParserError, ValueError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            logger.error("Unhandled UI server error: %s", exc, exc_info=True)
            self._send_json(
                {"ok": False, "error": "Unexpected server error"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _api_budgets(self) -> Dict[str, Any]:
        return {"budgets": self.service.get_budgets()}

    def _api_accounts(self) -> Dict[str, Any]:
        parts = self.path.split("/")
        budget_id = parts[3]
        return {"accounts": self.service.get_accounts(budget_id)}

    def _api_preview(self) -> Dict[str, Any]:
        body = self._read_json_body()
        file_name = body.get("file_name", "").strip()
        content = body.get("content", "")
        if not file_name or not content:
            raise ValueError("file_name and content are required")
        return self.service.preview_upload(file_name=file_name, content=content)

    def _api_upload(self) -> Dict[str, Any]:
        body = self._read_json_body()
        preview_id = body.get("preview_id", "").strip()
        budget_id = body.get("budget_id", "").strip()
        account_id = body.get("account_id", "").strip()
        if not preview_id or not budget_id or not account_id:
            raise ValueError("preview_id, budget_id, and account_id are required")
        return self.service.upload_preview(preview_id, budget_id, account_id)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str, port: int, env_file: str) -> ThreadingHTTPServer:
    """Create a configured UI web server instance."""
    service = UploadUIService(env_file=env_file)

    class BoundHandler(UploadUIHandler):
        pass

    BoundHandler.service = service
    return ThreadingHTTPServer((host, port), BoundHandler)


def main(argv: Optional[List[str]] = None) -> int:
    """Launch the local web UI."""
    parser = argparse.ArgumentParser(description="Launch the local YNAB upload UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument("--config", default=".env", help="Path to .env config file")
    args = parser.parse_args(argv)

    setup_logging("ynab_parser.webapp")

    server = create_server(args.host, args.port, args.config)
    url = f"http://{args.host}:{args.port}"
    logger.info("Starting local upload UI at %s", url)
    logger.info("Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping local upload UI.")
    finally:
        server.server_close()

    return 0
