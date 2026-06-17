import logging
import os
import requests
from flask import Blueprint, current_app, jsonify
from db.database import Cloudflare, CloudflareEmailsStatus, CloudflareEmailsRules
from db.db import db

cloudflare_email_bp = Blueprint("cloudflare_email", __name__)

def _format_rule(rule: dict) -> str:
  """Builds a short human-readable description of a single Cloudflare Email Routing rule"""
  matchers = ", ".join(str(m.get("value", m.get("type",""))) for m in rule.get("matchers", []))
  actions = []
  for a in rule.get("actions", []):
    value = a.get("value", [])
    if isinstance(value, list):
      value = ",".join(str(v) for v in value)
    actions.append(f"{a.get('type','')}:{value}")
  actions_str = ", ".join(actions)
  status = "enabled" if rule.get("enabled") else "disabled"
  return f"{matchers} -> {actions_str} [{status}]"[:500]

@cloudflare_email_bp.route("/cloudflare_email/update_emails_status", methods=['GET'])
def update_emails_status():
  """GET request: queries Cloudflare Email Routing status and rules for every domain in every Cloudflare account stored in DB, and syncs CloudflareEmailsStatus/CloudflareEmailsRules tables. Meant to be triggered periodically by a cron job."""
  try:
    logging.info("update_emails_status(): -----------------------Starting Cloudflare Email Routing status update-----------------------")
    web_folder = current_app.config.get("WEB_FOLDER","")
    if web_folder == "":
      logging.error("update_emails_status(): ERROR! - web_folder variable is empty!")
      return jsonify({"status": "error", "message": "web_folder is empty"}), 500
    #only the sites which are actually present on this server should be synced, not the whole Cloudflare account
    sites_list = [
      name for name in os.listdir(web_folder)
      if os.path.isdir(os.path.join(web_folder, name)) and not name.startswith('.')
    ]
    processed = 0
    errors = 0
    accounts = Cloudflare.query.all()
    for acc in accounts:
      headers = {
        "X-Auth-Email": acc.account,
        "X-Auth-Key": acc.token,
        "Content-Type": "application/json"
      }
      page = 1
      while True:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
        r = requests.get(url, headers=headers, timeout=10).json()
        if not r.get("success"):
          logging.error(f"update_emails_status(): Failed to load zones for account {acc.account}: {r.get('errors')}")
          errors += 1
          break
        for zone in r.get("result", []):
          domain = zone["name"]
          #skip domains which are not actually hosted on this server
          if domain not in sites_list:
            continue
          zone_id = zone["id"]
          try:
            #------------------------- Email Routing status -------------------------
            status_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing"
            status_result = requests.get(status_url, headers=headers, timeout=10).json()
            if status_result.get("success"):
              routing_enabled = bool(status_result.get("result", {}).get("enabled", False))
            else:
              logging.error(f"update_emails_status(): Failed to load Email Routing status for domain {domain}: {status_result.get('errors')}")
              routing_enabled = False
            record = CloudflareEmailsStatus.query.filter_by(domain=domain).first()
            if not record:
              new_record = CloudflareEmailsStatus(domain=domain, routing_enabled=routing_enabled, enabledby="cron job", updatedby="cron job")
              db.session.add(new_record)
              db.session.commit()
              logging.info(f"update_emails_status(): New Email Routing status record created for domain {domain}: {routing_enabled}")
            elif record.routing_enabled != routing_enabled:
              record.routing_enabled = routing_enabled
              record.updatedby = "cron job"
              db.session.commit()
              logging.info(f"update_emails_status(): Email Routing status for domain {domain} changed to {routing_enabled}")
            #------------------------- Email Routing rules -------------------------
            rules_page = 1
            rules = []
            while True:
              rules_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules?per_page=50&page={rules_page}"
              rules_result = requests.get(rules_url, headers=headers, timeout=10).json()
              if not rules_result.get("success"):
                logging.error(f"update_emails_status(): Failed to load Email Routing rules for domain {domain}: {rules_result.get('errors')}")
                break
              rules.extend(rules_result.get("result", []))
              if rules_page >= rules_result.get("result_info", {}).get("total_pages", 1):
                break
              rules_page += 1
            #re-writing the whole rule set for this domain with the current one received from Cloudflare
            CloudflareEmailsRules.query.filter_by(domain=domain).delete()
            for rule in rules:
              new_rule = CloudflareEmailsRules(domain=domain, rule=_format_rule(rule))
              db.session.add(new_rule)
            db.session.commit()
            processed += 1
          except Exception as err:
            logging.error(f"update_emails_status(): Error while processing domain {domain}: {err}")
            errors += 1
        if page >= r.get("result_info", {}).get("total_pages", 1):
          break
        page += 1
    logging.info(f"update_emails_status(): -----------------------Finished. Domains processed: {processed}, errors: {errors}-----------------------")
    return jsonify({"status": "done", "processed": processed, "errors": errors}), 200
  except Exception as err:
    logging.error(f"update_emails_status(): Global error: {err}")
    return jsonify({"status": "error", "message": str(err)}), 500
