document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
});

document.querySelectorAll(".delete-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    const mainSite = btn.dataset.site;
    const selectedSites = Array.from(
      document.querySelectorAll(".selected-site:checked")
    ).map(chk => chk.value);
    if (!selectedSites.includes(mainSite)) {
      selectedSites.push(mainSite);
    }
    const sitesList = selectedSites.join(", ");
    if (!confirm(`Ви дійсно хочете видалити наступні сайти?\n\n${sitesList}`)) {
      e.preventDefault();
      hideLoading();
    }
  });
});

document.querySelectorAll(".gitpull-btn").forEach(btn => {
  btn.addEventListener("click", e => {
    const mainSite = btn.dataset.site;
    const selectedSites = Array.from(
      document.querySelectorAll(".selected-site:checked")
    ).map(chk => chk.value);
    if (!selectedSites.includes(mainSite)) {
      selectedSites.push(mainSite);
    }
    const sitesList = selectedSites.join(", ");
    if (!confirm(`Оновити код до актуального на наступних сайтах?\n\n${sitesList}`)) {
      e.preventDefault();
      hideLoading();
      }
    });
});

document.addEventListener('show.bs.collapse', async function (event) {
  let button = event.target.previousElementSibling.querySelector("button");
  let path = button.dataset.path;
  let body = event.target.querySelector(".accordion-body");
  body.innerHTML = "Завантажую...";
  let response = await fetch(`/action/show/hrefhistory?domain=${encodeURIComponent(path)}`);
  let html = await response.text();
  body.innerHTML = html;
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
  overlayLoader();
});

window.addEventListener("pageshow", function (event) {
  if (event.persisted) {
  hideLoading();
  }
});

const checkboxes = document.querySelectorAll('.chk');
let lastChecked = null;
checkboxes.forEach(chk => {
  chk.addEventListener('click', function (e) {
  if (e.shiftKey && lastChecked) {
    let inRange = false;
    checkboxes.forEach(box => {
    if (box === this || box === lastChecked) {
      inRange = !inRange;
    }
    if (inRange) {
      box.checked = lastChecked.checked;
    }
    });
  }
  lastChecked = this;
  });
});

function checkAll(bx) {
  document.querySelectorAll("tbody tr").forEach(row => {
    if (row.style.display !== "none") {
      row.querySelectorAll("input[type=checkbox]").forEach(cb => {
        cb.checked = bx.checked;
      });
    }
  });
}

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})

let errorsOnly = false;

let domain = null;
function openEditor(domain) {
  fetch(`/robots/?domain=${encodeURIComponent(domain)}`)
  .then(response => response.json())
  .then(data => {
    document.getElementById("editorTextarea").value = data.content;
    document.getElementById("domain").value = domain
  })
  .catch(err => {
    alert("Помилка завантаження");
    console.error(err);
  });
}

function saveEditor() {
  const content = document.getElementById("editorTextarea").value;
  const domain = document.getElementById("domain").value;
  fetch("/robots/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      domain: domain,
      content: content
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.status === "ok") {
      alert("Збережено");
      bootstrap.Modal.getInstance(
        document.getElementById('editorModal')
      ).hide();
    } else {
      alert(data.error);
    }
  });
}

document.querySelectorAll(".buttonSetHref").forEach(btn => {
  btn.addEventListener("click", () => {
    const slugInput = document.getElementById(btn.dataset.slugId);
    const hreflangInput = document.getElementById(btn.dataset.hreflangId);
    const slug = slugInput.value.trim();
    const hreflang = hreflangInput.value.trim();

    slugInput.classList.toggle("is-invalid", slug === "");
    hreflangInput.classList.toggle("is-invalid", hreflang === "");
    if (slug === "" || hreflang === "") {
      return;
    }

    const formData = new FormData();
    formData.append("slug", slug);
    formData.append("hreflang", hreflang);
    formData.append("action", "page_clone_home");

    fetch(`https://${btn.dataset.site}/api/`, {
      method: "POST",
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      alert("Збережено");
    })
    .catch(err => {
      alert("Помилка надсилання запиту");
      console.error(err);
    });
  });
});

const btn = document.getElementById("scrollTopBtn");
window.addEventListener("scroll", () => {
  if (window.scrollY > 300) {
    btn.style.display = "block";
  } else {
    btn.style.display = "none";
  }
});

btn.addEventListener("click", () => {
  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
});

function applyFilters() {
  const owner = document.getElementById("ownerFilter").value.toLowerCase();
  const account = document.getElementById("accountFilter").value.toLowerCase();
  const text = (document.getElementById("siteFilter")?.value || "").toLowerCase();
  document.querySelectorAll("tbody tr").forEach(row => {
    const rowOwners = (row.dataset.owner || "").toLowerCase().split(/\s+/);
    const rowAccounts = (row.dataset.account || "").toLowerCase().split(/\s+/);
    const rowText = row.innerText.toLowerCase();
    const matchOwner = !owner || rowOwners.includes(owner);
    const matchAccount = !account || rowAccounts.includes(account);
    const matchText = !text || rowText.includes(text);
    const matchErrors = !errorsOnly || row.dataset.cfError === "1";
    row.style.display =
      (matchOwner && matchAccount && matchText && matchErrors) ? "" : "none";
  });
}

document.getElementById("ownerFilter").addEventListener("change", applyFilters);
document.getElementById("accountFilter").addEventListener("change", applyFilters);
document.getElementById("siteFilter").addEventListener("input", applyFilters);

function clearFilters() {
  const siteFilter  = document.getElementById("siteFilter");
  if (siteFilter) siteFilter.value = "";
  if (errorsOnly) {
    errorsOnly = false;
    const cfErrorIcon = document.getElementById("cfErrorIcon");
    if (cfErrorIcon) cfErrorIcon.style.opacity = "1";
  }
  applyFilters();
}

document.addEventListener("DOMContentLoaded", function () {
  const cfErrorIcon = document.getElementById("cfErrorIcon");
  if (cfErrorIcon) {
    cfErrorIcon.addEventListener("click", function () {
      errorsOnly = !errorsOnly;
      cfErrorIcon.style.opacity = errorsOnly ? "0.5" : "1";
      cfErrorIcon.title = errorsOnly ? "Показати всі сайти (скинути фільтр)" : "Є проблеми з Cloudflare у деяких сайтів!";
      applyFilters();
    });
  }
});

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    clearFilters();
  }
});

function overlayLoader() {
  const overlayLoader = document.getElementById("overlayLoader");
  overlayLoader.classList.add("d-none");
}

document.addEventListener("DOMContentLoaded", function () {
  const value = document.cookie
    .split('; ')
    .find(row => row.startsWith('x_cache='));

  if (value && value.split('=')[1] === "HIT") {
    document.getElementById("cacheIcon")
      .classList.remove("d-none");
  }
});
