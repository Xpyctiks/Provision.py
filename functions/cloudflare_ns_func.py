import logging
from db.db import db
from db.database import Cloudflare

def parse_ns(raw: str) -> list:
  """Splits a comma-separated NS servers string (as stored in Cloudflare.ns_servers) into a clean, deduplicated list."""
  result = []
  for ns in (raw or "").split(","):
    ns = ns.strip().lower().rstrip(".")
    if ns and ns not in result:
      result.append(ns)
  return result

def format_ns(ns_list: list) -> str:
  """Joins a list of NS servers into the comma-separated form stored in Cloudflare.ns_servers."""
  return ",".join(parse_ns(",".join(ns_list or [])))

def ns_from_zones(zones: list) -> list:
  """Takes NS servers from the first zone of a Cloudflare /zones API result list that has them assigned
  (all zones of one account share the same NS pair). Returns [] if there is no such zone."""
  for zone in zones or []:
    if zone.get("name_servers"):
      return parse_ns(",".join(zone["name_servers"]))
  return []

def save_account_ns_if_empty(acc: Cloudflare, ns_list: list) -> None:
  """Best-effort: stores NS servers for the account if it doesn't have them yet (e.g. account had no zones
  at the moment it was added). Never overwrites values already set, possibly manually, in admin panel."""
  try:
    if acc.ns_servers or not ns_list:
      return
    acc.ns_servers = format_ns(ns_list)
    db.session.commit()
    logging.info(f"save_account_ns_if_empty(): NS servers {acc.ns_servers} saved for Cloudflare account {acc.account}")
  except Exception as err:
    logging.error(f"save_account_ns_if_empty(): error for account {acc.account}: {err}")
