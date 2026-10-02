import logging
from flask import render_template,request,redirect,flash,Blueprint,jsonify,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare,DomainRegistrator
from functions.site_actions import is_admin,is_mail_admin
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.cloudflare_ns_func import parse_ns
from functions.domain_purchase_func import DOMAIN_RE,_set_ns
from functions.dynadot_func import dynadot_list_domains
from functions.spaceship_func import spaceship_list_domains

domain_registrators_bp = Blueprint("domain_registrators", __name__)

#Spaceship accepts 2..12 custom hosts, Dynadot up to 13 - the common safe range
NS_MIN = 2
NS_MAX = 12

def _list_domains(registrator: DomainRegistrator):
  """Dispatches the domain listing to the correct API based on registrator.provider."""
  if registrator.provider == "spaceship":
    return spaceship_list_domains(registrator)
  return dynadot_list_domains(registrator)

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
  """GET request (AJAX): returns all domains of the given registrator account as JSON"""
  try:
    name = (request.args.get("registrator") or "").strip()
    registrator = DomainRegistrator.query.filter_by(name=name).first()
    if not registrator:
      return jsonify({"error": f"Реєстратор {name} не знайдено в базі"}), 404
    logging.info(f"get_registrator_domains(): Loading domains of registrator {name} by {current_user.realname}")
    ok, domains_or_err = _list_domains(registrator)
    if not ok:
      return jsonify({"error": f"Помилка API реєстратора: {domains_or_err}"}), 502
    return jsonify({"domains": domains_or_err})
  except Exception as err:
    logging.error(f"get_registrator_domains(): general error by {current_user.realname}: {err}")
    return jsonify({"error": str(err)}), 500

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
