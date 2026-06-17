document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
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
  if (btn.classList.contains("DeleteRule-btn")) {
    if (!confirm("⚠Видалити це правило маршрутизації?")) {
      e.preventDefault();
      hideLoading();
    }
  }
  if (btn.name === "buttonDisableRouting") {
    if (!confirm("⚠Вимкнути Email Routing для цього домену? Вхідна пошта перестане оброблятися.")) {
      e.preventDefault();
      hideLoading();
    }
  }
});
