/**
 * Shared frontend behaviour used across every page.
 * Relies on mock-data.js being loaded first where sample data is needed.
 */

document.addEventListener("DOMContentLoaded", () => {
  highlightActiveNavLink();
  wirePasswordToggles();
  wireBootstrapValidation();
});

/** Adds the "active" class to the nav link matching the current page. */
function highlightActiveNavLink() {
  const current = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("[data-nav-link]").forEach((link) => {
    const target = link.getAttribute("data-nav-link");
    if (target === current) {
      link.classList.add("active");
      link.setAttribute("aria-current", "page");
    }
  });
}

/** Wires up any .password-toggle buttons to show/hide their sibling password input. */
function wirePasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.getAttribute("data-password-toggle"));
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.innerHTML = showing
        ? '<i class="bi bi-eye" aria-hidden="true"></i>'
        : '<i class="bi bi-eye-slash" aria-hidden="true"></i>';
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });
}

/** Applies Bootstrap's "was-validated" client-side validation pattern to any form with [data-validate]. */
function wireBootstrapValidation() {
  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const extraValid = typeof form.dataset.extraValidator === "string"
        ? window[form.dataset.extraValidator]?.(form) ?? true
        : true;

      if (!form.checkValidity() || !extraValid) {
        event.preventDefault();
        event.stopPropagation();
      } else {
        event.preventDefault();
        const successId = form.getAttribute("data-success-target");
        if (successId) {
          const successEl = document.getElementById(successId);
          if (successEl) {
            successEl.classList.remove("d-none");
            successEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }
      }
      form.classList.add("was-validated");
    });
  });
}

/** Escapes HTML special characters to safely inject fictional sample text into the DOM. */
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

/** Renders a Bootstrap badge span for a given label/variant pair. */
function badgeHtml(label, variant) {
  return `<span class="badge text-bg-${variant}">${escapeHtml(label)}</span>`;
}
