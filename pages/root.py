import logging
import math
from urllib.parse import urlencode
from flask import render_template,Blueprint,current_app,flash,make_response,request,jsonify
from flask_login import login_required,current_user
from functions.site_actions import is_admin, is_mail_admin
from db.database import Messages,User,Cloudflare,SitesShowRestricions
from functions.send_to_telegram import send_to_telegram
from db.db import db
from functions.cache_func import page_cache
from functions.root_func import PAGE_SIZE,get_cached_site_index,filter_by_restrictions,apply_search_filters,build_page_html_data

root_bp = Blueprint("root", __name__)

def _is_ajax_request() -> bool:
  return request.headers.get("X-Requested-With") == "XMLHttpRequest"

@root_bp.route("/", methods=['GET'])
@login_required
def index():
  """Main function: generates root page /. Server-side paginated (PAGE_SIZE sites per page) - the heavy
  per-site work (sqlite/JSON/text file reads) is only ever done for the current page's sites, while
  filtering/search/pagination/counters operate on a lightweight, briefly-cached index of ALL sites."""
  CACHE_KEY = f"user:{current_user.realname}"
  ajax = _is_ajax_request()
  page_arg = request.args.get("page")
  search = (request.args.get("search") or "").strip()
  owner_filter = (request.args.get("owner") or "").strip()
  account_filter = (request.args.get("account") or "").strip()
  errors_only = request.args.get("errors") == "1"
  export_list = request.args.get("export_list") == "1"
  #the "default view" (bare "/", no page/filter/export params) is the only one still eligible for the
  #old whole-page-HTML cache - every other combination is cheap enough now to just compute fresh every time
  is_default_view = not (page_arg or search or owner_filter or account_filter or errors_only or export_list)
  try:
    if is_default_view and not ajax:
      cached = page_cache.get(CACHE_KEY)
      if cached:
        response = make_response(cached)
        response.headers["X-Cache"] = "HIT"
        response.set_cookie("x_cache", "HIT")
        return response
    web_folder = current_app.config.get("WEB_FOLDER","")
    if web_folder == "":
      logging.error(f"index(): root page generate function ERROR! - web_folder variable is empty!")
      if ajax or export_list:
        return jsonify({"error": "WEB_FOLDER is empty"}), 500
      return "index(): root page generate function ERROR!", 500
    #shared (not per-user), briefly-cached lightweight index of ALL sites
    index_rows = get_cached_site_index(web_folder)
    #checking SitesShowRestricions table - hide a site from the current user if it has restrictions and the user is not listed in showforuser
    restrictions = {
      r.domain: [u.strip() for u in r.showforuser.split(',')]
      for r in SitesShowRestricions.query.all()
    }
    visible_rows = filter_by_restrictions(index_rows, restrictions, current_user.realname)
    total_count = len(visible_rows)
    has_cf_errors = any(r["is_error"] for r in visible_rows)
    if export_list:
      #lightweight full (unpaginated) domain+owner list, used by the CSV Href-history export which needs
      #every site the user can see, not just the currently displayed page
      return jsonify({"sites": [{"domain": r["domain"], "owner": r["owner_realname"]} for r in visible_rows]})
    filtered_rows = apply_search_filters(visible_rows, search, owner_filter, account_filter, errors_only)
    filtered_count = len(filtered_rows)
    total_pages = max(1, math.ceil(filtered_count / PAGE_SIZE))
    try:
      page = int(page_arg) if page_arg else 1
    except ValueError:
      page = 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    page_rows = filtered_rows[start:start + PAGE_SIZE]
    html_data = build_page_html_data(page_rows, web_folder, start + 1, restrictions, current_user.realname)
    if ajax:
      rows_html = render_template("template-main-rows.html", html_data=html_data, mail_admin=is_mail_admin())
      return jsonify({
        "rows_html": rows_html,
        "page": page,
        "total_pages": total_pages,
        "filtered_count": filtered_count,
        "total_count": total_count,
        "has_cf_errors": has_cf_errors
      })
    #gathering all list of available users to put them into user filter list (marks the active one as selected)
    users_list = [f'<option value="{s.realname}"{" selected" if s.realname == owner_filter else ""}>{s.realname}</option>' for s in User.query.order_by(User.username).all()]
    #gathering all list of available Cloudflare accounts to put them into accounts filter list
    cf_accounts_list = [f'<option value="{a.account}"{" selected" if a.account == account_filter else ""}>{a.account}</option>' for a in Cloudflare.query.order_by(Cloudflare.account).all()]
    #getting into DB and checking is there any messages for the current user (only meaningful on a full
    #page render - the flash modal isn't part of the AJAX row fragment, so this must not run for AJAX requests)
    messages = Messages.query.filter_by(foruserid=current_user.id).all()
    if len(messages) != 0:
      logging.info(f"index(): Some messages found for user {current_user.realname} - {len(messages)} of them...")
      msg = ""
      for i, s in enumerate(messages, 1):
        msg += f"<strong>📫 Массове повідомлення №{i}</strong>\n"
        msg += s.text+"\n"
        del_msg = Messages.query.filter_by(id=s.id).first()
        if del_msg:
          db.session.delete(del_msg)
          logging.info(f"Message with ID={s.id} deleted from DB as the read one.")
      db.session.commit()
      flash(msg,'alert alert-info')
      logging.info(f"index(): Flash popup windows is ready for the user {current_user.realname}...")
    extra_params = {}
    if search: extra_params["search"] = search
    if owner_filter: extra_params["owner"] = owner_filter
    if account_filter: extra_params["account"] = account_filter
    if errors_only: extra_params["errors"] = "1"
    filter_qs = ("&" + urlencode(extra_params)) if extra_params else ""
    response = make_response(render_template(
      "template-main.html",
      html_data=html_data,
      admin_panel=is_admin(),
      mail_admin=is_mail_admin(),
      users_list=users_list,
      cf_accounts_list=cf_accounts_list,
      has_cf_errors=has_cf_errors,
      total_count=total_count,
      filtered_count=filtered_count,
      page=page,
      total_pages=total_pages,
      prev_page=max(1, page-1),
      next_page=min(total_pages, page+1),
      filter_qs=filter_qs,
      search_value=search,
      errors_value=errors_only,
      version=current_app.config.get("VERSION","")
    ))
    if is_default_view and not current_app.debug:
      page_cache.set(CACHE_KEY, response.get_data(), timeout=300)
      response.headers["X-Cache"] = "MISS"
      response.set_cookie("x_cache", "MISS")
    return response
  except Exception as msg:
    logging.error(f"Error in index(/): {msg}")
    send_to_telegram(f"Root page render general error: {msg}",f"🚒Provision error by {current_user.realname}:")
    page_cache.delete(CACHE_KEY)
    if ajax or export_list:
      return jsonify({"error": str(msg)}), 500
    return "index(): root page generate function ERROR!", 500
