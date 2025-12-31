# REDESIM Gmail Draft Pipeline — Summary (v1.0-redesim-gmail-draft)

Scope

- Stabilize compose-only Gmail OAuth and draft-only flow for REDESIM.
- Keep existing REDESIM extraction logic untouched; no send actions.

What was done

- gmail_auth: project-scoped credentials at `credentials/gmail_credentials.json`, tokens at `credentials/gmail_token.json`; InstalledAppFlow (local server); reuse/refresh tokens; enforce `https://www.googleapis.com/auth/gmail.compose` only.
- gmail_draft_creator: single draft path using gmail_auth; accepts list/tuple/set recipients; returns draft ID; never sends.
- email_client and GmailService: aligned to gmail_auth paths and compose-only scope (no behavior change to send_email, just auth alignment).
- Test entrypoint `scripts/test_redesim_gmail_draft.py`: safe CLI that creates one draft, never sends; triggers browser OAuth if token is missing.

Verification

- Draft successfully created in Gmail (subject: “REDESIM Gmail draft test”; body: “Safe test draft created by REDESIM pipeline.”).
- No Gmail send logic executed; only draft creation.
- REDESIM extraction modules remain untouched.

How to run the test (draft-only, safe)

- Command: `/Users/dnigga/Documents/FBP_Backend/.venv/bin/python /Users/dnigga/Documents/FBP_Backend/scripts/test_redesim_gmail_draft.py --to "recipient@example.com" --subject "REDESIM Gmail draft test"`
- Behavior: writes token to `credentials/gmail_token.json` on first run (browser OAuth prompt); reuses token afterward; creates a Gmail draft and prints the draft ID.

Constraints respected

- No new scopes; compose-only.
- No new Gmail modules; no async queues or background jobs added.
- Deterministic, draft-only behavior; no refactor of REDESIM extraction logic.


