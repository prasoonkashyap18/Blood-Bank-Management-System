/**
 * Admin dashboard (pages/admin.html): replaces the Step 1 mock statistics
 * with real figures from GET /api/admin/summary (Step 4). This page is
 * already gated to authenticated admins by auth.js's guardAdminPage(), so
 * this script only needs to render what that endpoint returns.
 */

const DASH_STATUS_VARIANT = { Pending: "secondary", Approved: "info", Fulfilled: "success", Rejected: "danger" };

document.addEventListener("DOMContentLoaded", () => {
  const statsEl = document.getElementById("adminStats");
  if (!statsEl) return; // not on the admin dashboard page

  const recentRequestsBody = document.getElementById("recentRequestsBody");
  const recentRequestsEmpty = document.getElementById("recentRequestsEmpty");
  const lowStockAlertsEl = document.getElementById("lowStockAlerts");
  const allRequestsBody = document.getElementById("allRequestsBody");
  const adminInventoryBody = document.getElementById("adminInventoryBody");

  async function loadDashboard() {
    const { ok, data } = await apiRequest("/api/admin/summary");
    if (!ok) {
      statsEl.innerHTML = `<div class="col-12"><div class="alert alert-danger mb-0">Could not load dashboard data.</div></div>`;
      return;
    }
    const summary = data.summary;
    renderStats(summary);
    renderRecentRequests(summary.recentRequests);
    renderLowStockAlerts(summary);
    renderAllRequestsTab(summary.recentRequests);
    renderInventoryTab(summary.bloodGroupStock);
  }

  function renderStats(summary) {
    const cards = [
      { label: "Total donors", value: summary.totalDonors, icon: "bi-people-fill" },
      { label: "Available blood units", value: summary.availableUnits, icon: "bi-droplet-half" },
      { label: "Pending requests", value: summary.pendingRequests, icon: "bi-hourglass-split" },
      { label: "Fulfilled requests", value: summary.fulfilledRequests, icon: "bi-check2-circle" },
    ];
    statsEl.innerHTML = cards.map((s) => `
      <div class="col-6 col-xl-3">
        <div class="bb-card stat-card p-4 h-100">
          <i class="bi ${s.icon} text-danger fs-4 mb-2 d-block"></i>
          <div class="stat-value">${s.value}</div>
          <div class="stat-label">${s.label}</div>
        </div>
      </div>
    `).join("");
  }

  function renderRecentRequests(recent) {
    if (!recent || recent.length === 0) {
      recentRequestsBody.innerHTML = "";
      recentRequestsEmpty.classList.remove("d-none");
      return;
    }
    recentRequestsEmpty.classList.add("d-none");
    recentRequestsBody.innerHTML = recent.map((r) => `
      <tr>
        <td class="small text-secondary">#${r.id}</td>
        <td>${escapeHtml(r.requesterName)}</td>
        <td>${r.bloodGroup}</td>
        <td>${badgeHtml(r.status, DASH_STATUS_VARIANT[r.status] || "secondary")}</td>
      </tr>
    `).join("");
  }

  function renderLowStockAlerts(summary) {
    const lines = [];
    summary.outOfStockGroups.forEach((bg) => lines.push({ bg, label: "Out of stock", variant: "danger" }));
    summary.lowStockGroups.forEach((bg) => lines.push({ bg, label: "Low stock", variant: "warning" }));

    lowStockAlertsEl.innerHTML = lines.length
      ? lines.map((l) => `
          <div class="d-flex justify-content-between align-items-center border rounded p-2 mb-2">
            <span><i class="bi bi-exclamation-triangle text-danger me-2"></i>${l.bg}</span>
            ${badgeHtml(l.label, l.variant)}
          </div>
        `).join("") + (summary.nearExpiryUnits > 0
          ? `<p class="small text-secondary mt-2 mb-0"><i class="bi bi-hourglass-split me-1"></i>${summary.nearExpiryUnits} units expiring soon across all groups.</p>`
          : "")
      : `<p class="text-secondary small mb-0">No low-stock alerts right now.</p>`;
  }

  function renderAllRequestsTab(recent) {
    // The "Requests" tab links to the full requests page for search/filter/
    // actions; here it mirrors the same recent-requests data as a quick
    // glance, consistent with "Recent blood requests" on the Overview tab.
    if (!recent || recent.length === 0) {
      allRequestsBody.innerHTML = `<tr><td colspan="6" class="text-center text-secondary py-4">No requests yet.</td></tr>`;
      return;
    }
    allRequestsBody.innerHTML = recent.map((r) => `
      <tr>
        <td class="small text-secondary">#${r.id}</td>
        <td>${escapeHtml(r.requesterName)}</td>
        <td>${r.bloodGroup}</td>
        <td>${r.quantityUnits}</td>
        <td>${badgeHtml(r.urgency, "secondary")}</td>
        <td>${badgeHtml(r.status, DASH_STATUS_VARIANT[r.status] || "secondary")}</td>
      </tr>
    `).join("");
  }

  function renderInventoryTab(groups) {
    adminInventoryBody.innerHTML = groups.map((g) => {
      const variant = g.outOfStock ? "danger" : g.lowStock ? "warning" : "success";
      const label = g.outOfStock ? "Out of stock" : g.lowStock ? "Low" : "Available";
      return `
        <tr>
          <td class="fw-medium">${g.bloodGroup}</td>
          <td>${g.usableUnits} units</td>
          <td>${badgeHtml(label, variant)}</td>
        </tr>
      `;
    }).join("");
  }

  loadDashboard();
});
