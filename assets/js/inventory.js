/**
 * Blood inventory page: real, database-backed summary (public) plus an
 * admin-only batch management panel (view/add/correct/archive batches).
 *
 * Relies on assets/js/auth.js for apiRequest/escapeHtml/badgeHtml, already
 * loaded earlier on the page.
 */

let inventorySummaryCache = [];

function stockStatusBadge(group) {
  if (group.outOfStock) return badgeHtml("Out of stock", "danger");
  if (group.lowStock) return badgeHtml("Low", "warning");
  return badgeHtml("Available", "success");
}

function expiryStatusBadge(status) {
  if (status === "expired") return badgeHtml("Expired", "danger");
  if (status === "near_expiry") return badgeHtml("Near expiry", "warning");
  return badgeHtml("Usable", "success");
}

document.addEventListener("DOMContentLoaded", () => {
  const summaryEl = document.getElementById("inventorySummary");
  const alertsEl = document.getElementById("inventoryAlerts");
  const invSearch = document.getElementById("invSearch");
  const statusFilter = document.getElementById("statusFilter");
  const invClearBtn = document.getElementById("invClearBtn");
  const tableBody = document.getElementById("inventoryTableBody");
  const emptyState = document.getElementById("invEmptyState");
  const loadingState = document.getElementById("invLoadingState");
  const errorState = document.getElementById("invErrorState");

  if (!tableBody) return; // not on the inventory page

  async function loadSummary() {
    loadingState.classList.remove("d-none");
    errorState.classList.add("d-none");

    const { ok, data } = await apiRequest("/api/inventory/summary");
    loadingState.classList.add("d-none");

    if (!ok) {
      errorState.classList.remove("d-none");
      return;
    }

    inventorySummaryCache = data.summary.groups;
    renderStatCards(data.summary);
    renderAlerts(data.summary);
    renderTable();
  }

  function renderStatCards(summary) {
    const cards = [
      { label: "Usable units (all groups)", value: summary.totals.usableUnits, icon: "bi-droplet-half" },
      { label: "Blood groups tracked", value: summary.groups.length, icon: "bi-grid-3x3-gap" },
      { label: "Low / out-of-stock groups", value: summary.lowStockGroups.length + summary.outOfStockGroups.length, icon: "bi-exclamation-triangle" },
      { label: "Units expiring soon", value: summary.totals.nearExpiryUnits, icon: "bi-hourglass-split" },
    ];
    summaryEl.innerHTML = cards.map((c) => `
      <div class="col-6 col-lg-3">
        <div class="bb-card stat-card p-4 h-100">
          <i class="bi ${c.icon} text-danger fs-4 mb-2 d-block"></i>
          <div class="stat-value">${c.value}</div>
          <div class="stat-label">${c.label}</div>
        </div>
      </div>
    `).join("");
  }

  function renderAlerts(summary) {
    const parts = [];
    if (summary.outOfStockGroups.length) {
      parts.push(`<div class="alert alert-danger py-2 px-3 mb-2"><i class="bi bi-x-octagon me-1"></i>Out of stock: ${summary.outOfStockGroups.join(", ")}</div>`);
    }
    if (summary.lowStockGroups.length) {
      parts.push(`<div class="alert alert-warning py-2 px-3 mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Low stock (below ${summary.thresholds.lowStockThreshold} units): ${summary.lowStockGroups.join(", ")}</div>`);
    }
    if (summary.totals.expiredUnits > 0) {
      parts.push(`<div class="alert alert-secondary py-2 px-3 mb-2"><i class="bi bi-calendar-x me-1"></i>${summary.totals.expiredUnits} expired units recorded and excluded from usable stock.</div>`);
    }
    alertsEl.innerHTML = parts.join("");
  }

  function renderTable() {
    const query = invSearch.value.trim().toUpperCase();
    const status = statusFilter.value;

    const filtered = inventorySummaryCache.filter((g) => {
      const matchesQuery = !query || g.bloodGroup.includes(query);
      const matchesStatus =
        !status ||
        (status === "Available" && !g.lowStock && !g.outOfStock) ||
        (status === "Low" && g.lowStock) ||
        (status === "OutOfStock" && g.outOfStock);
      return matchesQuery && matchesStatus;
    });

    if (filtered.length === 0) {
      tableBody.innerHTML = "";
      emptyState.classList.remove("d-none");
      return;
    }
    emptyState.classList.add("d-none");

    tableBody.innerHTML = filtered.map((g) => `
      <tr>
        <td class="fw-medium">${g.bloodGroup}</td>
        <td>${g.usableUnits} units</td>
        <td class="text-secondary">${g.totalRecordedUnits} units</td>
        <td class="text-secondary">${g.batchCount}</td>
        <td>${stockStatusBadge(g)}</td>
        <td class="text-secondary">${g.nearExpiryUnits > 0 ? `${g.nearExpiryUnits} units` : "—"}</td>
        <td class="text-secondary">${g.expiredUnits > 0 ? `${g.expiredUnits} units` : "—"}</td>
      </tr>
    `).join("");
  }

  invSearch.addEventListener("input", renderTable);
  statusFilter.addEventListener("change", renderTable);
  invClearBtn.addEventListener("click", () => {
    invSearch.value = "";
    statusFilter.value = "";
    renderTable();
  });

  loadSummary();

  // -----------------------------------------------------------------------
  // Admin-only batch management panel
  // -----------------------------------------------------------------------

  const adminPanel = document.getElementById("adminInventoryPanel");
  const batchForm = document.getElementById("addBatchForm");
  const batchFormError = document.getElementById("addBatchError");
  const batchFormSuccess = document.getElementById("addBatchSuccess");
  const batchTableBody = document.getElementById("adminBatchTableBody");

  async function initAdminPanelIfAdmin() {
    const { ok, data } = await apiRequest("/api/auth/me");
    if (!ok || data.user.role !== "admin") return;
    adminPanel.classList.remove("d-none");
    await loadBatches();
  }

  async function loadBatches() {
    const { ok, data } = await apiRequest("/api/inventory");
    if (!ok) return;
    batchTableBody.innerHTML = data.batches.map((b) => `
      <tr>
        <td>${b.bloodGroup}</td>
        <td>${b.quantityUnits}</td>
        <td class="text-secondary small">${b.collectedDate || "—"}</td>
        <td class="text-secondary small">${b.expiryDate || "—"}</td>
        <td>${expiryStatusBadge(b.expiryStatus)}</td>
        <td>${b.status === "archived" ? badgeHtml("Archived", "secondary") : badgeHtml("Active", "success")}</td>
        <td class="text-secondary small">${b.notes ? escapeHtml(b.notes) : "—"}</td>
        <td class="text-end">
          ${b.status === "active"
            ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-archive-batch="${b.id}">Archive</button>`
            : ""}
        </td>
      </tr>
    `).join("");

    batchTableBody.querySelectorAll("[data-archive-batch]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        await apiRequest(`/api/inventory/${btn.dataset.archiveBatch}`, {
          method: "PATCH",
          body: { status: "archived", notes: "Archived from the inventory admin panel." },
        });
        await loadBatches();
        await loadSummary();
      });
    });
  }

  if (batchForm) {
    batchForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      batchFormError.classList.add("d-none");
      batchFormSuccess.classList.add("d-none");

      if (!batchForm.checkValidity()) {
        batchForm.classList.add("was-validated");
        return;
      }
      batchForm.classList.add("was-validated");

      const payload = {
        bloodGroup: document.getElementById("batchBloodGroup").value,
        quantityUnits: parseInt(document.getElementById("batchQuantity").value, 10),
        collectedDate: document.getElementById("batchCollectedDate").value,
        expiryDate: document.getElementById("batchExpiryDate").value,
        notes: document.getElementById("batchNotes").value,
      };

      const submitBtn = batchForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      try {
        const { ok, data } = await apiRequest("/api/inventory", { method: "POST", body: payload });
        if (ok) {
          batchFormSuccess.textContent = `Batch added: ${payload.quantityUnits} units of ${payload.bloodGroup}.`;
          batchFormSuccess.classList.remove("d-none");
          batchForm.reset();
          batchForm.classList.remove("was-validated");
          await loadBatches();
          await loadSummary();
        } else {
          const messages = data && data.fields ? Object.values(data.fields).join(" ") : (data && data.error) || "Could not add this batch.";
          batchFormError.textContent = messages;
          batchFormError.classList.remove("d-none");
        }
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  initAdminPanelIfAdmin();
});
