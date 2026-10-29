/**
 * Reports page (admin-only): real inventory/request/donation summaries,
 * a selectable date range, and CSV export buttons that hit the backend
 * export endpoints directly (the browser just navigates to the URL, so
 * the download carries the session cookie and the server does the work).
 */

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("reportsRoot");
  if (!root) return; // not on the reports page

  const accessDenied = document.getElementById("reportsAccessDenied");
  const dateFrom = document.getElementById("reportDateFrom");
  const dateTo = document.getElementById("reportDateTo");
  const applyBtn = document.getElementById("reportApplyBtn");
  const exportRequestsBtn = document.getElementById("exportRequestsBtn");
  const exportDonationsBtn = document.getElementById("exportDonationsBtn");

  function currentQuery() {
    const params = new URLSearchParams();
    if (dateFrom.value) params.set("dateFrom", dateFrom.value);
    if (dateTo.value) params.set("dateTo", dateTo.value);
    return params.toString();
  }

  async function loadInventorySummary() {
    const { ok, data } = await apiRequest("/api/inventory/summary");
    const list = document.getElementById("repInventoryList");
    if (!ok) {
      list.innerHTML = `<li class="text-danger small">Could not load inventory data.</li>`;
      return;
    }
    list.innerHTML = data.summary.groups.map((g) => `
      <li class="d-flex justify-content-between py-1 border-bottom">
        <span>${g.bloodGroup}</span><strong>${g.usableUnits} units</strong>
      </li>
    `).join("") + `
      <li class="d-flex justify-content-between py-1 pt-2"><span>Total usable</span><strong>${data.summary.totals.usableUnits} units</strong></li>
    `;
  }

  async function loadRequestsReport() {
    const { ok, data } = await apiRequest(`/api/reports/requests?${currentQuery()}`);
    const list = document.getElementById("repRequestList");
    const table = document.getElementById("repRequestsTable");
    if (!ok) {
      list.innerHTML = `<li class="text-danger small">Could not load request data.</li>`;
      table.innerHTML = "";
      return;
    }
    const breakdown = data.statusBreakdown;
    list.innerHTML = Object.entries(breakdown).map(([status, s]) => `
      <li class="d-flex justify-content-between py-1 border-bottom">
        <span>${status}</span><strong>${s.count} (${s.units} units)</strong>
      </li>
    `).join("") + `
      <li class="d-flex justify-content-between py-1 pt-2"><span>Total requests</span><strong>${data.totalRequests}</strong></li>
    `;

    table.innerHTML = data.requests.length === 0
      ? `<tr><td colspan="6" class="text-center text-secondary py-4">No requests in this range.</td></tr>`
      : data.requests.map((r) => `
          <tr>
            <td class="small text-secondary">#${r.id}</td>
            <td>${escapeHtml(r.requesterName)}</td>
            <td>${r.bloodGroup}</td>
            <td>${r.quantityUnits}</td>
            <td class="small text-secondary">${r.createdAt.slice(0, 10)}</td>
            <td>${badgeHtml(r.status, { Pending: "secondary", Approved: "info", Fulfilled: "success", Rejected: "danger" }[r.status] || "secondary")}</td>
          </tr>
        `).join("");
  }

  async function loadDonationsReport() {
    const { ok, data } = await apiRequest(`/api/reports/donations?${currentQuery()}`);
    const el = document.getElementById("repDonations");
    if (!ok) {
      el.innerHTML = `<p class="text-danger small mb-0">Could not load donation data.</p>`;
      return;
    }
    el.innerHTML = `
      <li class="d-flex justify-content-between py-1 border-bottom"><span>Donation records</span><strong>${data.totalDonations}</strong></li>
      <li class="d-flex justify-content-between py-1"><span>Total units donated</span><strong>${data.totalUnits}</strong></li>
    `;
  }

  async function loadDonorCount() {
    const { ok, data } = await apiRequest("/api/donors?limit=1");
    const el = document.getElementById("repDonors");
    if (el) el.textContent = ok ? data.total.toLocaleString() : "—";
  }

  async function loadAll() {
    await Promise.all([loadInventorySummary(), loadRequestsReport(), loadDonationsReport(), loadDonorCount()]);
  }

  applyBtn.addEventListener("click", loadAll);
  exportRequestsBtn.addEventListener("click", () => {
    window.location.href = `/api/reports/requests/export?${currentQuery()}`;
  });
  exportDonationsBtn.addEventListener("click", () => {
    window.location.href = `/api/reports/donations/export?${currentQuery()}`;
  });

  async function init() {
    const { ok, data } = await apiRequest("/api/auth/me");
    if (!ok || data.user.role !== "admin") {
      root.classList.add("d-none");
      accessDenied.classList.remove("d-none");
      return;
    }
    await loadAll();
  }

  init();
});
