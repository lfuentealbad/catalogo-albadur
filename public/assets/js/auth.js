/* ============================================================
   Albadur — login de clientes por RUT (frontend)
   Conversa con /api/auth/* (Cloudflare Worker + D1).
   ============================================================ */
(function () {
  // El login de clientes está construido pero aún OCULTO (se activa cuando
  // carguemos los clientes reales). Cambiar a true para mostrarlo.
  const LOGIN_ENABLED = false;

  const $ = (s) => document.querySelector(s);

  // Estado del usuario, accesible para app.js (prellenar el pedido)
  window.ALBADUR_USER = null;

  let rutValido = null; // RUT normalizado del paso 1

  async function api(path, body) {
    const opts = { method: body ? "POST" : "GET", headers: {} };
    if (body) { opts.headers["content-type"] = "application/json"; opts.body = JSON.stringify(body); }
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch {}
    return { status: res.status, data };
  }

  /* ---------- UI helpers ---------- */
  function openModal() {
    resetToStepRut();
    $("#auth-backdrop").hidden = false;
    $("#auth-modal").hidden = false;
    document.body.style.overflow = "hidden";
    setTimeout(() => $("#auth-rut").focus(), 50);
  }
  function closeModal() {
    $("#auth-backdrop").hidden = true;
    $("#auth-modal").hidden = true;
    document.body.style.overflow = "";
  }
  function resetToStepRut() {
    $("#step-rut").hidden = false;
    $("#step-pass").hidden = true;
    $("#auth-error").hidden = true;
    $("#pass-error").hidden = true;
    $("#auth-rut").value = "";
    $("#auth-pass").value = "";
  }
  function showErr(el, msg) { el.textContent = msg; el.hidden = false; }

  /* ---------- Sesión / header ---------- */
  function setLoggedIn(user) {
    window.ALBADUR_USER = user;
    $("#account-label").textContent = user.nombre.split(" ")[0] || "Mi cuenta";
    $("#account-btn").classList.add("logged");
    // prellenar identificación del pedido si existe el campo
    const cn = $("#customer-name");
    if (cn && !cn.value) cn.value = user.nombre;
    document.dispatchEvent(new CustomEvent("albadur:login", { detail: user }));
  }
  function setLoggedOut() {
    window.ALBADUR_USER = null;
    $("#account-label").textContent = "Ingresar";
    $("#account-btn").classList.remove("logged");
    document.dispatchEvent(new CustomEvent("albadur:logout"));
  }

  async function checkSession() {
    const { status, data } = await api("/api/auth/me");
    if (status === 200 && data.auth) setLoggedIn({ rut: data.rut, nombre: data.nombre });
    else setLoggedOut();
  }

  /* ---------- Flujo ---------- */
  async function onAccountClick() {
    if (window.ALBADUR_USER) {
      // logueado: ofrecer cerrar sesión
      if (confirm(`Sesión de ${window.ALBADUR_USER.nombre}.\n¿Cerrar sesión?`)) {
        await api("/api/auth/logout", {});
        setLoggedOut();
      }
      return;
    }
    openModal();
  }

  async function onRutContinue() {
    const rut = $("#auth-rut").value.trim();
    $("#auth-error").hidden = true;
    if (!rut) return showErr($("#auth-error"), "Escribe tu RUT.");
    const { data } = await api("/api/auth/check-rut", { rut });
    if (!data.ok) return showErr($("#auth-error"), data.error || "RUT inválido.");
    if (!data.exists)
      return showErr($("#auth-error"), "No encontramos tu RUT como cliente. Escríbenos a sociedadalbadur@gmail.com");

    rutValido = rut;
    // pasar al paso contraseña, en modo login o registro
    $("#step-rut").hidden = true;
    $("#step-pass").hidden = false;
    $("#pass-error").hidden = true;
    $("#auth-pass").value = "";
    if (data.hasAccount) {
      $("#pass-title").textContent = `Hola de nuevo`;
      $("#pass-help").textContent = `${data.nombre}: ingresa tu contraseña.`;
      $("#auth-pass").autocomplete = "current-password";
      $("#email-field").hidden = true;
      $("#pass-submit").textContent = "Iniciar sesión";
      $("#pass-submit").dataset.mode = "login";
    } else {
      $("#pass-title").textContent = `¡Bienvenido, ${data.nombre.split(" ")[0]}!`;
      $("#pass-help").textContent = "Eres cliente de Albadur. Crea una contraseña para tu cuenta.";
      $("#auth-pass").autocomplete = "new-password";
      $("#email-field").hidden = false;
      $("#pass-submit").textContent = "Crear cuenta";
      $("#pass-submit").dataset.mode = "register";
    }
    setTimeout(() => $("#auth-pass").focus(), 50);
  }

  async function onPassSubmit() {
    const mode = $("#pass-submit").dataset.mode;
    const password = $("#auth-pass").value;
    $("#pass-error").hidden = true;
    if (!password) return showErr($("#pass-error"), "Escribe tu contraseña.");

    let resp;
    if (mode === "register") {
      const email = $("#auth-email").value.trim();
      resp = await api("/api/auth/register", { rut: rutValido, password, email });
    } else {
      resp = await api("/api/auth/login", { rut: rutValido, password });
    }
    if (resp.status !== 200 || !resp.data.ok)
      return showErr($("#pass-error"), resp.data.error || "No se pudo continuar.");

    setLoggedIn({ rut: resp.data.rut, nombre: resp.data.nombre });
    closeModal();
  }

  /* ---------- Init ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    if (!LOGIN_ENABLED) { const b = $("#account-btn"); if (b) b.hidden = true; return; }
    $("#account-btn").addEventListener("click", onAccountClick);
    $("#auth-close").addEventListener("click", closeModal);
    $("#auth-backdrop").addEventListener("click", closeModal);
    $("#rut-continue").addEventListener("click", onRutContinue);
    $("#pass-submit").addEventListener("click", onPassSubmit);
    $("#pass-back").addEventListener("click", resetToStepRut);
    $("#auth-rut").addEventListener("keydown", (e) => { if (e.key === "Enter") onRutContinue(); });
    $("#auth-pass").addEventListener("keydown", (e) => { if (e.key === "Enter") onPassSubmit(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
    checkSession();
  });
})();
