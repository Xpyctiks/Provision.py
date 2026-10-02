import logging
import requests
from datetime import datetime
from db.database import DomainRegistrator

DYNADOT_API_URL = "https://api.dynadot.com/api3.json"

def dynadot_register_domain(registrator: DomainRegistrator, domain: str, duration: int = 1) -> tuple[bool, str]:
  """Purchases a new domain via Dynadot's register command. Returns (success, message)."""
  try:
    params = {
      "key": registrator.api_production_key,
      "command": "register",
      "domain": domain,
      "duration": duration
    }
    result = requests.get(DYNADOT_API_URL, params=params, timeout=30).json()
    response = result.get("RegisterResponse", {})
    if response.get("Status") == "success":
      logging.info(f"dynadot_register_domain(): Domain {domain} successfully registered via {registrator.name}")
      return True, "OK"
    logging.error(f"dynadot_register_domain(): Error registering domain {domain} via {registrator.name}: {result}")
    return False, result
  except Exception as err:
    logging.error(f"dynadot_register_domain(): general error for domain {domain}: {err}")
    return False, str(err)

def _dynadot_ms_to_iso(value) -> str:
  """Dynadot returns dates as epoch milliseconds (string or int). Converts to 'YYYY-MM-DD HH:MM', or '' if unknown."""
  try:
    return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d %H:%M")
  except Exception:
    return ""

def _dynadot_domain_status(item: dict) -> str:
  """Builds a short human-readable domain state out of Dynadot's yes/no flags."""
  states = []
  if str(item.get("Disabled", "")).lower() == "yes":
    states.append("disabled")
  if str(item.get("Hold", "")).lower() == "yes":
    states.append("hold")
  if str(item.get("UdrpLocked", "")).lower() == "yes":
    states.append("udrp locked")
  if str(item.get("RegistrantUnverified", "")).lower() == "yes":
    states.append("registrant unverified")
  try:
    if int(item.get("Expiration", 0)) / 1000 < datetime.now().timestamp():
      states.append("expired")
  except Exception:
    pass
  if str(item.get("Locked", "")).lower() in ("yes", "locked"):
    states.append("locked")
  return ", ".join(states) if states else "active"

def dynadot_list_domains(registrator: DomainRegistrator) -> tuple[bool, list | str]:
  """Lists all domains on the Dynadot account via the list_domain command. Returns (True, [ {name, ns, created, status}, ... ]) or (False, error)."""
  try:
    params = {"key": registrator.api_production_key, "command": "list_domain"}
    #list_domain returns the whole account at once - may be slow on big accounts
    result = requests.get(DYNADOT_API_URL, params=params, timeout=180).json()
    response = result.get("ListDomainInfoResponse", {})
    if response.get("Status") != "success":
      logging.error(f"dynadot_list_domains(): Error listing domains via {registrator.name}: {result}")
      return False, str(response.get("Error") or result)
    domains = []
    for item in response.get("MainDomains", []) or []:
      ns_settings = item.get("NameServerSettings", {}) or {}
      ns = []
      for server in ns_settings.get("NameServers", []) or []:
        name = server.get("ServerName") if isinstance(server, dict) else server
        if name:
          ns.append(str(name).lower())
      #domains on Dynadot parking/forwarding have no NS list - show the settings type instead
      if not ns and ns_settings.get("Type"):
        ns = [f"({ns_settings.get('Type')})"]
      domains.append({
        "name": str(item.get("Name", "")).lower(),
        "ns": ns,
        "created": _dynadot_ms_to_iso(item.get("Registration")),
        "status": _dynadot_domain_status(item)
      })
    logging.info(f"dynadot_list_domains(): {len(domains)} domain(s) loaded from {registrator.name}")
    return True, domains
  except Exception as err:
    logging.error(f"dynadot_list_domains(): general error for {registrator.name}: {err}")
    return False, str(err)

def dynadot_set_ns(registrator: DomainRegistrator, domain: str, ns_list: list) -> tuple[bool, str]:
  """Sets nameservers for the given domain via Dynadot's set_ns command. Returns (success, message)."""
  try:
    params = {
      "key": registrator.api_production_key,
      "command": "set_ns",
      "domain": domain
    }
    for i, ns in enumerate(ns_list):
      params[f"ns{i}"] = ns
    result = requests.get(DYNADOT_API_URL, params=params, timeout=30).json()
    response = result.get("SetNsResponse", {})
    if response.get("Status") == "success":
      logging.info(f"dynadot_set_ns(): NS servers for domain {domain} successfully set to {ns_list} via {registrator.name}")
      return True, "OK"
    logging.error(f"dynadot_set_ns(): Error setting NS servers for domain {domain} via {registrator.name}: {result}")
    return False, result
  except Exception as err:
    logging.error(f"dynadot_set_ns(): general error for domain {domain}: {err}")
    return False, str(err)
