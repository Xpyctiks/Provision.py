import logging
import requests
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from db.database import Cloudflare
from functions.site_actions import is_admin

cloudflare_email_dstaddresses_bp = Blueprint("cloudflare_email_dstaddresses", __name__)
def _get_headers(account: str, token: str) -> dict:
  return {
    "X-Auth-Email": account,
    "X-Auth-Key": token,
    "Content-Type": "application/json"
  }

def _get_account_id(headers: dict):
  """Returns the Cloudflare account ID (destination addresses are account-scoped, not zone-scoped)"""
  url = "https://api.cloudflare.com/client/v4/accounts"
  r = requests.get(url, headers=headers, timeout=10).json()
  if r.get("success") and r.get("result"):
    return r["result"][0]["id"]
  return None

def _get_destination_addresses(account_id, headers: dict) -> list:
  """Queries the full list of Email Routing destination addresses available on the Cloudflare account (handles pagination)"""
  addresses = []
  if not account_id:
    return addresses
  page = 1
  while True:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses?per_page=50&page={page}"
    r = requests.get(url, headers=headers, timeout=10).json()
    if not r.get("success"):
      logging.error(f"_get_destination_addresses(): Failed to load destination addresses for account {account_id}: {r.get('errors')}")
      break
    addresses.extend(r.get("result", []))
    if page >= r.get("result_info", {}).get("total_pages", 1):
      break
    page += 1
  return addresses

