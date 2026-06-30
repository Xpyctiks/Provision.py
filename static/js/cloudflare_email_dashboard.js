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

function applyAccountFilter() {
  const accountFilter = document.getElementById("accountFilter");
  if (!accountFilter) {
    return;
  }
  const account = accountFilter.value.toLowerCase();
  document.querySelectorAll("#emailDashboardTable tbody tr").forEach(row => {
    const rowAccount = (row.dataset.account || "").toLowerCase();
    row.style.display = (!account || rowAccount === account) ? "" : "none";
  });
}

document.addEventListener("DOMContentLoaded", function () {
  const accountFilter = document.getElementById("accountFilter");
  if (accountFilter) {
    accountFilter.addEventListener("change", applyAccountFilter);
  }
});

function parseSortDate(text) {
  const match = text.trim().match(/^(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})/);
  if (!match) {
    return 0;
  }
  const [, day, month, year, hours, minutes] = match;
  return new Date(year, month - 1, day, hours, minutes).getTime();
}

document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("emailDashboardTable");
  if (!table) {
    return;
  }
  const headers = table.querySelectorAll("th.sortable");
  headers.forEach((header) => {
    const realIndex = Array.from(header.parentElement.children).indexOf(header);
    header.addEventListener("click", function () {
      const sortType = header.dataset.sortType || "text";
      const isAscending = !header.classList.contains("sort-asc");
      headers.forEach(h => h.classList.remove("sort-asc", "sort-desc"));
      header.classList.add(isAscending ? "sort-asc" : "sort-desc");

      const tbody = table.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr")).filter(row => row.children.length > realIndex);

      rows.sort((rowA, rowB) => {
        const cellA = rowA.children[realIndex].innerText.trim();
        const cellB = rowB.children[realIndex].innerText.trim();
        let result;
        if (sortType === "date") {
          result = parseSortDate(cellA) - parseSortDate(cellB);
        } else {
          result = cellA.localeCompare(cellB, "uk");
        }
        return isAscending ? result : -result;
      });

      rows.forEach(row => tbody.appendChild(row));
      tbody.querySelectorAll("tr").forEach((row, i) => {
        const numberCell = row.querySelector("th[scope='row']");
        if (numberCell) {
          numberCell.textContent = i + 1;
        }
      });
    });
  });
});
