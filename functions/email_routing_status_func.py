import logging
from db.db import db
from db.database import EmailRoutingDomainStatus

def seed_email_routing_domain_status(domain: str, cf_account: str) -> None:
  """Best-effort: ensures a domain has a row in EmailRoutingDomainStatus (defaulting to "no routing
  configured yet") the moment it becomes known to the project - manual upload, auto-provision, adding it
  in Cloudflare, buying it - without waiting for someone to actually touch Email Routing for it. Never
  overwrites an existing row, which may already hold real, more accurate status."""
  try:
    if EmailRoutingDomainStatus.query.filter_by(domain=domain).first():
      return
    db.session.add(EmailRoutingDomainStatus(
      domain=domain, cloudflare_account=cf_account, routing_enabled=False, has_catchall=False
    ))
    db.session.commit()
  except Exception as err:
    logging.error(f"seed_email_routing_domain_status(): error for domain {domain}: {err}")

def sync_email_routing_domain_status(domain: str, cf_account: str, routing_enabled: bool, has_catchall: bool, actor: str) -> None:
  """Authoritative update - called wherever Email Routing status is actually queried/changed for a
  domain (cron sync, single-domain manage page, bulk page, domain purchase). Always overwrites."""
  row = EmailRoutingDomainStatus.query.filter_by(domain=domain).first()
  if not row:
    row = EmailRoutingDomainStatus(domain=domain)
    db.session.add(row)
  row.cloudflare_account = cf_account
  row.routing_enabled = routing_enabled
  row.has_catchall = has_catchall
  row.updatedby = actor
  db.session.commit()
