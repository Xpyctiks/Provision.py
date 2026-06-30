import logging
from flask import Blueprint, render_template, flash, redirect
from flask_login import login_required, current_user
from db.database import CloudflareEmailsStatus, CloudflareEmailsRules
from functions.site_actions import is_admin

cloudflare_email_dashboard_bp = Blueprint("cloudflare_email_dashboard", __name__)

@cloudflare_email_dashboard_bp.route("/cloudflare_email_dashboard/", methods=['GET'])
@login_required
def show_cloudflare_email_dashboard():
  """GET request: shows a combined dashboard of Email Routing status (CloudflareEmailsStatus) and rules (CloudflareEmailsRules) for every domain known in the DB"""
  try:
    statuses = CloudflareEmailsStatus.query.order_by(CloudflareEmailsStatus.domain).all()
    rules_by_domain = {}
    for rule in CloudflareEmailsRules.query.order_by(CloudflareEmailsRules.domain).all():
      rules_by_domain.setdefault(rule.domain, []).append(rule.rule)
    if not statuses:
      rows_html = '<tr><td colspan="5" class="text-center text-muted">Дані відсутні. Зачекайте на синхронізацію Email Routing або відкрийте керування для потрібного домену.</td></tr>'
    else:
      rows_html = ""
      for i, s in enumerate(statuses, 1):
        domain_rules = rules_by_domain.get(s.domain, [])
        if s.routing_enabled:
          status_badge = '<span class="badge bg-success">✅ Увімкнено</span>'
        else:
          status_badge = '<span class="badge bg-secondary">📪 Вимкнено</span>'
        if domain_rules:
          rules_items = "".join(f"<li>{rule}</li>" for rule in domain_rules)
          rules_cell = f"""<button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#rules{s.id}">{len(domain_rules)} шт. ▾</button>
          <div class="collapse mt-2" id="rules{s.id}"><ul class="mb-0 text-start small">{rules_items}</ul></div>"""
        else:
          rules_cell = '<span class="text-muted">немає правил</span>'
        updated_cell = s.updated.strftime('%d-%m-%Y %H:%M') if s.updated else ''
        if s.updatedby:
          updated_cell += f' ({s.updatedby})'
        rows_html += f"""
  <tr>
    <th scope="row">{i}</th>
    <td><a href="https://{s.domain}" target="_blank">{s.domain}</a></td>
    <td>{status_badge}</td>
    <td>{rules_cell}</td>
    <td>{updated_cell}</td>
    <td><a class="btn btn-sm btn-secondary" href="/cloudflare_email/manage?domain={s.domain}" title="Перегляд та керування Email Routing для цього домену.">⚙Керувати</a></td>
  </tr>"""
    return render_template("template-cloudflare_email_dashboard.html", rows_html=rows_html, admin_panel=is_admin())
  except Exception as err:
    logging.error(f"show_cloudflare_email_dashboard(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при завантаженні дашборду Email Routing! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)
