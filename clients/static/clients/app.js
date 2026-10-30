"use strict";

const $ = (selector) => document.querySelector(selector);
const labels = {
  prospect: "Prospecto",
  customer: "Cliente",
  inactive: "Inactivo",
};
const state = {
  page: 1,
  pages: 1,
  clients: [],
  editing: null,
  deleting: null,
  request: null,
  sequence: 0,
  busy: false,
};
const form = $("#client-form");
const clientDialog = $("#client-dialog");
const deleteDialog = $("#delete-dialog");
const dateFormatter = new Intl.DateTimeFormat("es-EC", {
  day: "numeric",
  month: "short",
  year: "numeric",
});
const pencil =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m16 3 5 5-12 12-6 1 1-6Z"/><path d="m14 5 5 5"/></svg>';
const trash =
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></svg>';

function csrfToken() {
  return (
    document.cookie
      .split("; ")
      .find((cookie) => cookie.startsWith("csrftoken="))
      ?.split("=")[1] || ""
  );
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      ...options.headers,
    },
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "El servidor no pudo procesar la solicitud. Vuelve a intentarlo.",
    );
  }
  if (!response.ok) {
    const error = new Error(
      data.message || "No se pudo completar la solicitud.",
    );
    error.fields = data.errors;
    throw error;
  }
  return data;
}

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}

function toast(message) {
  const notification = element("div", "toast");
  notification.append(element("span", "", "✓"), element("span", "", message));
  $("#toasts").replaceChildren(notification);
  window.setTimeout(() => notification.remove(), 5000);
}

function renderMetrics(metrics) {
  for (const [key, value] of Object.entries(metrics)) {
    $(`#metric-${key}`).textContent = value;
    const track = $(`#track-${key}`);
    if (track)
      track.style.width = `${metrics.total ? (value / metrics.total) * 100 : 0}%`;
  }
  $("#nav-count").textContent = metrics.total;
}

function actionButton(client, action, icon, title) {
  const button = element("button", `icon-button ${action}-button`);
  button.type = "button";
  button.innerHTML = icon; // Fixed local SVG; client data is only inserted with textContent.
  button.title = `${title} a ${client.name}`;
  button.setAttribute("aria-label", button.title);
  button.addEventListener("click", () =>
    action === "edit" ? openClient(client) : openDelete(client),
  );
  return button;
}

function renderClient(client) {
  const row = element("tr");
  const identityCell = element("td");
  const identity = element("div", "client-identity");
  const initials = client.name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  const avatar = element("span", "avatar", initials);
  const palette = [
    ["#e9eddb", "#788658"],
    ["#f2e7de", "#a48267"],
    ["#e7ecee", "#7c939e"],
    ["#efe5ec", "#a28499"],
  ];
  const colors = palette[client.id % palette.length];
  avatar.style.backgroundColor = colors[0];
  avatar.style.color = colors[1];
  avatar.setAttribute("aria-hidden", "true");
  const details = element("div");
  details.append(
    element("span", "client-name", client.name),
    element(
      "span",
      "client-date",
      `Desde el ${dateFormatter.format(new Date(client.created_at))}`,
    ),
  );
  identity.append(avatar, details);
  identityCell.append(identity);
  const company = element(
    "td",
    "company-text",
    client.company || "Sin empresa",
  );
  const contact = element("td", "contact-cell");
  contact.append(
    element("span", "contact-email", client.email),
    element("span", "contact-phone", client.phone || "Sin teléfono"),
  );
  const status = element("td", "status-cell");
  const badge = element("span", `status-badge ${client.status}`);
  badge.append(
    element("span", "status-dot"),
    document.createTextNode(labels[client.status]),
  );
  status.append(badge);
  const actions = element("td", "actions-cell");
  const buttons = element("div", "row-actions");
  buttons.append(
    actionButton(client, "edit", pencil, "Editar"),
    actionButton(client, "delete", trash, "Eliminar"),
  );
  actions.append(buttons);
  row.append(identityCell, company, contact, status, actions);
  return row;
}

async function loadClients() {
  state.request?.abort();
  state.request = new AbortController();
  const sequence = ++state.sequence;
  const params = new URLSearchParams({
    q: $("#search").value.trim(),
    status: $("#status-filter").value,
    page: state.page,
  });
  $("#list-error").hidden = true;
  $("#loading-state").hidden = false;
  $("#empty-state").hidden = true;
  $("#table-region").hidden = true;
  $("#table-region").setAttribute("aria-busy", "true");
  $("#previous-page").disabled = true;
  $("#next-page").disabled = true;
  try {
    const data = await api(`/api/clients/?${params}`, {
      signal: state.request.signal,
    });
    if (sequence !== state.sequence) return;
    state.clients = data.clients;
    state.page = data.pagination.page;
    state.pages = data.pagination.pages;
    renderMetrics(data.metrics);
    $("#directory-count").textContent = data.pagination.total;
    $("#client-rows").replaceChildren(...state.clients.map(renderClient));
    $("#table-region").hidden = !state.clients.length;
    $("#empty-state").hidden = Boolean(state.clients.length);
    const filtered = Boolean(params.get("q") || params.get("status"));
    $("#empty-title").textContent = filtered
      ? "No encontramos esa conexión"
      : "Tu red empieza con una conexión";
    $("#empty-message").textContent = filtered
      ? "Prueba con otro nombre, empresa o estado."
      : "Añade tu primer cliente para comenzar.";
    $("#empty-action").textContent = filtered
      ? "Limpiar filtros"
      : "Añadir cliente";
    const start = data.pagination.total ? (state.page - 1) * 8 + 1 : 0;
    const end = Math.min(state.page * 8, data.pagination.total);
    $("#pagination-label").textContent =
      `Mostrando ${start}–${end} de ${data.pagination.total} clientes`;
    $("#page-number").textContent = `${state.page} / ${state.pages}`;
    $("#previous-page").disabled = state.page <= 1;
    $("#next-page").disabled = state.page >= state.pages;
  } catch (error) {
    if (error.name === "AbortError" || sequence !== state.sequence) return;
    $("#list-error span").textContent = error.message;
    $("#list-error").hidden = false;
    $("#pagination-label").textContent = "No se pudo cargar el directorio.";
  } finally {
    if (sequence === state.sequence) {
      $("#loading-state").hidden = true;
      $("#table-region").setAttribute("aria-busy", "false");
    }
  }
}

