# Provision.py

**Provision.py** is a web-based and CLI application for automated deployment and lifecycle management of multiple websites on Linux/Nginx server infrastructure.

Version: **2.5.1**

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
- [User Management & Roles](#user-management--roles)
- [Cloudflare Integration](#cloudflare-integration)
- [Telegram Notifications](#telegram-notifications)

---

## Features

- **Site provisioning** — deploy sites automatically from Git repositories or manually from ZIP archives
- **Site cloning** — duplicate an existing site with the same configuration
- **Site lifecycle** — enable, disable, delete sites; pull latest Git changes
- **Redirect management** — create and manage Nginx 301 redirects with regex support
- **robots.txt management** — upload and track robots.txt files per site
- **Cloudflare integration** — add domains to Cloudflare accounts, manage DNS CNAME records
- **Multi-account support** — store multiple Cloudflare accounts and target servers
- **Role-based access control** — admin and regular user roles
- **Telegram notifications** — async alerts for provisioning events and errors
- **Real-time log viewer** — view application logs from the web UI
- **REST log API** — programmatic access to log data
- **Full CLI** — manage all settings and entities without the web UI

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | Flask, Flask-Login, Flask-SQLAlchemy |
| CLI | Click |
| Database | SQLite3 |
| Web server | Nginx |
| WSGI server | Gunicorn |
| PHP | PHP-FPM 8.2 |
| HTTP clients | httpx (async), requests |
| External APIs | Cloudflare API, Telegram Bot API |
| Security | Werkzeug (password hashing), secure session cookies |

---

## Requirements

- Python 3.11+
- Nginx
- PHP-FPM 8.2 (optional, for PHP sites)
- Git
- A Linux server with `root` or `sudo` access

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Installation

1. **Clone the repository:**

```bash
git clone <repo_url> /opt/Provision.py
cd /opt/Provision.py
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

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

---

## Configuration

All settings are stored in the SQLite database at `/etc/provision/provision.db`.

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
| `nginxAddConfDir` | Nginx additional configs directory | `/etc/nginx/additional-configs` |
| `nginxPath` | Nginx main configuration directory | `/etc/nginx/` |
| `phpPool` | PHP-FPM pool.d directory | `/etc/php/8.2/fpm/pool.d/` |
| `phpFpmPath` | PHP-FPM executable path | `/usr/sbin/php-fpm8.2` |

Settings can be changed via the CLI (`python main.py set`) or the Admin Panel web interface.

---

## Running the Application

### Development

```bash
python main.py
```

### Production with Gunicorn

**1. Create `gunicorn_config.py` in the application directory:**

```python
import sys
import os

# Update to your virtualenv or system Python path
venv_path = "/usr/local/"
sys.path.insert(0, os.path.join(venv_path, "lib/python3.11/site-packages"))
sys.path.insert(0, "/opt/Provision.py")

bind = "0.0.0.0:8880"
workers = 1
timeout = 30
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

The CLI is accessed via `python main.py <command>`.

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

### Cloudflare Accounts

```bash
python main.py cloudflare add <email> <api_token>
python main.py cloudflare del <email>
python main.py cloudflare upd <email> <new_token>
python main.py cloudflare default <email>
```

### Server Management

```bash
python main.py servers add <server_name> <IP_address>
python main.py servers del <server_name>
python main.py servers upd <server_name> <new_IP>
python main.py servers default <server_name>
```

### Domain Ownership

```bash
python main.py owner add <domain> <user_id>
python main.py owner del <domain>
python main.py owner upd <domain> <new_user_id>
```

### Domain–Cloudflare Account Linking

```bash
python main.py account add <domain> <cloudflare_email>
python main.py account del <domain>
python main.py account upd <domain> <new_email>
python main.py account upload <file_path>   # bulk import from file
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
| `/` | Dashboard — list of all sites with status and actions |
| `/login/` | Login page |
| `/logout/` | Logout |
| `/provision/` | Provision a new site from a Git template |
| `/upload/` | Deploy a site from a ZIP archive |
| `/clone/` | Clone an existing site |
| `/action/` | Perform site actions (enable / disable / delete / git pull) |
| `/action/showstructure/` | Browse site directory structure |
| `/redirects_manager/` | Manage 301 Nginx redirects |
| `/cloudflare_domains/` | Add domains to Cloudflare |
| `/dns_validation/` | Manage DNS CNAME validation records |
| `/robots.py` | Upload and manage robots.txt files |
| `/validate/` | Domain validation |
| `/logs/` | View application logs |
| `/logs/api/` | REST API endpoint for log data |

### Admin Panel

Accessible only to users with `admin` role.

| Route | Description |
|---|---|
| `/admin_panel/` | Admin overview |
| `/admin_panel/settings/` | System settings |
| `/admin_panel/users/` | User management |
| `/admin_panel/templates/` | Git template management |
| `/admin_panel/cloudflare/` | Cloudflare account management |
| `/admin_panel/owners/` | Domain ownership |
| `/admin_panel/servers/` | Server configuration |
| `/admin_panel/links/` | Domain–account linking |
| `/admin_panel/accounts/` | Domain account associations |
| `/admin_panel/messages/` | Send messages to users |

---

## User Management & Roles

| Role | `rights` value | Access |
|---|---|---|
| Admin | `255` | Full access including Admin Panel |
| Regular user | `1` | Site management, provisioning, Cloudflare tools |

- Sessions expire after **8 hours**.
- Passwords are hashed with Werkzeug's `generate_password_hash`.
- Failed login attempts are logged.

---

## Cloudflare Integration

1. Add one or more Cloudflare accounts (email + API token):

```bash
python main.py cloudflare add user@example.com your_api_token
python main.py cloudflare default user@example.com
```

2. Link individual domains to specific accounts:

```bash
python main.py account add example.com user@example.com
```

3. Use the `/cloudflare_domains/` page to add a domain to the linked Cloudflare account.
4. Use `/dns_validation/` to add CNAME records for domain ownership verification.

---

## Telegram Notifications

The application sends async notifications via a Telegram Bot for:

- Site provisioning started / completed / failed
- Critical errors
- Login attempts

**Setup:**

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token.
2. Get the chat ID of the target chat or group.
3. Configure:

```bash
python main.py set token <bot_token>
python main.py set chat <chat_id>
```
