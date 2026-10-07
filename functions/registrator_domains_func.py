import logging
import threading
from datetime import datetime
from sqlalchemy import func
from db.db import db
from db.database import DomainRegistrator, RegistratorDomain
from functions.dynadot_func import dynadot_list_domains
from functions.spaceship_func import spaceship_list_domains

#registrator names whose sync is currently running in a background thread (guarded by _running_lock),
#so a second request for the same registrator (cron + page button) doesn't start a parallel sync
_running = set()
_running_lock = threading.Lock()

def list_domains_from_api(registrator: DomainRegistrator):
  """Dispatches the (slow) full domain listing to the correct API based on registrator.provider.
  Returns (True, [ {name, ns, created, status}, ... ]) or (False, error)."""
  if registrator.provider == "spaceship":
    return spaceship_list_domains(registrator)
  return dynadot_list_domains(registrator)

def _parse_date(value: str):
  """'YYYY-MM-DD HH:MM' (as returned by *_list_domains) -> datetime, or None."""
  try:
    return datetime.strptime(value, "%Y-%m-%d %H:%M") if value else None
  except Exception:
    return None

def _ns_to_str(ns_list) -> str:
  return ",".join(str(n).strip().lower() for n in (ns_list or []) if str(n).strip())

def row_to_dict(row: RegistratorDomain) -> dict:
  """Same shape as *_list_domains() items - the page's JS works with this."""
  return {
    "name": row.domain,
    "ns": [n for n in (row.ns_servers or "").split(",") if n],
    "created": row.registered.strftime("%Y-%m-%d %H:%M") if row.registered else "",
    "status": row.status or "-"
  }

def load_domains_from_db(registrator_name: str) -> list:
  rows = RegistratorDomain.query.filter_by(registrator=registrator_name).order_by(RegistratorDomain.domain).all()
  return [row_to_dict(r) for r in rows]

def last_sync_time(registrator_name: str):
  """Time of the last successful sync for the registrator (max RegistratorDomain.synced), or None."""
  return db.session.query(func.max(RegistratorDomain.synced)).filter(RegistratorDomain.registrator == registrator_name).scalar()

def sync_registrator(registrator: DomainRegistrator) -> dict:
  """Full sync of one registrator account with the DB: new domains are added, NS/date/status updated,
  domains no longer present at the registrator are deleted. Nothing is touched if the API call fails."""
  name = registrator.name
  logging.info(f"sync_registrator(): -----------------------Starting domains sync for registrator {name}-----------------------")
  ok, domains_or_err = list_domains_from_api(registrator)
  if not ok:
    logging.error(f"sync_registrator(): API error for registrator {name}, DB left untouched: {domains_or_err}")
    return {"registrator": name, "ok": False, "error": str(domains_or_err)}
  api_domains = {d["name"]: d for d in domains_or_err if d.get("name")}
  existing = {r.domain: r for r in RegistratorDomain.query.filter_by(registrator=name).all()}
  #safety net: an "empty" answer while we know about domains is far more likely an API hiccup than a wiped account
  if not api_domains and existing:
    logging.error(f"sync_registrator(): registrator {name} API returned 0 domains while DB has {len(existing)} - deletion skipped, check the account manually")
    return {"registrator": name, "ok": False, "error": "API повернув 0 доменів, а в базі вони є - синхронізацію пропущено"}
  added = updated = deleted = 0
  try:
    for domain, d in api_domains.items():
      ns = _ns_to_str(d.get("ns"))
      registered = _parse_date(d.get("created", ""))
      status = (d.get("status") or "")[:256]
      row = existing.get(domain)
      if row is None:
        db.session.add(RegistratorDomain(registrator=name, domain=domain, ns_servers=ns, registered=registered, status=status))
        added += 1
      elif row.ns_servers != ns or row.registered != registered or row.status != status:
        row.ns_servers, row.registered, row.status = ns, registered, status
        updated += 1
    for domain, row in existing.items():
      if domain not in api_domains:
        db.session.delete(row)
        deleted += 1
    db.session.flush()
    #mark every row of this registrator as freshly synced (one UPDATE) - used to show "last sync" on the page
    RegistratorDomain.query.filter_by(registrator=name).update({RegistratorDomain.synced: datetime.now()}, synchronize_session=False)
    db.session.commit()
  except Exception as err:
    db.session.rollback()
    logging.error(f"sync_registrator(): DB error for registrator {name}: {err}")
    return {"registrator": name, "ok": False, "error": str(err)}
  logging.info(f"sync_registrator(): -----------------------Registrator {name} synced: {len(api_domains)} domains total, added {added}, updated {updated}, deleted {deleted}-----------------------")
  return {"registrator": name, "ok": True, "total": len(api_domains), "added": added, "updated": updated, "deleted": deleted}

def is_sync_running(registrator_name: str) -> bool:
  with _running_lock:
    return registrator_name in _running

def start_background_sync(app, registrator_names: list) -> tuple:
  """Starts one background thread syncing the given registrators one after another. Registrators whose sync
  is already running are skipped. Returns (started_names, already_running_names)."""
  with _running_lock:
    started = [n for n in registrator_names if n not in _running]
    skipped = [n for n in registrator_names if n in _running]
    _running.update(started)
  if started:
    threading.Thread(target=_sync_worker, args=(app, started), daemon=True).start()
  return started, skipped

def _sync_worker(app, registrator_names: list) -> None:
  with app.app_context():
    for name in registrator_names:
      try:
        registrator = DomainRegistrator.query.filter_by(name=name).first()
        if registrator:
          sync_registrator(registrator)
        else:
          logging.error(f"_sync_worker(): registrator {name} not found in DB")
      except Exception as err:
        db.session.rollback()
        logging.error(f"_sync_worker(): error syncing registrator {name}: {err}")
      finally:
        with _running_lock:
          _running.discard(name)

def upsert_registrator_domain(registrator_name: str, domain: str, ns_list=None, status: str = None, registered=None) -> None:
  """Best-effort: adds/updates one domain row right away (after purchase / NS change) without a full sync.
  Only the given fields are changed on an existing row."""
  try:
    row = RegistratorDomain.query.filter_by(registrator=registrator_name, domain=domain).first()
    if row is None:
      row = RegistratorDomain(registrator=registrator_name, domain=domain, ns_servers="", status="", registered=registered)
      db.session.add(row)
    if ns_list is not None:
      row.ns_servers = _ns_to_str(ns_list)
    if status is not None:
      row.status = status
    if registered is not None:
      row.registered = registered
    db.session.commit()
  except Exception as err:
    db.session.rollback()
    logging.error(f"upsert_registrator_domain(): error for {domain} ({registrator_name}): {err}")
