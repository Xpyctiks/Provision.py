import logging
import time
import requests
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
