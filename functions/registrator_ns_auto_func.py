import logging
import random
import threading
import uuid
from datetime import datetime
from flask_login import login_user
from db.db import db
from db.database import Cloudflare, DomainRegistrator, User
from functions.domain_purchase_func import (
  _add_domain_to_cf, _set_ns, get_purchase_row, append_purchase_message, CF_ACCOUNT_DOMAIN_LIMIT
)
from functions.pages_forms import _load_zones_for_account
from functions.cloudflare_ns_func import save_account_ns_if_empty
from functions.site_actions import link_domain_and_account
from functions.email_routing_status_func import seed_email_routing_domain_status
from functions.provision_func import setSiteOwner

#"Автоматичні NS операції" on /domain_registrators/: selected registrator domains are split into batches of
#BATCH_SIZE, every batch goes to a randomly chosen Cloudflare account, each domain is added there as a new zone
#and the NS servers Cloudflare returns for it are set at the registrator right away.
BATCH_SIZE = 50

_jobs = {}                       # job_id -> job state dict (see _new_job)
_jobs_lock = threading.Lock()
_active_job = {"id": None}       # only one job at a time - parallel jobs would race for the same free CF slots

def plan_batches(domains: list, accounts: list, free_slots: dict):
  """Splits domains into batches of BATCH_SIZE and assigns every batch to a random account that still has enough
  free zone slots - accounts not used yet are preferred, so with enough accounts every batch lands on its own
  account. Returns (plan, error): plan = [(Cloudflare, [domains...]), ...]."""
  batches = [domains[i:i + BATCH_SIZE] for i in range(0, len(domains), BATCH_SIZE)]
  remaining = dict(free_slots)
  used = set()
  plan = []
  for batch in batches:
    candidates = [a for a in accounts if remaining.get(a.account, 0) >= len(batch)]
    if not candidates:
      total_free = sum(remaining.values())
      return None, (f"Недостатньо вільних місць на обраних аккаунтах Cloudflare: не вдалося розмістити групу з {len(batch)} доменів "
                    f"(залишилось вільних місць: {total_free}, по аккаунтах: " + ", ".join(f"{k}: {v}" for k, v in remaining.items()) + "). "
                    f"Оберіть більше аккаунтів або менше доменів.")
    fresh = [a for a in candidates if a.account not in used]
    acc = random.choice(fresh or candidates)
    used.add(acc.account)
    remaining[acc.account] -= len(batch)
    plan.append((acc, batch))
  return plan, None

def _new_job(registrator_name: str, plan: list, realname: str) -> dict:
  return {
    "id": uuid.uuid4().hex,
    "registrator": registrator_name,
    "status": "running",
    "started_by": realname,
    "started": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "plan": [{"account": acc.account, "count": len(batch)} for acc, batch in plan],
    "total": sum(len(batch) for _, batch in plan),
    "processed": 0,
    "ok": 0,
    "failed": 0,
    "results": [],     # [{domain, account, ok, message, ns}]
    "error": ""
  }

def start_auto_ns_job(app, registrator: DomainRegistrator, domains: list, accounts: list, user_id: int, realname: str):
  """Validates, plans and starts the background job. Returns (job_dict, error)."""
  with _jobs_lock:
    if _active_job["id"] and _jobs.get(_active_job["id"], {}).get("status") == "running":
      return None, "Інша автоматична NS операція вже виконується - дочекайтесь її завершення."
  #the live zone list of every selected account (one listing per account) - used both for the free-slot count and to
  #skip domains that really are on one of these accounts already. The local Domain_account table is NOT used for this:
  #it's only a "last known" link and stays behind when a zone is deleted on Cloudflare, so it can't be trusted here.
  #A domain sitting on some other, not selected account is simply refused by Cloudflare and reported per domain.
  zones_by_account = {acc.account: _load_zones_for_account(acc) for acc in accounts}
  present = {}
  for acc_name, zones in zones_by_account.items():
    for zone_name in zones:
      present.setdefault(zone_name, acc_name)
  todo = [d for d in domains if d not in present]
  skipped = [{"domain": d, "account": present[d], "ok": False, "ns": [], "message": f"Вже є на аккаунті Cloudflare {present[d]}, пропущено"} for d in domains if d in present]
  if not todo:
    return None, "Усі обрані домени вже є на обраних аккаунтах Cloudflare - нічого додавати."
  random.shuffle(todo)
  free_slots = {name: max(0, CF_ACCOUNT_DOMAIN_LIMIT - len(zones)) for name, zones in zones_by_account.items()}
  plan, err = plan_batches(todo, accounts, free_slots)
  if err:
    return None, err
  job = _new_job(registrator.name, plan, realname)
  job["total"] += len(skipped)
  job["processed"] = len(skipped)
  job["failed"] = len(skipped)
  job["results"].extend(skipped)
  with _jobs_lock:
    _jobs[job["id"]] = job
    _active_job["id"] = job["id"]
  logging.info(f"-----------------------Auto NS job {job['id']} started by {realname} for registrator {registrator.name}: "
               f"{len(todo)} domain(s) to add, {len(skipped)} skipped, plan: {job['plan']}-----------------------")
  plan_ids = [(acc.id, batch) for acc, batch in plan]
  threading.Thread(target=_worker, args=(app, job, registrator.id, plan_ids, user_id), daemon=True).start()
  return job, None

