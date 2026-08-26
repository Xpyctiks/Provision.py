import logging
import os
import re
from flask import current_app
from db.database import Ownership, Domain_account, User, CloudflareEmailsStatus
from functions.pages_forms import load_cf_active_zones, getSiteLocale, getSiteHrefHistory
from functions.site_actions import count_redirects
from functions.cache_func import page_cache

PAGE_SIZE = 50
SITE_INDEX_CACHE_KEY = "root_site_index"
SITE_INDEX_CACHE_TTL = 60

def natural_key(s):
  """Allows to sort with natural keys - when after 10 goes 11, not 20"""
  return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def _build_raw_site_index(web_folder: str) -> list:
  """Builds the lightweight per-site index for ALL sites, using only bulk (*.query.all()) DB lookups -
  no per-site query, no file/sqlite I/O. This is the expensive-but-shared part, meant to be cached briefly
  by get_cached_site_index() since it's identical for every user (restrictions are applied afterwards)."""
  sites_list = [
    name for name in os.listdir(web_folder)
    if os.path.isdir(os.path.join(web_folder, name)) and not name.startswith('.')
  ]
  sites_list = sorted(sites_list, key=natural_key)
  #bulk lookups - O(1) queries regardless of how many sites there are, instead of a query per site
  ownership_by_domain = {o.domain: o for o in Ownership.query.all()}
  user_realname_by_id = {str(u.id): u.realname for u in User.query.all()}
  cf_account_by_domain = {a.domain: a.account for a in Domain_account.query.all()}
  email_routing_by_domain = {r.domain: r.routing_enabled for r in CloudflareEmailsStatus.query.all()}
  #load all zones from all Cloudflare accounts once (already bulk, per-account not per-site)
  cf_zones = load_cf_active_zones()
  index_rows = []
  for s in sites_list:
    owner_row = ownership_by_domain.get(s)
    if owner_row:
      owner_realname = user_realname_by_id.get(str(owner_row.owner), "ERROR!")
    else:
      owner_realname = "Шукаю власника 💔"
    cf_status = cf_zones.get(s)
    index_rows.append({
      "domain": s,
      "owner_realname": owner_realname,
      "cf_account": cf_account_by_domain.get(s),
      "cf_status": cf_status,
      "is_error": cf_status != "active",
      "email_routing": email_routing_by_domain.get(s, False),
      #plain values only (not the live ORM row) - this list gets pickled into the FileSystemCache
      "created": owner_row.created if owner_row else None,
      "cloned": owner_row.cloned if owner_row else None
    })
  return index_rows

def get_cached_site_index(web_folder: str) -> list:
  """Returns the shared (not per-user) site index, cached briefly so that browsing between pages/filters
  doesn't re-list the whole web folder / re-query the DB / re-hit the Cloudflare API on every click."""
  cached = page_cache.get(SITE_INDEX_CACHE_KEY)
  if cached is not None:
    return cached
  try:
    index_rows = _build_raw_site_index(web_folder)
  except Exception as err:
    logging.error(f"get_cached_site_index(): error building site index: {err}")
    raise
  page_cache.set(SITE_INDEX_CACHE_KEY, index_rows, timeout=SITE_INDEX_CACHE_TTL)
  return index_rows

def filter_by_restrictions(index_rows: list, restrictions: dict, realname: str) -> list:
  """Removes sites hidden from the current user via SitesShowRestricions (same rule as before pagination)."""
  return [
    row for row in index_rows
    if row["domain"] not in restrictions or realname in restrictions[row["domain"]]
  ]

def apply_search_filters(rows: list, search_text: str, owner: str, account: str, errors_only: bool) -> list:
  """Filters the (already restriction-filtered) index the same way the old client-side applyFilters() did.
  The old version matched the free-text search against the WHOLE visible row text (row.innerText), not just
  the domain - so besides the domain itself, also check owner/cf_account here to stay just as forgiving."""
  search_text = (search_text or "").strip().lower()
  owner = (owner or "").strip()
  account = (account or "").strip()
  result = rows
  if search_text:
    result = [
      r for r in result
      if search_text in r["domain"].lower()
      or search_text in (r["owner_realname"] or "").lower()
      or search_text in (r["cf_account"] or "").lower()
    ]
  if owner:
    result = [r for r in result if r["owner_realname"] == owner]
  if account:
    result = [r for r in result if r["cf_account"] == account]
  if errors_only:
    result = [r for r in result if r["is_error"]]
  return result

