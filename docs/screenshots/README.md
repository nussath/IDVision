# IDVision — UI screenshots

Captures of each working section of the dashboard. Used in the project report
and the main README.

## Current captures

| File | What it shows |
|------|---------------|
| `admin_panel.png` | `/admin` — Retrain + Email notifications + User management cards |
| `admin_test_email_dispatched.png` | `/admin` after clicking **Send test email** |
| `admin_smtp_auth_error.png` | `/admin` surfacing a real SMTP `BadCredentials` error |
| `email_received_in_gmail.png` | The resulting test message arriving in the inbox |

## Still to capture

Save 1280-wide PNGs into this folder with the names below, then commit:

- `home.png` — anonymous landing page at `/`
- `login.png` — login form with an error flash (try a wrong password)
- `dashboard.png` — `/dashboard` with the stats panel and recent detections
- `camera_running.png` — `/camera` with the live feed visible
- `camera_stopped.png` — `/camera` after clicking **Stop camera**
- `criminals.png` — `/criminals` with the add form and a non-empty table
- `missing.png` — `/missing` likewise
- `alerts.png` — `/alerts` with at least one row that has a snapshot thumbnail
- `snapshot_full.png` — a snapshot opened full-size in a new tab
- `register_bootstrap.png` — `/register` in bootstrap mode (no admin yet)
- `register_admin.png` — `/register` in admin mode
- `alert_email.png` — a real detection email (subject, body, attached snapshot)
