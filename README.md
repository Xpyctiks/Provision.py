# Provision.py

**Provision.py** is a web-based and CLI application for automated deployment and lifecycle management of multiple websites on Linux/Nginx server infrastructure. It handles Git/ZIP-based provisioning, Cloudflare DNS/SSL/Email-Routing automation, Nginx 301 redirects, and role-based multi-user access from a single dashboard.

Version: **2.8.1**

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [CLI Reference](#cli-reference)
- [Web Interface](#web-interface)
- [Admin Panel](#admin-panel)
- [User Management & Roles](#user-management--roles)
- [Site Provisioning & Cloning](#site-provisioning--cloning)
- [Cloudflare Integration](#cloudflare-integration)
- [Cloudflare Email Routing](#cloudflare-email-routing)
- [Redirects Management](#redirects-management)
- [DNS Validation](#dns-validation)
- [Site Visibility Restrictions](#site-visibility-restrictions)
- [Authelia SSO Integration](#authelia-sso-integration)
- [Telegram Notifications](#telegram-notifications)
- [Caching](#caching)
- [Periodic Sync Endpoints](#periodic-sync-endpoints)

---

## Features

- **Site provisioning** — deploy sites automatically from Git repositories (with automatic subdomain detection) or manually from ZIP archives
- **Web Archive import** — optionally pull a previously archived snapshot of a domain and unpack it into a newly provisioned site's `public/drop` folder
- **Site cloning** — duplicate an existing site into a single new domain or in bulk into a list of domains, keeping the clone/hreflang history
- **Site lifecycle** — enable, disable, delete (single or bulk) sites; pull latest Git changes (single or bulk, with automatic PHP migrations)
- **Automatic Cloudflare SSL & DNS on provisioning** — issues an origin certificate and creates/updates the required A records for every new site
- **Cloudflare domain management** — add/remove domains on a Cloudflare account, list domains, manage arbitrary DNS records (add/edit/delete, single or bulk across domains)
- **DNS validation** — per-domain CNAME record management for search-engine/ownership verification
- **Redirect management** — per-site 301 Nginx redirect manager, bulk redirect creation across many domains at once, CSV import, and a global redirects dashboard synced from disk to DB
- **Cloudflare Email Routing management** — enable/disable routing and manage forwarding rules per domain, bulk rule creation across domains, a global routing dashboard, and destination-address management (add/delete/resend verification)
- **robots.txt management** — view and edit robots.txt files per site
- **Site visibility restrictions** — site owners can hide/unhide their own sites from other users; admins can restrict any site to a specific list of users
- **Role-based access control** — Admin, Mail-Admin (view/manage email & redirects only, no site modification) and regular User roles
- **Authelia SSO integration** — hybrid login: works standalone with its own login form, or auto-logs-in users authenticated by an Authelia reverse-proxy via the `Remote-User` header
- **Telegram notifications** — async alerts for provisioning events, errors, and privilege-violation attempts
- **Real-time log viewer** — view application logs from the web UI, with a REST API for programmatic access
- **Response caching** — per-user page cache for the dashboard to keep large site lists fast
- **Broadcast messages** — admins can push a one-time message to every user, shown as a flash notice on next visit
- **Full CLI** — manage users, Git templates and core settings without the web UI

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | Flask, Flask-Login, Flask-SQLAlchemy, Flask-Caching |
| CLI | Click |
| Database | SQLite3 |
| Web server | Nginx |
| WSGI server | Gunicorn |
| PHP | PHP-FPM 8.2 |
| HTTP clients | httpx (async, Telegram), requests (sync, Cloudflare API / web archive) |
| External APIs | Cloudflare API (Zones, DNS, SSL, Email Routing), Telegram Bot API |
| SSO | Authelia (optional, via reverse-proxy `Remote-User` header) |
| Domain parsing | tldextract, idna |
| Certificates | `cryptography` (CSR/key generation for Cloudflare Origin CA) |
| Security | Werkzeug (password hashing), secure session cookies |

---

## Requirements

- Python 3.11+
- Nginx
- PHP-FPM 8.2 (optional, for PHP sites)
- Git
- A Linux server with `root` or `sudo` access

Install Python dependencies (there is no `requirements.txt` in the repo, so the packages need to be installed directly, or pinned into your own requirements file first):

```bash
pip install flask flask-login flask-sqlalchemy flask-caching click requests httpx idna tldextract cryptography gunicorn
```

---

## Installation

1. **Clone the repository:**

```bash
git clone <repo_url> /opt/Provision.py
cd /opt/Provision.py
```

2. **Install dependencies** (see [Requirements](#requirements)).

3. **Initialize the database and create the first admin user:**

```bash
python main.py user add admin "Admin Name" "yourpassword"
python main.py user setadmin admin
```

4. **Configure required paths:**

```bash
python main.py set webfolder /var/www/drops-sites/
python main.py set nginxpath /etc/nginx/
```

5. **Configure Telegram notifications (optional):**

```bash
python main.py set token <telegram_bot_token>
python main.py set chat <telegram_chat_id>
```

Everything else (Cloudflare accounts, servers, Git templates, domain ownership, mail-admin users, etc.) is managed afterwards through the **Admin Panel** in the web UI — see [Admin Panel](#admin-panel).

---

## Configuration

All settings are stored in the SQLite database at `/etc/provision/provision.db` (created automatically on first launch with sane defaults). They can be edited via the CLI (`python main.py set ...`, for the handful of values exposed there) or, more completely, via **Admin Panel → Налаштування**.

| Parameter | Description | Default |
|---|---|---|
| `telegramChat` | Telegram chat ID for notifications | (empty) |
| `telegramToken` | Telegram bot API token | (empty) |
| `logFile` | Application log file path | `/var/log/provision.log` |
| `sessionKey` | Flask session encryption key | (auto-generated) |
| `webFolder` | Root directory for websites | `/var/www/drops-sites/` |
| `nginxCrtPath` | Nginx SSL certificates directory | `/etc/nginx/ssl/` |
| `wwwUser` | Web server file ownership user | `www-data` |
| `wwwGroup` | Web server file ownership group | `www-data` |
| `nginxSitesPathAv` | Nginx `sites-available` directory | `/etc/nginx/sites-available-drops/` |
| `nginxSitesPathEn` | Nginx `sites-enabled` directory | `/etc/nginx/sites-enabled-drops/` |
| `nginxAddConfDir` | Nginx additional configs directory (redirect `301-*.conf` files live here) | `/etc/nginx/additional-configs` |
| `nginxPath` | Nginx main configuration directory | `/etc/nginx/` |
| `phpPool` | PHP-FPM pool.d directory | `/etc/php/8.2/fpm/pool.d/` |
| `phpFpmPath` | PHP-FPM executable path | `/usr/sbin/php-fpm8.2` |
| `autheliaLogoutUrl` | If set, `/logout/` redirects here instead of `/login/` (for Authelia SSO setups) | (empty) |
| `webArchiveApiUrl` | Base URL of a web-archive service; if set, provisioning can pull `<domain>.zip` from `<url>/<domain>.zip` | (empty) |

> **Note:** `functions/variables.py` keeps in-flight job state (`JOB_ID`, `JOB_COUNTER`, `CLONED_FROM`, ...) in plain module-level globals shared by every thread within a worker process. With `worker_class = "gthread"` and `threads > 1`, two clone/provision jobs that happen to land on threads of the *same* worker process at the same time can read/overwrite each other's job state. This hasn't been observed causing problems in practice, but if you start seeing jobs reported with the wrong domain/job ID in logs or Telegram notifications, this is the place to look.

---

## Running the Application

### Development

```bash
python main.py
```

### Production with Gunicorn

**1. Create `gunicorn_config.py` in the application directory** (a copy ready to adjust is included at the repo root - `gunicorn_config.py`):

```python
import sys
import os

# Update to your virtualenv or system Python path
venv_path = "/usr/local/"
sys.path.insert(0, os.path.join(venv_path, "lib/python3.11/site-packages"))
sys.path.insert(0, "/opt/Provision.py")

bind = "127.0.0.1:8880"
workers = 8
threads = 8
worker_class = "gthread"
timeout = 300
keepalive = 30
graceful_timeout = 30
backlog = 2048
loglevel = "info"
wsgi_app = "main:application"
```

**2. Create a systemd service file `gunicorn-provision.service`:**

```ini
[Unit]
Description=Gunicorn instance for provision.py
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/Provision.py
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/gunicorn -c /opt/Provision.py/gunicorn_config.py main:application
StandardOutput=append:/var/log/gunicorn/provision.log
StandardError=append:/var/log/gunicorn/provision-error.log

[Install]
WantedBy=multi-user.target
```

**3. Enable and start the service:**

```bash
ln -s /opt/Provision.py/gunicorn-provision.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable gunicorn-provision
systemctl start gunicorn-provision
```

---

## CLI Reference

The CLI is accessed via `python main.py <command>`. It only covers the subset of entities below — **Cloudflare accounts, servers, domain ownership, domain↔Cloudflare-account links, and the mail-admin role are managed exclusively through the [Admin Panel](#admin-panel)** web UI, not via CLI.

### User Management

```bash
python main.py user add <username> <realname> <password>
python main.py user del <username>
python main.py user setpwd <username> <password>
python main.py user setadmin <username>
python main.py user unsetadmin <username>
```

### Template Management

Git repository templates used for site provisioning.

```bash
python main.py templates add <name> <git_repo_url>
python main.py templates del <name>
python main.py templates upd <name> <new_repo_url>
python main.py templates default <name>
```

### System Settings

```bash
python main.py set chat <telegram_chat_id>
python main.py set token <telegram_bot_token>
python main.py set log <log_file_path>
python main.py set webfolder <web_root_path>
python main.py set nginxpath <nginx_config_path>
```

### Information Display

```bash
python main.py show users
python main.py show config
python main.py show templates
python main.py show cloudflare
python main.py show servers
python main.py show owners
python main.py show accounts
python main.py version
```

---

## Web Interface

The application listens on port `8880` by default (configurable in `gunicorn_config.py`).

### Main Pages

| Route | Description |
|---|---|
| `/` | Dashboard — list of all sites with status, Cloudflare/email-routing indicators and actions |
| `/login/` | Login page |
| `/login/authelia/` | Entry point for Authelia forward-auth SSO |
| `/logout/` | Logout (redirects to Authelia logout URL if configured) |
| `/provision/` | Provision a new site from a Git template (optionally seeded from a Web Archive) |
| `/upload/` | Deploy a site from a ZIP archive |
| `/clone/` | Clone an existing site to one domain or a bulk list of domains |
| `/action/` | Dispatcher: site enable/disable/delete, git pull, redirect deletion, apply changes, hide/unhide site |
| `/action/show/hrefhistory` | Returns the clone/hreflang history for a site (used by the dashboard accordion) |
| `/action/clear_cache/` | Manually clears the dashboard page cache |
| `/redirects_manager/` | Manage 301 Nginx redirects for a single site |
| `/redirects_bulk/` | Create the same 301 redirect across many domains of a Cloudflare account at once |
| `/redirects_dashboard/` | Global dashboard of all redirects across all domains |
| `/upload_redirects/` | Add a single redirect or bulk-import redirects from a CSV file for a site |
| `/cloudflare_domains/` | Add/remove domains on a Cloudflare account; manage DNS records (single & bulk) |
| `/cloudflare_email/manage` | Manage Email Routing (enable/disable, rules) for a single domain |
| `/cloudflare_email_bulk/` | Bulk-create Email Routing forwarding rules across many domains |
| `/cloudflare_email_dashboard/` | Global dashboard of Email Routing status/rules across all domains |
| `/cloudflare_email_dstaddresses/` | Manage Email Routing destination addresses for a Cloudflare account |
| `/dns_validation/` | Manage CNAME records for domain ownership/search-engine validation |
| `/robots.py` | View and edit `robots.txt` for a site |
| `/validate/` | Validates that a domain/subdomain's DNS points at the expected server |
| `/logs/` | View application logs |
| `/logs/api/` | REST API endpoint for log data |

### Admin Panel

Accessible only to users with the `admin` role.

| Route | Description |
|---|---|
| `/admin_panel/` | Redirects to Settings |
| `/admin_panel/settings/` | Edit all global settings (see [Configuration](#configuration)) |
| `/admin_panel/users/` | Create/delete users; promote/demote Admin, Mail-Admin, regular User roles |
| `/admin_panel/templates/` | Add/delete Git provisioning templates; set the default one |
| `/admin_panel/cloudflare/` | Add/delete Cloudflare accounts (token validated against the API on add); set the default one |
| `/admin_panel/owners/` | Assign/remove domain ownership; clear "cloned from" info |
| `/admin_panel/servers/` | Add/delete target servers by name+IP; set the default one |
| `/admin_panel/links/` | Link/unlink a domain to a Cloudflare account (used across the app to pick the right API token) |
| `/admin_panel/accounts/` | Link/unlink a Cloudflare account to the user(s) allowed to see it |
| `/admin_panel/restrictions/` | Restrict a site's dashboard visibility to a specific list of users |
| `/admin_panel/messages/` | Broadcast a one-time text message to all users, or clear the pending message queue |

---

## User Management & Roles

| Role | `rights` value | Access |
|---|---|---|
| Admin | `255` | Full access including Admin Panel |
| Mail-Admin | `50` | View-only access to sites; full access to redirects (manager/bulk/dashboard) and Cloudflare Email Routing (manage/bulk/dashboard/destination addresses) and DNS validation/logs; **blocked** from provisioning, cloning, uploading, robots.txt editing, and any site enable/disable/delete/git-pull/apply-changes action |
| Regular user | `1` | Site management, provisioning, cloning, Cloudflare tools |

- Users and roles are created/changed exclusively in **Admin Panel → Користувачі** (or the CLI `user` commands for basic add/admin toggling — the CLI has no mail-admin option).
- Sessions expire after **8 hours**.
- Passwords are hashed with Werkzeug's `generate_password_hash`.
- Failed login attempts and privilege-violation attempts are logged and sent to Telegram.
- Site owners can hide their own sites from other users (see [Site Visibility Restrictions](#site-visibility-restrictions)).

---

## Site Provisioning & Cloning

- **`/provision/`** deploys a new site from a Git template: it issues/validates the Cloudflare SSL certificate and A/www records, `git clone`s the template into the web root, and generates the Nginx config. Subdomains are auto-detected (via `tldextract`) so the certificate/DNS setup targets the correct root domain, unless "not a subdomain" is explicitly forced.
  - If a **Web Archive URL** is configured (`webArchiveApiUrl`) and a source domain is given, its archived ZIP is downloaded and unpacked into the new site's `public/drop` folder after provisioning.
- **`/upload/`** deploys one or more sites from uploaded ZIP archives (each must contain a `public/` folder); handles certificates/DNS the same way as Git provisioning.
- **`/clone/`** duplicates an existing site's files into a new domain (single) or a whole list of domains (bulk, one per line) — including certificate/DNS setup for each — and preserves clone lineage in the `Ownership.cloned` field and the site's `clones-history.json`.
- **`/action/`** handles enable/disable/delete (single or bulk with checkboxes) and Git pull (single or bulk, running `git stash`, `git pull`, resetting file ownership, and PHP `bin/migrate.php` if present).

---

## Cloudflare Integration

1. Add one or more Cloudflare accounts (email + API token) via **Admin Panel → Cloudflare**. The token is validated against the API before being stored.
2. Link individual domains to specific accounts via **Admin Panel → Лінки доменів**.
3. Use `/cloudflare_domains/` to add/remove a domain on the account and manage arbitrary DNS records for it (A/AAAA/CNAME/MX/etc.), either one record on one domain or one record pushed to several selected domains at once.
4. Use `/dns_validation/` to add/remove CNAME records used for domain ownership verification (e.g. Google Search Console).
5. `/validate/` checks that a domain's (or its detected subdomain's root) A records match the IP of the selected target server.

---

## Cloudflare Email Routing

- **`/cloudflare_email/manage`** — per-domain page to enable/disable Cloudflare Email Routing and add/delete forwarding rules, reading live from the Cloudflare API and keeping `CloudflareEmailsStatus`/`CloudflareEmailsRules` in the local DB in sync.
- **`/cloudflare_email_bulk/`** — creates the same `<login>@<domain> → destination` forwarding rule across many domains of a Cloudflare account at once, auto-enabling routing per domain if it's off.
- **`/cloudflare_email_dashboard/`** — read-only overview of routing status and rules for every domain known to the system.
- **`/cloudflare_email_dstaddresses/`** — add, delete, or resend the verification email for Email Routing destination addresses on a Cloudflare account (Cloudflare has no native "resend" endpoint, so this deletes and re-adds the address).

---

## Redirects Management

- **`/redirects_manager/`** — per-site view/add/delete of 301 redirects stored as Nginx `location` blocks in `301-<domain>.conf`; changes are staged until **Apply changes** reloads Nginx.
- **`/redirects_bulk/`** — creates the same redirect rule across every selected domain of a Cloudflare account in one go.
- **`/upload_redirects/`** — adds a single redirect, or bulk-imports a `from,to` CSV file, to one site's redirect config.
- **`/redirects_dashboard/`** — read-only overview of every redirect on every domain, parsed from the `301-*.conf` files into the `RedirectsRules` table.

---

## DNS Validation

`/dns_validation/` looks up the Cloudflare zone for a domain (via its linked account) and lets you add or remove CNAME records used to verify domain ownership with search engines or other third-party services.

---

## Site Visibility Restrictions

- **Per-owner hide/unhide**: on the dashboard, a site's owner can click 👁️/🙈 to hide the site from every other user (adds/removes a `SitesShowRestricions` row scoped to just themselves).
- **Admin-wide restrictions**: **Admin Panel → Обмеження показу** lets an admin restrict any site's dashboard visibility to an explicit comma-separated list of real names, regardless of ownership.

---

## Authelia SSO Integration

The app supports two coexisting login paths:

- **Standalone** — the normal `/login/` form with local username/password.
- **Authelia forward-auth (hybrid)** — if a reverse proxy enforces Authelia authentication and forwards a `Remote-User` header, `try_authelia_login()` (`functions/authelia_auth.py`) runs on every request and auto-logs-in the matching local user. If the header names a user that doesn't exist locally, access is denied with a warning. Configure `autheliaLogoutUrl` so `/logout/` redirects back through Authelia's own logout instead of the local login page.

---

## Telegram Notifications

The application sends async notifications via a Telegram Bot for:

- Site provisioning / cloning / upload started, completed, or failed
- Critical errors (missing config variables, failed API calls, etc.)
- Failed login attempts
- Attempts by a mail-admin (or non-privileged user) to access an action they're not allowed to perform

**Setup:**

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token.
2. Get the chat ID of the target chat or group.
3. Configure:

```bash
python main.py set token <bot_token>
python main.py set chat <chat_id>
```

---

## Caching

The dashboard (`/`) response is cached per-user (`flask-caching`, filesystem backend, 300s TTL) to keep large site lists fast. The cache is invalidated automatically after any action that changes the site list or its state, and can also be cleared manually from `/action/clear_cache/`.

---

## Periodic Sync Endpoints

Two unauthenticated GET endpoints are meant to be triggered by an external cron job (they re-read live state and refresh the local DB cache used by the dashboards):

| Route | Purpose |
|---|---|
| `/redirects_dashboard/update_redirects_status` | Re-parses every `301-*.conf` file and refreshes the `RedirectsRules` table |
| `/cloudflare_email/update_emails_status` | Re-queries Cloudflare Email Routing status/rules for every locally-hosted domain and refreshes `CloudflareEmailsStatus`/`CloudflareEmailsRules` |
