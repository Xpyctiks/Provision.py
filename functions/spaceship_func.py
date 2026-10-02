import logging
import time
import requests
from datetime import datetime
from db.database import DomainRegistrator

SPACESHIP_API_URL = "https://spaceship.dev/api/v1"

def _headers(registrator: DomainRegistrator) -> dict:
  """Builds the auth headers for Spaceship API calls. api_production_key -> X-Api-Key, api_secret_key -> X-Api-Secret."""
  return {
    "X-Api-Key": registrator.api_production_key,
    "X-Api-Secret": registrator.api_secret_key,
    "Content-Type": "application/json"
  }

def _error_detail(response) -> str:
  """Extracts the 'detail' field from a Spaceship application/problem+json error response, falling back to raw text."""
  try:
    return response.json().get("detail") or f"HTTP {response.status_code}"
  except Exception:
    return f"HTTP {response.status_code}: {response.text[:200]}"

def _poll_operation(operation_id: str, headers: dict, timeout: int = 60, interval: int = 2) -> tuple[bool, str]:
  """Polls GET /async-operations/{id} until status becomes success/failed, or until timeout. Returns (success, message)."""
  elapsed = 0
  while elapsed <= timeout:
    try:
      r = requests.get(f"{SPACESHIP_API_URL}/async-operations/{operation_id}", headers=headers, timeout=15)
      data = r.json()
      status = data.get("status")
      if status == "success":
        logging.info(f"_poll_operation(): Spaceship operation {operation_id} completed successfully")
        return True, "OK"
      if status == "failed":
        details = data.get("details") or "Unknown error"
        logging.error(f"_poll_operation(): Spaceship operation {operation_id} failed: {details}")
        return False, str(details)
      #still pending - wait and retry
    except Exception as err:
      logging.error(f"_poll_operation(): error polling operation {operation_id}: {err}")
      return False, str(err)
    time.sleep(interval)
    elapsed += interval
  logging.error(f"_poll_operation(): timed out waiting for Spaceship operation {operation_id}")
  return False, "Таймаут очікування відповіді Spaceship"

def spaceship_register_domain(registrator: DomainRegistrator, domain: str, duration: int = 1) -> tuple[bool, str]:
  """Purchases a new domain via Spaceship's async domain registration endpoint. Returns (success, message)."""
  try:
    headers = _headers(registrator)
    body = {
      "autoRenew": False,
      "years": duration,
      "privacyProtection": {"level": "high", "userConsent": True},
      "contacts": {
        "registrant": registrator.contact_id,
        "admin": registrator.contact_id,
        "tech": registrator.contact_id,
        "billing": registrator.contact_id
      }
    }
    logging.info(f"spaceship_register_domain(): Requesting registration of domain {domain} via {registrator.name}")
    r = requests.post(f"{SPACESHIP_API_URL}/domains/{domain}", headers=headers, json=body, timeout=30)
    if r.status_code != 202:
      error_msg = _error_detail(r)
      logging.error(f"spaceship_register_domain(): Error registering domain {domain} via {registrator.name}: {error_msg}")
      return False, error_msg
    operation_id = r.headers.get("spaceship-async-operationid")
    if not operation_id:
      logging.error(f"spaceship_register_domain(): Domain {domain}: 202 Accepted but no spaceship-async-operationid header returned")
      return False, "Spaceship не повернув ID операції"
    logging.info(f"spaceship_register_domain(): Domain {domain} registration accepted, operation {operation_id}, polling for result...")
    ok, msg = _poll_operation(operation_id, headers)
    if ok:
      logging.info(f"spaceship_register_domain(): Domain {domain} successfully registered via {registrator.name}")
    else:
      logging.error(f"spaceship_register_domain(): Error registering domain {domain} via {registrator.name}: {msg}")
    return ok, msg
  except Exception as err:
    logging.error(f"spaceship_register_domain(): general error for domain {domain}: {err}")
    return False, str(err)

def _spaceship_date_to_iso(value) -> str:
  """Spaceship returns ISO-8601 dates (e.g. 2024-05-01T10:20:30.000Z). Converts to 'YYYY-MM-DD HH:MM', or '' if unknown."""
  if not value:
    return ""
  try:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
  except Exception:
    return str(value)[:16].replace("T", " ")

def spaceship_list_domains(registrator: DomainRegistrator) -> tuple[bool, list | str]:
  """Lists all domains on the Spaceship account via GET /domains (paginated, max 100 per request).
  Returns (True, [ {name, ns, created, status}, ... ]) or (False, error)."""
  try:
    headers = _headers(registrator)
    domains = []
    skip = 0
    take = 100
    while True:
      r = requests.get(f"{SPACESHIP_API_URL}/domains", headers=headers, params={"take": take, "skip": skip, "orderBy": "name"}, timeout=30)
      if r.status_code != 200:
        error_msg = _error_detail(r)
        logging.error(f"spaceship_list_domains(): Error listing domains via {registrator.name}: {error_msg}")
        return False, error_msg
      data = r.json()
      items = data.get("items", []) or []
      for item in items:
        nameservers = item.get("nameservers", {}) or {}
        ns = [str(h).lower() for h in (nameservers.get("hosts") or [])]
        if not ns and nameservers.get("provider"):
          ns = [f"({nameservers.get('provider')})"]
        status = item.get("lifecycleStatus") or ""
        if item.get("suspensions"):
          status = f"{status}, suspended".strip(", ")
        if item.get("verificationStatus") and item.get("verificationStatus") not in ("success", "verified"):
          status = f"{status}, verification: {item.get('verificationStatus')}".strip(", ")
        domains.append({
          "name": str(item.get("name", "")).lower(),
          "ns": ns,
          "created": _spaceship_date_to_iso(item.get("registrationDate")),
          "status": status or "-"
        })
      skip += len(items)
      if not items or skip >= int(data.get("total", 0) or 0):
        break
    logging.info(f"spaceship_list_domains(): {len(domains)} domain(s) loaded from {registrator.name}")
    return True, domains
  except Exception as err:
    logging.error(f"spaceship_list_domains(): general error for {registrator.name}: {err}")
    return False, str(err)

def spaceship_set_ns(registrator: DomainRegistrator, domain: str, ns_list: list) -> tuple[bool, str]:
  """Sets custom nameservers for the given domain via Spaceship's nameservers endpoint. Returns (success, message)."""
  try:
    headers = _headers(registrator)
    body = {"provider": "custom", "hosts": ns_list}
    r = requests.put(f"{SPACESHIP_API_URL}/domains/{domain}/nameservers", headers=headers, json=body, timeout=30)
    if r.status_code == 200:
      logging.info(f"spaceship_set_ns(): NS servers for domain {domain} successfully set to {ns_list} via {registrator.name}")
      return True, "OK"
    error_msg = _error_detail(r)
    logging.error(f"spaceship_set_ns(): Error setting NS servers for domain {domain} via {registrator.name}: {error_msg}")
    return False, error_msg
  except Exception as err:
    logging.error(f"spaceship_set_ns(): general error for domain {domain}: {err}")
    return False, str(err)
