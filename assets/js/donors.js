/**
 * Donor directory page: real, database-backed search/filter/pagination,
 * plus a donor detail modal with donation history.
 *
 * Relies on assets/js/auth.js having already defined apiRequest/escapeHtml
 * (loaded earlier on the page) and assets/js/mock-data.js only for the
 * canonical BLOOD_GROUPS list used to populate the filter dropdown.
 */

const DONOR_PAGE_SIZE = 10;
let donorPageOffset = 0;
let donorPageTotal = 0;
let donorFetchToken = 0; // guards against an older, slower request overwriting a newer one

const STATUS_BADGE_VARIANT = { pending: "secondary", approved: "success", rejected: "danger" };

function donorStatusBadge(status) {
  const variant = STATUS_BADGE_VARIANT[status] || "secondary";
  return `<span class="badge text-bg-${variant} text-capitalize">${escapeHtml(status)}</span>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const bloodGroupFilter = document.getElementById("bloodGroupFilter");
  const cityFilter = document.getElementById("cityFilter");
  const statusFilter = document.getElementById("statusFilter");
  const searchInput = document.getElementById("searchInput");
  const clearFiltersBtn = document.getElementById("clearFiltersBtn");
  const tableBody = document.getElementById("donorsTableBody");
  const cardList = document.getElementById("donorsCardList");
  const resultsCount = document.getElementById("resultsCount");
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const errorState = document.getElementById("errorState");
  const resultsWrapper = document.getElementById("resultsWrapper");
  const prevPageBtn = document.getElementById("prevPageBtn");
  const nextPageBtn = document.getElementById("nextPageBtn");

  if (!tableBody) return; // not on the donor directory page

  BLOOD_GROUPS.forEach((bg) => {
    bloodGroupFilter.insertAdjacentHTML("beforeend", `<option value="${bg}">${bg}</option>`);
  });

  function currentFilters() {
    return {
      q: searchInput.value.trim(),
      bloodGroup: bloodGroupFilter.value,
      city: cityFilter.value.trim(),
      status: statusFilter.value,
    };
  }

  function renderRows(donors) {
    tableBody.innerHTML = donors.map((d) => `
      <tr>
        <td class="fw-medium">${escapeHtml(d.fullName)}</td>
        <td><span class="badge text-bg-danger-subtle text-danger-emphasis border border-danger-subtle">${d.bloodGroup}</span></td>
        <td>${escapeHtml(d.city)}</td>
        <td>${donorStatusBadge(d.status)}</td>
        <td class="small text-secondary">${d.lastDonationDate ? escapeHtml(d.lastDonationDate) : "—"}</td>
        <td>
          <button type="button" class="btn btn-sm btn-bb-outline" data-view-donor="${d.id}">
            <i class="bi bi-eye me-1"></i>View
          </button>
        </td>
      </tr>
    `).join("");

    cardList.innerHTML = donors.map((d) => `
      <div class="bb-card p-3 mb-3">
        <div class="d-flex justify-content-between align-items-start">
          <h3 class="h6 mb-1">${escapeHtml(d.fullName)}</h3>
          <span class="badge text-bg-danger-subtle text-danger-emphasis border border-danger-subtle">${d.bloodGroup}</span>
        </div>
        <p class="small text-secondary mb-1"><i class="bi bi-geo-alt me-1"></i>${escapeHtml(d.city)}</p>
        <p class="small text-secondary mb-1">${donorStatusBadge(d.status)}</p>
        <p class="small text-secondary mb-2"><i class="bi bi-calendar-event me-1"></i>Last donation: ${d.lastDonationDate ? escapeHtml(d.lastDonationDate) : "—"}</p>
        <button type="button" class="btn btn-sm btn-bb-outline w-100" data-view-donor="${d.id}">
          <i class="bi bi-eye me-1"></i>View details
        </button>
      </div>
    `).join("");

    tableBody.querySelectorAll("[data-view-donor]").forEach((btn) => {
      btn.addEventListener("click", () => openDonorDetail(btn.dataset.viewDonor));
    });
    cardList.querySelectorAll("[data-view-donor]").forEach((btn) => {
      btn.addEventListener("click", () => openDonorDetail(btn.dataset.viewDonor));
    });
  }

  function updatePaginationControls() {
    const shownFrom = donorPageTotal === 0 ? 0 : donorPageOffset + 1;
    const shownTo = Math.min(donorPageOffset + DONOR_PAGE_SIZE, donorPageTotal);
    resultsCount.textContent = donorPageTotal === 0
      ? "No donors found"
      : `Showing ${shownFrom}–${shownTo} of ${donorPageTotal} donors`;
    prevPageBtn.disabled = donorPageOffset === 0;
    nextPageBtn.disabled = shownTo >= donorPageTotal;
  }

  async function loadDonors() {
    const token = ++donorFetchToken;
    loadingState.classList.remove("d-none");
    errorState.classList.add("d-none");
    resultsWrapper.classList.add("d-none");
    emptyState.classList.add("d-none");

    const filters = currentFilters();
    const params = new URLSearchParams({ limit: DONOR_PAGE_SIZE, offset: donorPageOffset });
    if (filters.q) params.set("q", filters.q);
    if (filters.bloodGroup) params.set("bloodGroup", filters.bloodGroup);
    if (filters.city) params.set("city", filters.city);
    if (filters.status) params.set("status", filters.status);

    const { ok, data } = await apiRequest(`/api/donors?${params.toString()}`);
    if (token !== donorFetchToken) return; // a newer request already landed

    loadingState.classList.add("d-none");

    if (!ok) {
      errorState.classList.remove("d-none");
      return;
    }

    donorPageTotal = data.total;
    if (data.donors.length === 0) {
      emptyState.classList.remove("d-none");
      updatePaginationControls();
      return;
    }

    resultsWrapper.classList.remove("d-none");
    renderRows(data.donors);
    updatePaginationControls();
  }

  let debounceHandle = null;
  function scheduleReload() {
    donorPageOffset = 0;
    clearTimeout(debounceHandle);
    debounceHandle = setTimeout(loadDonors, 250);
  }

  searchInput.addEventListener("input", scheduleReload);
  cityFilter.addEventListener("input", scheduleReload);
  bloodGroupFilter.addEventListener("change", scheduleReload);
  statusFilter.addEventListener("change", scheduleReload);

  clearFiltersBtn.addEventListener("click", () => {
    searchInput.value = "";
    bloodGroupFilter.value = "";
    cityFilter.value = "";
    statusFilter.value = "";
    donorPageOffset = 0;
    loadDonors();
  });

  prevPageBtn.addEventListener("click", () => {
    donorPageOffset = Math.max(0, donorPageOffset - DONOR_PAGE_SIZE);
    loadDonors();
  });
  nextPageBtn.addEventListener("click", () => {
    donorPageOffset += DONOR_PAGE_SIZE;
    loadDonors();
  });

  loadDonors();

  // ---------------------------------------------------------------------
  // Donor detail modal
  // ---------------------------------------------------------------------

  const modalEl = document.getElementById("donorDetailModal");
  const bsModal = modalEl ? new bootstrap.Modal(modalEl) : null;
  const modalBody = document.getElementById("donorDetailBody");

  async function openDonorDetail(donorId) {
    if (!bsModal) return;
    modalBody.innerHTML = `
      <div class="text-center py-4 text-secondary">
        <div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading...
      </div>`;
    bsModal.show();

    const { ok, data } = await apiRequest(`/api/donors/${donorId}`);
    if (!ok) {
      modalBody.innerHTML = `<p class="text-danger mb-0">Could not load this donor's details.</p>`;
      return;
    }

    const donor = data.donor;
    const hasPrivateFields = "phone" in donor;

    let html = `
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h3 class="h5 mb-1">${escapeHtml(donor.fullName)}</h3>
          <span class="badge text-bg-danger-subtle text-danger-emphasis border border-danger-subtle me-1">${donor.bloodGroup}</span>
          ${donorStatusBadge(donor.status)}
        </div>
      </div>
      <dl class="row small mb-0">
        <dt class="col-5 col-sm-4 text-secondary">City</dt><dd class="col-7 col-sm-8">${escapeHtml(donor.city)}</dd>
        <dt class="col-5 col-sm-4 text-secondary">Last donation</dt><dd class="col-7 col-sm-8">${donor.lastDonationDate ? escapeHtml(donor.lastDonationDate) : "—"}</dd>
    `;
    if (hasPrivateFields) {
      html += `
        <dt class="col-5 col-sm-4 text-secondary">Phone</dt><dd class="col-7 col-sm-8">${escapeHtml(donor.phone)}</dd>
        <dt class="col-5 col-sm-4 text-secondary">Email</dt><dd class="col-7 col-sm-8">${donor.email ? escapeHtml(donor.email) : "—"}</dd>
      `;
    }
    html += `</dl>`;

    if (!hasPrivateFields) {
      html += `<p class="small text-secondary mt-3 mb-0"><i class="bi bi-lock me-1"></i>Contact details and donation history are only visible to this donor's own account or an administrator.</p>`;
      modalBody.innerHTML = html;
      return;
    }

    html += `<hr><h4 class="h6">Donation history</h4><div id="donorDonationsList" class="small text-secondary">Loading...</div>`;
    modalBody.innerHTML = html;

    const donationsRes = await apiRequest(`/api/donors/${donorId}/donations`);
    const donationsList = document.getElementById("donorDonationsList");
    if (!donationsList) return; // modal was closed/replaced before this resolved

    if (!donationsRes.ok) {
      donationsList.innerHTML = `<p class="text-danger mb-0 small">Could not load donation history.</p>`;
      return;
    }
    const donations = donationsRes.data.donations;
    donationsList.innerHTML = donations.length === 0
      ? `<p class="mb-0">No donation records yet.</p>`
      : `<ul class="list-unstyled mb-0">` + donations.map((d) => `
          <li class="d-flex justify-content-between border-bottom py-1">
            <span>${escapeHtml(d.donationDate)}</span>
            <span>${d.quantityUnits} unit${d.quantityUnits === 1 ? "" : "s"}</span>
          </li>
        `).join("") + `</ul>`;
  }
});
