document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll('.dropdown-item.account').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_account').value = value2;
    document.getElementById('Account').innerText = value2;
  });
}); 

document.querySelectorAll('.dropdown-item.server').forEach(item => {
  item.addEventListener('click', function () {
    let value2 = this.getAttribute('data-value');
    document.getElementById('selected_server').value = value2;
    document.getElementById('Server').innerText = value2;
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
