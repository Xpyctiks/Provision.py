document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll(".SaveSettings-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    if (!confirm(`Зберіти нові налаштування?`)) {
      e.preventDefault();
      hideLoading();
    }
  });
});

document.querySelectorAll(".DeleteUser-btn").forEach(btn => {
  btn.addEventListener("click", e => {
  if (!confirm(`Видалити користувача?`)) {
    e.preventDefault();
    hideLoading();
    }
  });
});

document.querySelectorAll(".DeleteTemplate-btn").forEach(btn => {
  btn.addEventListener("click", e => {
  if (!confirm(`Видалити обраний шаблон?`)) {
    e.preventDefault();
    hideLoading();
    }
  });
});

document.querySelectorAll(".DefaultTemplate-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    if (!confirm(`Зробити обраний шаблон за замовчуванням?`)) {
      e.preventDefault();
      hideLoading();
    }
  });
});

document.querySelectorAll(".AdminUser-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    if (!confirm(`Змінити статус користувача?`)) 
    {
      e.preventDefault();
      hideLoading();
    }
  });
});

document.querySelectorAll(".PublishMessage-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    if (!confirm(`Опублікувати повідомлення для всіх?`)) 
    {
      e.preventDefault();
      hideLoading();
    }
  });
});

document.querySelectorAll(".ClearMessages-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    if (!confirm(`Видалити АБСОЛЮТНО всі очікуючі повідомлення із базі?`)) 
    {
      e.preventDefault();
      hideLoading();
    }
  });
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

function syncSettings() {
  const map = [
    ['settings-0', 'value-0'],
    ['settings-1', 'value-1'],
    ['settings-2', 'value-2'],
    ['settings-3', 'value-3'],
    ['settings-4', 'value-4'],
    ['settings-5', 'value-5'],
    ['settings-6', 'value-6'],
    ['settings-7', 'value-7'],
    ['settings-8', 'value-8'],
    ['settings-9', 'value-9'],
    ['settings-10', 'value-10'],
    ['settings-11', 'value-11'],
    ['settings-12', 'value-12'],
    ['settings-13', 'value-13']
  ];

  map.forEach(([srcId, targetId]) => {
    const src = document.getElementById(srcId);
    const target = document.getElementById(targetId);
    if (src && target) {
      target.value = src.value;
    }
  });
  showLoading();
}

const form1 = document.getElementById("postform1");
if (form1) {
  document.getElementById("postform1").addEventListener("submit", function(event) {
    const input = document.getElementById("textform");
    const value = input.value.trim();
    if (value === "") {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
    }
  });
}

const form2 = document.getElementById("postform2");
if (form2) {
  document.getElementById("postform2").addEventListener("submit", function(event) {
    const input = document.getElementById("new-username");
    const value = input.value.trim();
    if (value === "") {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
    }
    const input2 = document.getElementById("new-password");
    const value2 = input2.value.trim();
    if (value2 === "") {
      input2.classList.add("is-invalid");
      input2.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input2.classList.remove("is-invalid");
      input2.classList.add("is-valid");
    }
    const input3 = document.getElementById("new-realname");
    const value3 = input3.value.trim();
    if (value3 === "") {
      input3.classList.add("is-invalid");
      input3.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input3.classList.remove("is-invalid");
      input3.classList.add("is-valid");
    }
  });
}

const form3 = document.getElementById("postform3");
if (form3) {
  document.getElementById("postform3").addEventListener("submit", function(event) {
    const input = document.getElementById("field1");
    const value = input.value.trim();
    if (value === "") {
      input.classList.add("is-invalid");
      input.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
    }
    const input2 = document.getElementById("field2");
    const value2 = input2.value.trim();
    if (value2 === "") {
      input2.classList.add("is-invalid");
      input2.classList.remove("is-valid");
      document.getElementById("spinnerLoading").style.visibility = "hidden";
      event.preventDefault();
    } else {
      input2.classList.remove("is-invalid");
      input2.classList.add("is-valid");
    }
  });
}

function applyFilters() {
  const owner = document.getElementById("accountFilter").value;
  const text  = document.getElementById("domainFilter")?.value || "";

  document.querySelectorAll("tbody tr").forEach(row => {
    const rowOwner = row.dataset.owner || "";
    const rowText  = row.innerText.toLowerCase();

    const matchOwner = !owner || rowOwner === owner;
    const matchText  = !text || rowText.includes(text);

    row.style.display = (matchOwner && matchText) ? "" : "none";
  });
}

document.getElementById("accountFilter").addEventListener("change", applyFilters);
document.getElementById("domainFilter").addEventListener("input", applyFilters);

function clearFilters() {
  const siteFilter  = document.getElementById("domainFilter");
  if (siteFilter) siteFilter.value = "";
  applyFilters();
}

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    clearFilters();
  }
});
