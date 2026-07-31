import logging
import requests
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
    error_msg = response.get("Status")
    logging.error(f"dynadot_register_domain(): Error registering domain {domain} via {registrator.name}: {error_msg}")
    return False, error_msg
  except Exception as err:
    logging.error(f"dynadot_register_domain(): general error for domain {domain}: {err}")
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
    error_msg = response.get("Status")
    logging.error(f"dynadot_set_ns(): Error setting NS servers for domain {domain} via {registrator.name}: {error_msg}")
    return False, error_msg
  except Exception as err:
    logging.error(f"dynadot_set_ns(): general error for domain {domain}: {err}")
    return False, str(err)