@cloudflare_email_dstaddresses_bp.route("/cloudflare_email_dstaddresses/", methods=['GET'])
@login_required
def show_dstaddresses():
  """GET request: shows the Email Routing destination addresses management page for the selected Cloudflare account"""
  selected_account = (request.args.get("account") or "").strip()
  try:
    accounts = Cloudflare.query.order_by(Cloudflare.account).all()
    accounts_list = ""
    for acc in accounts:
      accounts_list += f'<li><a class="dropdown-item account" href="#" data-value="{acc.account}">{acc.account}</a></li>\n'
    addresses_html = ""
    if selected_account:
      acc = Cloudflare.query.filter_by(account=selected_account).first()
      if not acc:
        logging.error(f"show_dstaddresses(): Account {selected_account} requested by {current_user.realname} is not found in DB!")
        flash(f'Аккаунт Cloudflare {selected_account} не знайдено в базі!','alert alert-danger')
        return redirect("/cloudflare_email_dstaddresses/",302)
      headers = _get_headers(acc.account, acc.token)
      account_id = _get_account_id(headers)
      addresses = _get_destination_addresses(account_id, headers)
      if not addresses:
        addresses_html = '<tr><td colspan="4" class="text-center text-muted">Адреси призначення відсутні</td></tr>'
      else:
        for i, addr in enumerate(addresses, 1):
          email = addr.get("email","")
          addr_id = addr.get("id", addr.get("tag",""))
          verified = bool(addr.get("verified"))
          verified_badge = '<span class="badge bg-success">верифіковано</span>' if verified else '<span class="badge bg-warning text-dark">не верифіковано</span>'
          resend_button = "" if verified else f'<button type="submit" class="btn btn-outline-warning ResendAddress-btn" name="buttonResendAddress" onclick="showLoading()" value="{addr_id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити та додати цю адресу знову, щоб Cloudflare повторно надіслав листа з верифікацією.">📨</button>'
          addresses_html += f"""
  <tr class="table-success">
    <td class="table-success cname-cell">{i}</td>
    <td class="table-success cname-cell">{email}</td>
    <td class="table-success cname-cell">{verified_badge}</td>
    <td class="table-success cname-cell">
      <form action="/cloudflare_email_dstaddresses/" method="POST" id="postform" novalidate>
        <input type="hidden" name="selected_account" value="{selected_account}">
        <input type="hidden" name="address_email" value="{email}">
        <button type="submit" class="btn btn-outline-danger DeleteAddress-btn" name="buttonDeleteAddress" onclick="showLoading()" value="{addr_id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити цю адресу призначення.">❌</button>
        {resend_button}
      </form>
    </td>
  </tr>"""
    return render_template(
      "template-cloudflare_email_dstaddress.html",
      accounts_list=accounts_list,
      selected_account=selected_account,
      addresses_html=addresses_html,
      admin_panel=is_admin()
    )
  except Exception as err:
    logging.error(f"show_dstaddresses(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка на сторінці управління адресами призначення! Дивіться логи.','alert alert-danger')
    return redirect("/",302)

@cloudflare_email_dstaddresses_bp.route("/cloudflare_email_dstaddresses/", methods=['POST'])
@login_required
def catch_dstaddresses():
  """POST request processor: handles add/delete/resend-verification actions for Email Routing destination addresses"""
  selected_account = (request.form.get("selected_account") or "").strip()
  if not selected_account:
    flash('Аккаунт Cloudflare не вказано!','alert alert-danger')
    return redirect("/cloudflare_email_dstaddresses/",302)
  try:
    acc = Cloudflare.query.filter_by(account=selected_account).first()
    if not acc:
      logging.error(f"catch_dstaddresses(): Account {selected_account} requested by {current_user.realname} is not found in DB!")
      flash(f'Аккаунт Cloudflare {selected_account} не знайдено в базі!','alert alert-danger')
      return redirect("/cloudflare_email_dstaddresses/",302)
    headers = _get_headers(acc.account, acc.token)
    account_id = _get_account_id(headers)
    if not account_id:
      logging.error(f"catch_dstaddresses(): Failed to resolve Cloudflare account ID for {selected_account}!")
      flash(f'Не вдалося визначити ID аккаунту Cloudflare {selected_account}!','alert alert-danger')
      return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
    #------------------------- add a new destination address -------------------------
    if "buttonAddAddress" in request.form:
      email = request.form.get("new-address-email","").strip()
      if not email:
        flash('Email адреса не вказана!','alert alert-warning')
        return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
      url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses"
      result = requests.post(url, headers=headers, json={"email": email}, timeout=10).json()
      if result.get("success"):
        logging.info(f"catch_dstaddresses(): Destination address {email} created for account {selected_account} by {current_user.realname}")
        flash(f'Адреса {email} успішно додана! Лист з верифікацією надіслано на цю поштову скриньку.','alert alert-success')
      else:
        error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_dstaddresses(): Failed to create destination address {email} for account {selected_account}: {result.get('errors')}")
        flash(f'Помилка при додаванні адреси {email}: <strong>{error_msg}</strong>','alert alert-danger')
    #------------------------- delete an address -------------------------
    elif "buttonDeleteAddress" in request.form:
      addr_id = request.form.get("buttonDeleteAddress","").strip()
      if not addr_id:
        flash('ID адреси не був отриман сервером!','alert alert-warning')
        return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
      url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses/{addr_id}"
      result = requests.delete(url, headers=headers, timeout=10).json()
      if result.get("success"):
        logging.info(f"catch_dstaddresses(): Destination address {addr_id} deleted for account {selected_account} by {current_user.realname}")
        flash('Адреса успішно видалена!','alert alert-success')
      else:
        error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_dstaddresses(): Failed to delete destination address {addr_id} for account {selected_account}: {result.get('errors')}")
        flash(f'Помилка при видаленні адреси: <strong>{error_msg}</strong>','alert alert-danger')
    #------------------------- resend verification e-mail (Cloudflare has no direct "resend" endpoint, so we delete and re-create the address) -------------------------
    elif "buttonResendAddress" in request.form:
      addr_id = request.form.get("buttonResendAddress","").strip()
      email = request.form.get("address_email","").strip()
      if not addr_id or not email:
        flash('Якісь важливі параметри не були отримані сервером!','alert alert-warning')
        return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
      del_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses/{addr_id}"
      del_result = requests.delete(del_url, headers=headers, timeout=10).json()
      if not del_result.get("success"):
        error_msg = (del_result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_dstaddresses(): Failed to delete destination address {addr_id} (for resend) for account {selected_account}: {del_result.get('errors')}")
        flash(f'Помилка при повторній відправці верифікації для {email}: <strong>{error_msg}</strong>','alert alert-danger')
      else:
        add_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses"
        add_result = requests.post(add_url, headers=headers, json={"email": email}, timeout=10).json()
        if add_result.get("success"):
          logging.info(f"catch_dstaddresses(): Verification resent for destination address {email} (account {selected_account}) by {current_user.realname}")
          flash(f'Лист з верифікацією повторно надіслано на {email}!','alert alert-success')
        else:
          error_msg = (add_result.get("errors", [{}])[0].get("message", "Unknown error"))
          logging.error(f"catch_dstaddresses(): Failed to re-create destination address {email} for account {selected_account}: {add_result.get('errors')}")
          flash(f'Адреса {email} була видалена, але повторне додавання не вдалося: <strong>{error_msg}</strong>','alert alert-danger')
    else:
      flash('Помилка! Ні один з можливих параметрів не був переданий!','alert alert-danger')
      logging.error(f"catch_dstaddresses(): Something strange was received via POST request for account {selected_account} and we can't process that.")
    return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
  except Exception as err:
    logging.error(f"catch_dstaddresses(): general error by {current_user.realname} for account {selected_account}: {err}")
    flash('Неочікувана помилка при обробці запиту! Дивіться логи.','alert alert-danger')
    return redirect(f"/cloudflare_email_dstaddresses/?account={selected_account}",302)