function clearErrors() {
  $("#form-error").hidden = true;
  form.querySelectorAll(".field-error").forEach((node) => {
    node.textContent = "";
  });
  form
    .querySelectorAll("[aria-invalid]")
    .forEach((node) => node.removeAttribute("aria-invalid"));
}

function openClient(client = null) {
  state.editing = client;
  form.reset();
  clearErrors();
  $("#dialog-title").textContent = client
    ? "Cuidemos esta conexión"
    : "Nueva conexión";
  $("#save-client").textContent = client
    ? "Guardar cambios"
    : "Guardar cliente";
  if (client) {
    for (const key of ["name", "company", "email", "phone", "status"])
      form.elements[key].value = client[key];
  }
  clientDialog.showModal();
  $("#name").focus();
}

function openDelete(client) {
  state.deleting = client;
  $("#delete-name").textContent = client.name;
  $("#delete-error").hidden = true;
  deleteDialog.showModal();
  $("#delete-dialog [data-close]").focus();
}

function lockDialog(dialog, busy) {
  state.busy = busy;
  dialog.querySelectorAll("button, input, select").forEach((node) => {
    node.disabled = busy;
  });
  dialog.setAttribute("aria-busy", String(busy));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  clearErrors();
  const values = Object.fromEntries(new FormData(form));
  for (const key of Object.keys(values)) values[key] = values[key].trim();
  if (!values.name) {
    $("#error-name").textContent = "Introduce el nombre del cliente.";
    $("#name").setAttribute("aria-invalid", "true");
    $("#name").focus();
    return;
  }
  const editing = state.editing;
  const buttonLabel = $("#save-client").textContent;
  lockDialog(clientDialog, true);
  $("#save-client").textContent = "Guardando…";
  try {
    await api(editing ? `/api/clients/${editing.id}/` : "/api/clients/", {
      method: editing ? "PUT" : "POST",
      body: JSON.stringify(values),
    });
    clientDialog.close();
    toast(
      editing
        ? "Los cambios se guardaron correctamente."
        : "Una nueva conexión en tu directorio.",
    );
    if (!editing) {
      $("#search").value = "";
      $("#status-filter").value = "";
      state.page = 1;
    }
    await loadClients();
  } catch (error) {
    $("#form-error").textContent = error.message;
    $("#form-error").hidden = false;
    let firstInvalid;
    for (const [field, messages] of Object.entries(error.fields || {})) {
      const input = form.elements.namedItem(field);
      const message = document.getElementById(`error-${field}`);
      if (input && message) {
        message.textContent = messages.join(" ");
        input.setAttribute("aria-invalid", "true");
        firstInvalid ||= input;
      }
    }
    lockDialog(clientDialog, false);
    firstInvalid?.focus();
  } finally {
    lockDialog(clientDialog, false);
    $("#save-client").textContent = buttonLabel;
  }
});

$("#confirm-delete").addEventListener("click", async () => {
  if (state.busy || !state.deleting) return;
  lockDialog(deleteDialog, true);
  $("#confirm-delete").textContent = "Eliminando…";
  try {
    await api(`/api/clients/${state.deleting.id}/`, { method: "DELETE" });
    deleteDialog.close();
    toast("Cliente eliminado del directorio.");
    await loadClients();
  } catch (error) {
    $("#delete-error").textContent = error.message;
    $("#delete-error").hidden = false;
  } finally {
    lockDialog(deleteDialog, false);
    $("#confirm-delete").textContent = "Sí, eliminar";
  }
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});
document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("cancel", (event) => {
    if (state.busy) event.preventDefault();
  });
});
$("#new-client").addEventListener("click", () => openClient());
$("#retry").addEventListener("click", loadClients);
let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  // Invalidate any older request immediately, before the debounce elapses.
  state.request?.abort();
  ++state.sequence;
  searchTimer = setTimeout(() => {
    state.page = 1;
    loadClients();
  }, 280);
});
$("#status-filter").addEventListener("change", () => {
  state.page = 1;
  loadClients();
});
$("#previous-page").addEventListener("click", () => {
  --state.page;
  loadClients();
});
$("#next-page").addEventListener("click", () => {
  ++state.page;
  loadClients();
});
$("#empty-action").addEventListener("click", () => {
  if ($("#search").value || $("#status-filter").value) {
    $("#search").value = "";
    $("#status-filter").value = "";
    state.page = 1;
    loadClients();
  } else openClient();
});
document.addEventListener("keydown", (event) => {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
  if (event.key === "/" && !typing && !document.querySelector("dialog[open]")) {
    event.preventDefault();
    $("#search").focus();
  }
});
loadClients();
