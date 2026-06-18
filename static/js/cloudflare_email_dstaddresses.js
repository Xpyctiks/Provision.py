document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll('.dropdown-item.account').forEach(item => {
  item.addEventListener('click', function () {
    showLoading();
    let value = this.getAttribute('data-value');
    window.location.href = '/cloudflare_email_dstaddresses/?account=' + encodeURIComponent(value);
  });
});

function showLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) {
    spinner.style.visibility = "visible";
  }
}

function hideLoading() {
  const spinner = document.getElementById("spinnerLoading");
  if (spinner) {
    spinner.style.visibility = "hidden";
  } else {
    console.warn("Spinner element not found!");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  hideLoading();
});

window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
    hideLoading();
  }
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})

document.addEventListener("submit", function (e) {
  const btn = e.submitter;
  if (!btn) {
    return;
  }
  if (btn.classList.contains("DeleteAddress-btn")) {
    if (!confirm("⚠Видалити цю адресу призначення?")) {
      e.preventDefault();
      hideLoading();
    }
  }
  if (btn.classList.contains("ResendAddress-btn")) {
    if (!confirm("⚠Адреса буде видалена та додана знову, щоб Cloudflare повторно надіслав листа з верифікацією. Продовжити?")) {
      e.preventDefault();
      hideLoading();
    }
  }
});
