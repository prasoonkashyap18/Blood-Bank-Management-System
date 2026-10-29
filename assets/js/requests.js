/**
 * Blood requests page: real, database-backed request submission, a "my
 * requests" view for any logged-in user, and an admin-only panel to
 * search/filter all requests and change their status (Approve/Reject/
 * Fulfilled), wired to the inventory-deduction backend.
 */

const REQUEST_STATUS_VARIANT = { Pending: "secondary", Approved: "info", Fulfilled: "success", Rejected: "danger" };
const REQUEST_URGENCY_VARIANT = { Critical: "danger", High: "warning", Medium: "info", Low: "secondary" };

function requestStatusBadge(status) {
  return badgeHtml(status, REQUEST_STATUS_VARIANT[status] || "secondary");
}
function requestUrgencyBadge(urgency) {
  return badgeHtml(urgency, REQUEST_URGENCY_VARIANT[urgency] || "secondary");
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("requestForm");
  if (!form) return; // not on the requests page

  const formError = document.getElementById("requestError");
  const formSuccess = document.getElementById("requestSuccess");
  const loginPrompt = document.getElementById("requestLoginPrompt");
  const formCard = document.getElementById("requestFormCard");

  const myRequestsCard = document.getElementById("myRequestsCard");
  const myRequestsBody = document.getElementById("myRequestsBody");
  const myRequestsEmpty = document.getElementById("myRequestsEmpty");

  const adminPanel = document.getElementById("adminRequestsPanel");
  const adminTableBody = document.getElementById("adminRequestsBody");
  const adminEmpty = document.getElementById("adminRequestsEmpty");
  const adminStatusFilter = document.getElementById("adminStatusFilter");
  const adminBloodGroupFilter = document.getElementById("adminBloodGroupFilter");
  const adminDateFrom = document.getElementById("adminDateFrom");
  const adminDateTo = document.getElementById("adminDateTo");
  const adminClearBtn = document.getElementById("adminFilterClearBtn");

  let currentUser = null;

  async function loadMyRequests() {
    const { ok, data } = await apiRequest("/api/requests?limit=50");
    if (!ok) return;
    if (data.requests.length === 0) {
      myRequestsBody.innerHTML = "";
      myRequestsEmpty.classList.remove("d-none");
      return;
    }
    myRequestsEmpty.classList.add("d-none");
    myRequestsBody.innerHTML = data.requests.map((r) => `
      <tr>
        <td class="small text-secondary">#${r.id}</td>
        <td><span class="badge text-bg-danger-subtle text-danger-emphasis border border-danger-subtle">${r.bloodGroup}</span></td>
        <td>${r.quantityUnits}</td>
        <td>${requestUrgencyBadge(r.urgency)}</td>
        <td>${requestStatusBadge(r.status)}</td>
        <td class="small text-secondary">${r.rejectionReason ? escapeHtml(r.rejectionReason) : "—"}</td>
      </tr>
    `).join("");
  }

  async function loadAdminRequests() {
    const params = new URLSearchParams({ limit: 50 });
    if (adminStatusFilter.value) params.set("status", adminStatusFilter.value);
    if (adminBloodGroupFilter.value) params.set("bloodGroup", adminBloodGroupFilter.value);
    if (adminDateFrom.value) params.set("dateFrom", adminDateFrom.value);
    if (adminDateTo.value) params.set("dateTo", adminDateTo.value);

    const { ok, data } = await apiRequest(`/api/requests?${params.toString()}`);
    if (!ok) return;

    if (data.requests.length === 0) {
      adminTableBody.innerHTML = "";
      adminEmpty.classList.remove("d-none");
      return;
    }
    adminEmpty.classList.add("d-none");

    adminTableBody.innerHTML = data.requests.map((r) => {
      const canApprove = r.status === "Pending";
      const canReject = r.status === "Pending" || r.status === "Approved";
      const canFulfill = r.status === "Approved";
      return `
        <tr>
          <td class="small text-secondary">#${r.id}</td>
          <td>${escapeHtml(r.requesterName)}<br><span class="text-secondary small">${escapeHtml(r.requesterContact)}</span></td>
          <td><span class="badge text-bg-danger-subtle text-danger-emphasis border border-danger-subtle">${r.bloodGroup}</span></td>
          <td>${r.quantityUnits}</td>
          <td>${escapeHtml(r.location)}</td>
          <td>${requestUrgencyBadge(r.urgency)}</td>
          <td>${requestStatusBadge(r.status)}${r.rejectionReason ? `<div class="small text-secondary">${escapeHtml(r.rejectionReason)}</div>` : ""}</td>
          <td class="text-end text-nowrap">
            ${canApprove ? `<button type="button" class="btn btn-sm btn-outline-success me-1" data-action="approve" data-id="${r.id}">Approve</button>` : ""}
            ${canFulfill ? `<button type="button" class="btn btn-sm btn-bb-primary me-1" data-action="fulfill" data-id="${r.id}">Fulfill</button>` : ""}
            ${canReject ? `<button type="button" class="btn btn-sm btn-outline-danger" data-action="reject" data-id="${r.id}">Reject</button>` : ""}
          </td>
        </tr>
      `;
    }).join("");

    adminTableBody.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => handleAdminAction(btn.dataset.action, btn.dataset.id, btn));
    });
  }

  async function handleAdminAction(action, requestId, btn) {
    let payload = { status: "" };
    if (action === "approve") payload.status = "Approved";
    if (action === "fulfill") payload.status = "Fulfilled";
    if (action === "reject") {
      const reason = window.prompt("Reason for rejecting this request:");
      if (reason === null) return; // cancelled
      if (!reason.trim()) {
        window.alert("A rejection reason is required.");
        return;
      }
      payload = { status: "Rejected", rejectionReason: reason.trim() };
    }

    btn.disabled = true;
    const { ok, data } = await apiRequest(`/api/requests/${requestId}`, { method: "PATCH", body: payload });
    if (!ok) {
      window.alert((data && data.error) || "That action could not be completed.");
    }
    await loadAdminRequests();
  }

  [adminStatusFilter, adminBloodGroupFilter].forEach((el) => el && el.addEventListener("change", loadAdminRequests));
  [adminDateFrom, adminDateTo].forEach((el) => el && el.addEventListener("change", loadAdminRequests));
  if (adminClearBtn) {
    adminClearBtn.addEventListener("click", () => {
      adminStatusFilter.value = "";
      adminBloodGroupFilter.value = "";
      adminDateFrom.value = "";
      adminDateTo.value = "";
      loadAdminRequests();
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlertEl(formError);
    hideAlertEl(formSuccess);

    if (!form.checkValidity()) {
      form.classList.add("was-validated");
      return;
    }
    form.classList.add("was-validated");

    const payload = {
      requesterName: document.getElementById("reqName").value.trim(),
      requesterContact: document.getElementById("reqContact").value.trim(),
      bloodGroup: document.getElementById("reqBloodGroup").value,
      quantityUnits: parseInt(document.getElementById("reqUnits").value, 10),
      location: document.getElementById("reqCity").value.trim(),
      urgency: document.getElementById("reqUrgency").value,
      notes: document.getElementById("reqNotes").value.trim(),
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    try {
      const { ok, data } = await apiRequest("/api/requests", { method: "POST", body: payload });
      if (ok) {
        showAlertEl(formSuccess, `Request #${data.request.id} submitted and is now Pending review.`, "success");
        form.reset();
        form.classList.remove("was-validated");
        await loadMyRequests();
        if (currentUser && currentUser.role === "admin") await loadAdminRequests();
      } else {
        const messages = data && data.fields ? Object.values(data.fields).join(" ") : (data && data.error) || "Could not submit this request.";
        showAlertEl(formError, messages, "danger");
      }
    } finally {
      submitBtn.disabled = false;
    }
  });

  function showAlertEl(el, message, kind) {
    if (!el) return;
    el.textContent = message;
    el.className = `alert alert-${kind}`;
    el.classList.remove("d-none");
  }
  function hideAlertEl(el) {
    if (el) el.classList.add("d-none");
  }

  async function init() {
    const { ok, data } = await apiRequest("/api/auth/me");
    currentUser = ok ? data.user : null;

    if (!currentUser) {
      formCard.classList.add("d-none");
      myRequestsCard.classList.add("d-none");
      loginPrompt.classList.remove("d-none");
      return;
    }
    formCard.classList.remove("d-none");
    myRequestsCard.classList.remove("d-none");
    loginPrompt.classList.add("d-none");

    await loadMyRequests();

    if (currentUser.role === "admin") {
      adminPanel.classList.remove("d-none");
      await loadAdminRequests();
    }
  }

  init();
});
