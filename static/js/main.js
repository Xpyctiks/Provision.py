document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("myModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }

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
        }
      });
    });
});

document.addEventListener('show.bs.collapse', async function (event) {
  let button = event.target.previousElementSibling.querySelector("button");
  let path = button.dataset.path;
  let body = event.target.querySelector(".accordion-body");
  body.innerHTML = "Завантажую...";
  let response = await fetch(`/action/showstructure/?showstructure=${encodeURIComponent(path)}`);
  let html = await response.text();
  body.innerHTML = html;
});

document.getElementById("closeAll").addEventListener("click", function () {
  document.querySelectorAll(".accordion .collapse.show").forEach(el => {
    let bsCollapse = bootstrap.Collapse.getInstance(el);
    if (!bsCollapse) {
      bsCollapse = new bootstrap.Collapse(el, { toggle: false });
    }
      bsCollapse.hide();
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
  var cbs = document.getElementsByTagName('input');
  for(var i=0; i < cbs.length; i++) {
  if(cbs[i].type == 'checkbox') {
    cbs[i].checked = bx.checked;
  }
  }
}

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})

let domain = null;
function openEditor(domain) {
  fetch(`/robots?domain=${encodeURIComponent(domain)}`)
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
  fetch("/robots", {
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
  const owner = document.getElementById("ownerFilter").value;
  const text  = document.getElementById("siteFilter")?.value || "";

  document.querySelectorAll("tbody tr").forEach(row => {
    const rowOwner = row.dataset.owner || "";
    const rowText  = row.innerText.toLowerCase();

    const matchOwner = !owner || rowOwner === owner;
    const matchText  = !text || rowText.includes(text);

    row.style.display = (matchOwner && matchText) ? "" : "none";
  });
}

document.getElementById("ownerFilter").addEventListener("change", applyFilters);
document.getElementById("siteFilter").addEventListener("input", applyFilters);
