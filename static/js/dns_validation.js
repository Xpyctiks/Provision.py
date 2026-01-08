document.addEventListener("DOMContentLoaded", function () {
    const modalElement = document.getElementById("myModal");
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})

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

function fillCnameAndSubmit(button) {
  const row = button.closest("tr");
  const cnameCell = row.querySelector(".cname-cell");
  const cnameValue = cnameCell.textContent.trim();
  const cnameInput = document.querySelector('input[name="cname"]');
  cnameInput.value = cnameValue;
  showLoading();
}
