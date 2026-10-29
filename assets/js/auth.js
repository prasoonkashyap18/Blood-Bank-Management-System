/**
 * Session-aware navigation and real backend-connected login/register forms.
 *
 * This is the only module that talks to the Flask API added in Step 2.
 * Every other page's interactive behaviour (search, filters, demo forms)
 * stays exactly as it was in Step 1 and is untouched by this file.
 */

let cachedCsrfToken = null;

async function getCsrfToken() {
  if (cachedCsrfToken) return cachedCsrfToken;
  const res = await fetch("/api/auth/csrf-token", { credentials: "same-origin" });
  const data = await res.json();
  cachedCsrfToken = data.csrfToken;
  return cachedCsrfToken;
}

async function apiRequest(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  const options = { method, credentials: "same-origin", headers };

  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await getCsrfToken();
    options.body = JSON.stringify(body ?? {});
  }

  const res = await fetch(path, options);
  let data = null;
  try {
    data = await res.json();
  } catch (_err) {
    data = null;
  }
  return { ok: res.ok, status: res.status, data };
}

function rootPrefix() {
  return document.body.dataset.pagesPrefix || "";
}

function setFormLoading(form, loading) {
  const btn = form.querySelector('button[type="submit"]');
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    btn.dataset.originalText = btn.dataset.originalText || btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Please wait...';
  } else if (btn.dataset.originalText) {
    btn.innerHTML = btn.dataset.originalText;
  }
}

function showAlert(el, message, kind) {
  if (!el) return;
  el.textContent = message;
  el.className = `alert alert-${kind}`;
  el.classList.remove("d-none");
}

function hideAlert(el) {
  if (!el) return;
  el.classList.add("d-none");
}

function fieldErrorMessages(fields) {
  if (!fields) return "";
  return Object.values(fields).join(" ");
}

// ---------------------------------------------------------------------------
// Session-aware navbar
// ---------------------------------------------------------------------------

async function renderAuthNav() {
  const area = document.getElementById("authNavArea");
  const adminItem = document.getElementById("adminNavItem");
  const prefix = rootPrefix();

  const { ok, data } = await apiRequest("/api/auth/me");
  const user = ok ? data.user : null;

  if (adminItem) {
    adminItem.classList.toggle("d-none", !(user && user.role === "admin"));
  }

  if (!area) return;

  if (user) {
    const firstName = user.fullName.split(" ")[0];
    area.innerHTML = `
      <span class="small text-secondary d-none d-lg-inline">Hi, ${escapeHtml(firstName)}</span>
      <button type="button" class="btn btn-bb-outline btn-sm" id="logoutBtn">
        <i class="bi bi-box-arrow-right me-1"></i>Log Out
      </button>
    `;
    document.getElementById("logoutBtn").addEventListener("click", async () => {
      await apiRequest("/api/auth/logout", { method: "POST" });
      // `prefix` is "pages/" when we're at the root index.html, "" when
      // we're already inside pages/ — so the path back to the homepage is
      // the opposite: "index.html" from root, "../index.html" from pages/.
      window.location.href = prefix ? "index.html" : "../index.html";
    });
  } else {
    const page = document.body.dataset.page;
    const loginBtn = `<a class="btn btn-bb-outline btn-sm" href="${prefix}login.html">Log In</a>`;
    const registerBtn = `<a class="btn btn-bb-primary btn-sm" href="${prefix}register.html">Become a Donor</a>`;
    if (page === "login") {
      area.innerHTML = registerBtn;
    } else if (page === "register") {
      area.innerHTML = loginBtn;
    } else {
      area.innerHTML = loginBtn + registerBtn;
    }
  }
}

// ---------------------------------------------------------------------------
// Admin page guard
// ---------------------------------------------------------------------------

async function guardAdminPage() {
  if (document.body.dataset.page !== "admin") return;
  const { ok, data } = await apiRequest("/api/auth/me");
  const user = ok ? data.user : null;
  if (!user || user.role !== "admin") {
    window.location.href = "login.html?next=admin.html";
  }
}

// ---------------------------------------------------------------------------
// Login form
// ---------------------------------------------------------------------------

function wireLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  const errorEl = document.getElementById("loginError");
  const successEl = document.getElementById("loginSuccess");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(errorEl);
    hideAlert(successEl);

    if (!form.checkValidity()) {
      form.classList.add("was-validated");
      return;
    }
    form.classList.add("was-validated");

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;
    const rememberMe = document.getElementById("rememberMe").checked;

    setFormLoading(form, true);
    try {
      const { ok, status, data } = await apiRequest("/api/auth/login", {
        method: "POST",
        body: { email, password, rememberMe },
      });

      if (ok) {
        showAlert(successEl, "Login successful. Redirecting...", "success");
        const params = new URLSearchParams(window.location.search);
        const next = params.get("next");
        const safeNext = next && /^[a-zA-Z0-9_-]+\.html$/.test(next) ? next : null;
        setTimeout(() => {
          window.location.href = safeNext || "../index.html";
        }, 600);
      } else if (status === 401) {
        showAlert(errorEl, (data && data.error) || "Invalid email or password.", "danger");
      } else {
        showAlert(errorEl, (data && data.error) || "Something went wrong. Please try again.", "danger");
      }
    } catch (_err) {
      showAlert(errorEl, "Could not reach the server. Is the backend running?", "danger");
    } finally {
      setFormLoading(form, false);
    }
  });
}

// ---------------------------------------------------------------------------
// Registration form
// ---------------------------------------------------------------------------

function wireRegisterForm() {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const errorEl = document.getElementById("registerError");
  const successEl = document.getElementById("registerSuccess");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(errorEl);
    hideAlert(successEl);

    const password = document.getElementById("regPassword");
    const confirm = document.getElementById("confirmPassword");
    const passwordsMatch = password.value.length > 0 && password.value === confirm.value;
    confirm.setCustomValidity(passwordsMatch ? "" : "mismatch");

    if (!form.checkValidity()) {
      form.classList.add("was-validated");
      return;
    }
    form.classList.add("was-validated");

    const payload = {
      fullName: document.getElementById("fullName").value.trim(),
      email: document.getElementById("regEmail").value.trim(),
      phone: document.getElementById("regPhone").value.trim(),
      bloodGroup: document.getElementById("bloodGroup").value,
      city: document.getElementById("regCity").value.trim(),
      lastDonationDate: document.getElementById("lastDonation").value,
      password: password.value,
      confirmPassword: confirm.value,
      consent: document.getElementById("consent").checked,
    };

    setFormLoading(form, true);
    try {
      const { ok, status, data } = await apiRequest("/api/auth/register", {
        method: "POST",
        body: payload,
      });

      if (ok) {
        showAlert(
          successEl,
          "Registration successful! You can now log in with your new account.",
          "success"
        );
        form.reset();
        form.classList.remove("was-validated");
        setTimeout(() => {
          window.location.href = "login.html";
        }, 1200);
      } else if (status === 409 || status === 400) {
        showAlert(errorEl, fieldErrorMessages(data && data.fields) || (data && data.error), "danger");
      } else {
        showAlert(errorEl, (data && data.error) || "Something went wrong. Please try again.", "danger");
      }
    } catch (_err) {
      showAlert(errorEl, "Could not reach the server. Is the backend running?", "danger");
    } finally {
      setFormLoading(form, false);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderAuthNav();
  guardAdminPage();
  wireLoginForm();
  wireRegisterForm();
});
