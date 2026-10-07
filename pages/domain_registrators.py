import logging
from flask import render_template,request,redirect,flash,Blueprint,jsonify,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare,DomainRegistrator
from functions.site_actions import is_admin,is_mail_admin
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.cloudflare_ns_func import parse_ns
from functions.domain_purchase_func import DOMAIN_RE,_set_ns
from functions.registrator_domains_func import load_domains_from_db,last_sync_time,is_sync_running,start_background_sync

domain_registrators_bp = Blueprint("domain_registrators", __name__)

#Spaceship accepts 2..12 custom hosts, Dynadot up to 13 - the common safe range
NS_MIN = 2
NS_MAX = 12

def _cf_ns_options() -> list:
  """NS pairs stored for Cloudflare accounts (Cloudflare.ns_servers) - offered as checkboxes in the "change NS" window."""
  options = []
  for acc in Cloudflare.query.order_by(Cloudflare.account).all():
    ns = parse_ns(acc.ns_servers)
    if ns:
      options.append({"account": acc.account, "ns": ns})
  return options

@domain_registrators_bp.route("/domain_registrators/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_domain_registrators():
  """GET request: shows the registrators page - registrator picker; the domains table itself is loaded via AJAX"""
  try:
    registrators = DomainRegistrator.query.order_by(DomainRegistrator.name).all()
    reg_options = "".join(f'<option value="{r.name}">{r.name} ({r.provider})</option>' for r in registrators)
    return render_template("template-domain_registrators.html",reg_options=reg_options,cf_ns_options=_cf_ns_options(),admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_domain_registrators(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці роботи з реєстраторами, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@domain_registrators_bp.route("/domain_registrators/domains/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def get_registrator_domains():
  """GET request (AJAX): returns all domains of the given registrator account as JSON - from the local
  RegistratorDomain cache (fast), not from the registrator API. See sync routes below for refreshing it."""
  try:
    name = (request.args.get("registrator") or "").strip()
    registrator = DomainRegistrator.query.filter_by(name=name).first()
    if not registrator:
      return jsonify({"error": f"Реєстратор {name} не знайдено в базі"}), 404
    last_sync = last_sync_time(name)
    return jsonify({
      "domains": load_domains_from_db(name),
      "last_sync": last_sync.strftime("%d.%m.%Y %H:%M") if last_sync else "",
      "sync_running": is_sync_running(name)
    })
  except Exception as err:
    logging.error(f"get_registrator_domains(): general error by {current_user.realname}: {err}")
    return jsonify({"error": str(err)}), 500

@domain_registrators_bp.route("/domain_registrators/sync/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def sync_one_registrator():
  """POST request (AJAX, form/JSON field "registrator"): starts a background sync of one registrator with the DB.
  The page then polls /domain_registrators/domains/ (sync_running flag) and reloads the table when it's done."""
  try:
    data = request.get_json(silent=True) or request.form
    name = (data.get("registrator") or "").strip()
    if not DomainRegistrator.query.filter_by(name=name).first():
      return jsonify({"error": f"Реєстратор {name} не знайдено в базі"}), 404
    started, skipped = start_background_sync(current_app._get_current_object(), [name])
    logging.info(f"sync_one_registrator(): sync of registrator {name} requested by {current_user.realname}: {'started' if started else 'already running'}")
    return jsonify({"status": "started" if started else "already running"})
  except Exception as err:
    logging.error(f"sync_one_registrator(): general error by {current_user.realname}: {err}")
    return jsonify({"error": str(err)}), 500

@domain_registrators_bp.route("/domain_registrators/sync_all/", methods=['GET'])
def sync_all_registrators():
  """GET request: starts a background sync of ALL registrators in DB with the RegistratorDomain table (new domains are
  added, NS/dates/statuses updated, domains missing at the registrator deleted). Answers immediately - the sync can take
  long. Meant to be triggered periodically by a cron job (same as /cloudflare_email/update_emails_status)."""
  try:
    names = [r.name for r in DomainRegistrator.query.order_by(DomainRegistrator.name).all()]
    started, skipped = start_background_sync(current_app._get_current_object(), names)
    logging.info(f"sync_all_registrators(): registrators sync started for {started}, already running: {skipped}")
    return jsonify({"status": "started", "started": started, "already_running": skipped}), 200
  except Exception as err:
    logging.error(f"sync_all_registrators(): Global error: {err}")
    return jsonify({"status": "error", "message": str(err)}), 500

@domain_registrators_bp.route("/domain_registrators/set_ns/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def set_registrator_ns():
  """POST request (AJAX, JSON body {registrator, domains: [...], ns: [...]}): sets the given NS servers for every
  selected domain via the registrator's API. Returns per-domain results as JSON."""
  try:
    data = request.get_json(silent=True) or {}
    name = (data.get("registrator") or "").strip()
    domains = [str(d).strip().lower() for d in (data.get("domains") or []) if str(d).strip()]
    ns = parse_ns(",".join(str(n) for n in (data.get("ns") or [])))
    registrator = DomainRegistrator.query.filter_by(name=name).first()
    if not registrator:
      return jsonify({"error": f"Реєстратор {name} не знайдено в базі"}), 404
    if not domains:
      return jsonify({"error": "Не обрано жодного домену"}), 400
    if not NS_MIN <= len(ns) <= NS_MAX:
      return jsonify({"error": f"Потрібно вказати від {NS_MIN} до {NS_MAX} NS серверів, отримано {len(ns)}"}), 400
    bad_ns = [n for n in ns if not DOMAIN_RE.fullmatch(n)]
    if bad_ns:
      return jsonify({"error": f"Некоректні NS сервери: {', '.join(bad_ns)}"}), 400
    logging.info(f"-----------------------Setting NS {ns} for {len(domains)} domain(s) via registrator {name} by {current_user.realname}: {domains}-----------------------")
    results = []
    for domain in domains:
      if not DOMAIN_RE.fullmatch(domain):
        results.append({"domain": domain, "ok": False, "message": "Некоректне ім'я домену"})
        continue
      ok, msg = _set_ns(registrator, domain, ns)
      results.append({"domain": domain, "ok": ok, "message": "NS встановлено" if ok else str(msg)})
    ok_count = sum(1 for r in results if r["ok"])
    logging.info(f"set_registrator_ns(): NS set for {ok_count} of {len(results)} domain(s) via {name} by {current_user.realname}")
    return jsonify({"results": results, "ok_count": ok_count, "total": len(results), "ns": ns})
  except Exception as err:
    logging.error(f"set_registrator_ns(): general error by {current_user.realname}: {err}")
    return jsonify({"error": str(err)}), 500