def build_page_html_data(page_rows: list, web_folder: str, start_index: int, restrictions: dict, realname: str) -> list:
  """Computes the heavy per-site detail (sqlite/JSON/text file I/O, filesystem checks) - only for the
  given page slice of the index (up to PAGE_SIZE sites), not for the whole site list."""
  html_data = []
  ngx_sites_pathen = current_app.config.get("NGX_SITES_PATHEN", "")
  for offset, row in enumerate(page_rows):
    i = start_index + offset
    s = row["domain"]
    ngx_site = os.path.join(ngx_sites_pathen, s)
    #check robots.txt for existance and change its button color
    if os.path.exists(os.path.join(web_folder, s, "public", "robots.txt")):
      robots_button = "btn-primary"
    else:
      robots_button = "btn-light"
    #cf_account was already bulk-resolved in the index - no extra query needed here
    cf_account = row["cf_account"]
    if not cf_account:
      dns_validation = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary disabled dropdown-item" type="submit" name="validation" value="{s}" style="margin-top: 5px;">📮DNS валідація</a><br>'
      cf_account_display = "⌛нема інформації"
    else:
      dns_validation = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary dropdown-item" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" name="validation" value="{s}" onclick="showLoading()" style="margin-top: 5px;" title="Керування CNAME записами для валідації домену для пошукових систем.">📮DNS валідація</a>'
      cf_account_display = cf_account
    #build Cloudflare status suffix for site_status field (index already knows if there's an error)
    cf_status = row["cf_status"]
    if cf_status is None:
      cf_status_html = '❌Домен відсутній у Cloudflare'
      table_class = "table-danger"
    elif cf_status != "active":
      cf_status_html = f'⚠️CF статус: {cf_status}'
      table_class = "table-danger"
    else:
      cf_status_html = '✅Статус сайту OK'
      table_class = "table-success"
    cf_error_attr = ' data-cf-error="1"' if row["is_error"] else ''
    #read locale value from the site's own DB (seo_metas.extra_fileds, e.g. {"locale": "fr"}) to use as html_lang
    html_lang = getSiteLocale(s, web_folder)
    #read the current clone's slug/hreflang from the site's clones-history.json to use as input placeholders
    current_clone = getSiteHrefHistory(s, web_folder)
    #site owner's realname; if it matches the current user, show the eye button to let them hide/unhide the site for others
    site_owner = row["owner_realname"]
    if site_owner == realname:
      if s in restrictions:
        eye_button = f'&nbsp;<button class="btn btn-sm btn-outline-secondary eye-btn p-0" type="submit" value="{s}" name="unhideSite" form="main_form" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Сайт прихований від інших користувачів. Натисніть, щоб знову показати його всім.">🙈</button>'
      else:
        eye_button = f'&nbsp;<button class="btn btn-sm btn-outline-secondary eye-btn p-0" type="submit" value="{s}" name="hideSite" form="main_form" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Приховати цей сайт від інших користувачів (бачити його будете тільки ви).">👁️</button>'
    else:
      eye_button = ""
    #email routing status icon
    email_icon = '&nbsp;<span style="font-size: 1.4em;" data-bs-toggle="tooltip" data-bs-placement="top" title="Email Routing увімкнено на Cloudflare для цього домену">📧</span>' if row["email_routing"] else ''
    #site created date/clone note - reuses the plain values already fetched in bulk for the index
    created_raw = row["created"]
    cloned_raw = row["cloned"]
    if created_raw:
      if not cloned_raw:
        site_created = created_raw.strftime("%d-%m-%Y %H:%M:%S")
      else:
        site_created = f"{created_raw.strftime('%d-%m-%Y %H:%M:%S')}.<br>Клон {cloned_raw}"
    else:
      site_created = "невідомо🤷🏼‍♂️"
    if os.path.islink(ngx_site):
      html_data.append({
        "table_type": f'<tr data-owner="{site_owner}" data-account="{cf_account_display}"{cf_error_attr}>\n<th scope="row" class="{table_class}">{i}{eye_button}{email_icon}</th>',
        "button_2": f'<button class="btn btn-warning dropdown-item" type="submit" value="{s}" name="disable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Тимчасово вимкнути сайт - він не будет оброблятися при запитах зовні,але фізично залишається на сервері.">🚧Вимкнути</button>',
        "site_name": s,
        "table_type2": f'<td class="{table_class}">',
        "count_redirects": count_redirects(s),
        "getSiteCreated": site_created,
        "id": i,
        "accordeon_path": os.path.join(web_folder, s),
        "getSiteOwner": site_owner,
        "site_status": cf_status_html,
        "robots_button": robots_button,
        "dns_validation": dns_validation,
        "cf_account": cf_account_display,
        "html_lang": html_lang,
        "site_slug": current_clone["slug"],
        "site_hreflang": current_clone["hreflang"]
      })
    else:
      if table_class == "table-success":
        table_class = "table-warning"
      html_data.append({
        "table_type": f'<tr data-owner="{site_owner}" data-account="{cf_account_display}"{cf_error_attr}>\n<th scope="row" class="{table_class}">{i}{eye_button}{email_icon}</th>',
        "button_2": f'<button class="btn btn-success dropdown-item" type="submit" value="{s}" name="enable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>',
        "site_name": s,
        "table_type2": f'<td class="{table_class}">',
        "count_redirects": count_redirects(s),
        "getSiteCreated": site_created,
        "id": i,
        "accordeon_path": os.path.join(web_folder, s),
        "getSiteOwner": site_owner,
        "site_status": f'🚧Сайт вимкнено<br>{cf_status_html}',
        "robots_button": robots_button,
        "dns_validation": dns_validation,
        "cf_account": cf_account_display,
        "html_lang": html_lang,
        "site_slug": current_clone["slug"],
        "site_hreflang": current_clone["hreflang"]
      })
  return html_data
