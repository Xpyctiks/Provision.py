// ── Shift-click range selection for checkbox lists/tables (shared by all pages) ──
// Click one checkbox, hold Shift and click another one - every checkbox of the same group between them gets the
// state of the last clicked one. Works with lists rendered later via AJAX (event delegation on document).
// Group = checkboxes with the same "name" attribute (or, if there's no name, the same set of CSS classes), so
// "select all" checkboxes and unrelated checkboxes on the same page never get pulled into a range.
// Only visible, enabled checkboxes are affected (respects search/filters that hide rows).
// Every changed checkbox gets a bubbling "change" event, so page counters/buttons/selection state update as usual.
(function () {
  const anchors = new Map();   // group key -> last clicked checkbox

  function groupKey(cb) {
    const name = cb.getAttribute("name");
    if (name) return "name:" + name + "|form:" + (cb.getAttribute("form") || "");
    return "class:" + Array.from(cb.classList).sort().join(".");
  }

  function isUsable(cb) {
    return !cb.disabled && cb.getClientRects().length > 0;
  }

  function groupMembers(key) {
    return Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(cb => isUsable(cb) && groupKey(cb) === key);
  }

  //Shift+mousedown would otherwise select page text between the two clicks
  document.addEventListener("mousedown", function (e) {
    if (e.shiftKey && e.target instanceof HTMLInputElement && e.target.type === "checkbox") {
      e.preventDefault();
    }
  });

  document.addEventListener("click", function (e) {
    const cb = e.target;
    if (!(cb instanceof HTMLInputElement) || cb.type !== "checkbox" || cb.disabled) return;
    const key = groupKey(cb);
    const anchor = anchors.get(key);
    if (e.shiftKey && anchor && anchor !== cb && document.contains(anchor)) {
      const members = groupMembers(key);
      const from = members.indexOf(anchor);
      const to = members.indexOf(cb);
      if (from !== -1 && to !== -1) {
        const [start, end] = from < to ? [from, to] : [to, from];
        for (let i = start; i <= end; i++) {
          const box = members[i];
          if (box === cb || box.checked === cb.checked) continue;
          box.checked = cb.checked;
          box.dispatchEvent(new Event("change", { bubbles: true }));
        }
        const sel = window.getSelection();
        if (sel) sel.removeAllRanges();
      }
    }
    anchors.set(key, cb);
  });
})();