def get_job(job_id: str):
  with _jobs_lock:
    job = _jobs.get(job_id)
    return dict(job, results=list(job["results"])) if job else None

def _record(job: dict, domain: str, account: str, ok: bool, message: str, ns=None):
  with _jobs_lock:
    job["results"].append({"domain": domain, "account": account, "ok": ok, "message": message, "ns": ns or []})
    job["processed"] += 1
    job["ok" if ok else "failed"] += 1

def _worker(app, job: dict, registrator_id: int, plan_ids: list, user_id: int):
  #a request context with the initiating user logged in - setSiteOwner()/link_domain_and_account() rely on current_user
  with app.app_context(), app.test_request_context():
    try:
      user = db.session.get(User, user_id)
      if user:
        login_user(user)
      registrator = db.session.get(DomainRegistrator, registrator_id)
      for acc_id, batch in plan_ids:
        acc = db.session.get(Cloudflare, acc_id)
        for domain in batch:
          _process_domain(job, registrator, acc, domain)
      with _jobs_lock:
        job["status"] = "done"
    except Exception as err:
      db.session.rollback()
      logging.error(f"auto_ns _worker(): job {job['id']} aborted: {err}")
      with _jobs_lock:
        job["status"] = "error"
        job["error"] = str(err)
    finally:
      logging.info(f"-----------------------Auto NS job {job['id']} finished: {job['ok']} ok, {job['failed']} failed of {job['total']}-----------------------")

def _process_domain(job: dict, registrator: DomainRegistrator, acc: Cloudflare, domain: str):
  try:
    ok, ns_or_err = _add_domain_to_cf(acc, domain)
    if not ok:
      logging.error(f"auto_ns: failed to add {domain} to CF account {acc.account}: {ns_or_err}")
      _record(job, domain, acc.account, False, f"Помилка додавання в Cloudflare: {ns_or_err}")
      return
    ns = ns_or_err
    #the zone exists on Cloudflare now - register it in our DB regardless of the NS result, same as the purchase pipeline does
    save_account_ns_if_empty(acc, ns)
    setSiteOwner(domain)
    link_domain_and_account(domain, acc.account)
    seed_email_routing_domain_status(domain, acc.account)
    #_set_ns() also updates the RegistratorDomain cache on success
    ns_ok, ns_msg = _set_ns(registrator, domain, ns)
    purchase_row = get_purchase_row(domain)
    if purchase_row and purchase_row.stage == "just_bought":
      purchase_row.cloudflare_account = acc.account
      if ns_ok:
        purchase_row.status = "success"
        append_purchase_message(purchase_row, "Додано в Cloudflare та встановлено NS (автоматичні NS операції)", stage="ns_set")
      else:
        db.session.commit()
    if ns_ok:
      logging.info(f"auto_ns: {domain} added to CF account {acc.account}, NS {ns} set via {registrator.name}")
      _record(job, domain, acc.account, True, f"Додано в Cloudflare, NS {', '.join(ns)} встановлено", ns)
    else:
      logging.error(f"auto_ns: {domain} added to CF account {acc.account}, but NS {ns} set failed: {ns_msg}")
      _record(job, domain, acc.account, False, f"Додано в Cloudflare, але NS {', '.join(ns)} НЕ встановлено: {ns_msg}", ns)
  except Exception as err:
    db.session.rollback()
    logging.error(f"auto_ns: unexpected error for {domain}: {err}")
    _record(job, domain, acc.account, False, f"Неочікувана помилка: {err}")
