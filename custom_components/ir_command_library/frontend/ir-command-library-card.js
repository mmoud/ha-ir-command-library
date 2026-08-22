const IR_DOMAIN = "ir_command_library";

class IRCommandLibraryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._items = [];
    this._stamp = "";
    this._query = "";
  }

  static getStubConfig() { return {}; }
  setConfig(config) { this._config = { ...config }; this._render(); }
  getCardSize() { return Math.max(3, this._groups().length * 3); }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6, min_rows: 3 }; }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const items = Object.values(hass.states)
      .filter((state) => state.entity_id.startsWith("button.") && state.attributes.ir_command)
      .sort((a, b) => a.entity_id.localeCompare(b.entity_id));
    const stamp = items.map((state) => `${state.entity_id}:${state.state}:${state.last_updated}`).join("|");
    if (stamp === this._stamp) return;
    this._stamp = stamp;
    this._items = items;
    this._render();
  }

  _groups() {
    const groups = new Map();
    for (const state of this._items) {
      const a = state.attributes;
      if (!a.ir_controller || !a.ir_area || !a.ir_device || !a.ir_command) continue;
      const haystack = `${a.ir_area} ${a.ir_device_name || a.ir_device} ${a.ir_command_name || a.ir_command}`.toLowerCase();
      if (this._query && !haystack.includes(this._query.toLowerCase())) continue;
      const key = `${a.ir_controller}|${a.ir_area}|${a.ir_device}`;
      if (!groups.has(key)) {
        groups.set(key, {
          controller: a.ir_controller,
          area: a.ir_area,
          device: a.ir_device,
          deviceName: a.ir_device_name || this._pretty(a.ir_device),
          commands: [],
        });
      }
      groups.get(key).commands.push({
        entityId: state.entity_id,
        command: a.ir_command,
        name: a.ir_command_name || this._pretty(a.ir_command),
        icon: a.icon || "mdi:remote",
        available: state.state !== "unavailable",
      });
    }
    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
    for (const group of groups.values()) {
      group.commands.sort((a, b) => collator.compare(a.command, b.command));
    }
    return [...groups.values()].sort((a, b) => collator.compare(`${a.area} ${a.device}`, `${b.area} ${b.device}`));
  }

  async _press(group, command, button) {
    if (!command.available) return this._status(`${command.name} is unavailable`, true);
    button.classList.add("sending");
    this._status(`Sending ${group.deviceName} · ${command.name}…`);
    try {
      await this._hass.callService("button", "press", { entity_id: command.entityId });
      button.classList.remove("sending");
      button.classList.add("sent");
      this._status(`${command.name} sent`);
      setTimeout(() => button.classList.remove("sent"), 700);
    } catch (error) {
      button.classList.remove("sending");
      button.classList.add("failed");
      this._status(error?.message || "Command failed", true);
      setTimeout(() => button.classList.remove("failed"), 1200);
    }
  }

  _status(message, failed = false) {
    const node = this.shadowRoot?.querySelector(".status");
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("error", failed);
    clearTimeout(this._statusTimer);
    this._statusTimer = setTimeout(() => {
      node.textContent = "Ready";
      node.classList.remove("error");
    }, 2500);
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    const groups = this._groups();
    const content = groups.length ? `<div class="remotes">${groups.map((group, groupIndex) => `
      <section class="remote">
        <div class="remote-head">
          <div class="device-icon">${this._escape(group.deviceName.slice(0, 1).toUpperCase())}</div>
          <div class="identity"><h2>${this._escape(group.deviceName)}</h2><p>${this._escape(group.area)} · ${this._escape(this._pretty(group.controller.replace(/^remote\./, "")))}</p></div>
          <span class="count">${group.commands.length}</span>
        </div>
        <div class="commands">${group.commands.map((command, commandIndex) => `
          <button class="command ${command.available ? "" : "unavailable"}" data-group="${groupIndex}" data-command="${commandIndex}" title="${this._escape(command.name)}">
            <span class="orb"><ha-icon icon="${this._escape(command.icon)}"></ha-icon></span>
            <span class="command-name">${this._escape(command.name)}</span>
          </button>`).join("")}</div>
      </section>`).join("")}</div>` : `
      <div class="empty"><ha-icon icon="mdi:remote-off"></ha-icon><strong>No commands yet</strong><span>Open Learn &amp; Manage to teach or register a command.</span></div>`;

    this.shadowRoot.innerHTML = `<style>${sharedStyles()}
      .top{display:flex;align-items:center;gap:9px;padding:12px 16px 2px}.top .search{flex:1}.status{font-size:11px;color:#62e7ad}.status.error{color:#ff8299}
      .remotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;padding:12px 16px 16px}.remote{padding:18px;border-radius:23px;border:1px solid var(--ir-border);background:linear-gradient(150deg,rgba(255,255,255,.065),rgba(255,255,255,.018));box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 18px 36px rgba(0,0,0,.22)}
      .remote-head{display:flex;align-items:center;gap:12px;margin-bottom:18px}.device-icon{width:40px;height:40px;display:grid;place-items:center;border-radius:13px;color:var(--ir-accent);font-weight:800;background:rgba(75,212,255,.10);border:1px solid rgba(75,212,255,.25)}.identity{min-width:0}.identity h2{font-size:15px;margin:0}.identity p{margin:3px 0 0;font-size:10px;color:var(--ir-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.count{margin-left:auto;min-width:25px;height:25px;padding:0 5px;border-radius:13px;display:grid;place-items:center;font-size:10px;color:var(--ir-accent);background:rgba(75,212,255,.10)}
      .commands{display:grid;grid-template-columns:repeat(auto-fit,minmax(74px,1fr));gap:13px 8px}.command{appearance:none;border:0;background:transparent;color:inherit;padding:0;min-width:0;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:7px}.orb{width:49px;height:49px;border-radius:50%;display:grid;place-items:center;color:var(--ir-accent);border:1px solid rgba(117,231,255,.33);background:radial-gradient(circle at 32% 24%,rgba(117,231,255,.28),rgba(17,25,40,.94) 67%);box-shadow:0 10px 24px rgba(0,0,0,.35),0 0 18px rgba(117,231,255,.10);transition:.16s}.command:hover .orb{transform:translateY(-3px) scale(1.05);border-color:rgba(117,231,255,.65);box-shadow:0 14px 28px rgba(0,0,0,.42),0 0 24px rgba(117,231,255,.22)}.command:active .orb,.command.sending .orb{transform:scale(.91)}.command.sent .orb{color:#62f2ae;border-color:#62f2ae}.command.failed .orb{color:#ff758f;border-color:#ff758f}.command.unavailable{opacity:.38;cursor:not-allowed}.orb ha-icon{--mdc-icon-size:22px}.command-name{width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;color:rgba(255,255,255,.68)}
      @media(max-width:600px){.remotes{padding:10px;gap:11px}.remote{padding:15px}.commands{grid-template-columns:repeat(4,minmax(0,1fr))}.status{display:none}}
    </style><ha-card><div class="top"><input class="search" type="search" placeholder="Search commands" value="${this._escape(this._query)}"><span class="status">Ready</span></div>${content}</ha-card>`;

    this.shadowRoot.querySelector(".search")?.addEventListener("input", (event) => {
      this._query = event.target.value;
      this._render();
      const input = this.shadowRoot.querySelector(".search");
      input?.focus();
      input?.setSelectionRange(this._query.length, this._query.length);
    });
    this.shadowRoot.querySelectorAll(".command").forEach((button) => button.addEventListener("click", () => {
      const group = groups[Number(button.dataset.group)];
      this._press(group, group.commands[Number(button.dataset.command)], button);
    }));
  }

  _pretty(value) { return String(value || "").replace(/[_.-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()); }
  _escape(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
}

class IRCommandManagerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._busy = false;
    this._message = "Ready";
    this._error = false;
    this._stamp = "";
  }

  static getStubConfig() { return {}; }
  setConfig(config) { this._config = { ...config }; this._render(); }
  getCardSize() { return 6; }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6, min_rows: 5 }; }
  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const stamp = Object.values(hass.states)
      .filter((state) => state.entity_id.startsWith("remote.") || (state.entity_id.startsWith("button.") && state.attributes.ir_command))
      .map((state) => `${state.entity_id}:${state.attributes.friendly_name || ""}:${state.attributes.ir_area || ""}:${state.attributes.ir_device_name || ""}:${state.attributes.ir_command_name || ""}`)
      .sort()
      .join("|");
    if (stamp === this._stamp) return;
    this._stamp = stamp;
    this._render();
  }

  _remotes() {
    // Home Assistant uses this feature bit to indicate that a remote can learn
    // commands. A remote-domain entity can also represent a media device or a
    // virtual remote, neither of which belongs in this IR/RF controller picker.
    const LEARN_COMMAND = 1;
    return Object.values(this._hass?.states || {})
      .filter((state) => state.entity_id.startsWith("remote.") && (Number(state.attributes.supported_features || 0) & LEARN_COMMAND))
      .sort((a, b) => this._name(a).localeCompare(this._name(b)));
  }

  _buttons() {
    return Object.values(this._hass?.states || {}).filter((state) => state.entity_id.startsWith("button.") && state.attributes.ir_command).sort((a, b) => this._label(a).localeCompare(this._label(b)));
  }

  _name(state) { return state.attributes.friendly_name || state.entity_id; }
  _label(state) { const a = state.attributes; return `${a.ir_area} · ${a.ir_device_name} · ${a.ir_command_name}`; }

  _values() {
    const root = this.shadowRoot;
    return {
      controller: root.querySelector("#controller")?.value || "",
      area: root.querySelector("#area")?.value.trim() || "",
      device: root.querySelector("#device")?.value.trim() || "",
      command: root.querySelector("#command")?.value.trim() || "",
      command_type: root.querySelector("#type")?.value || "ir",
      alternative: Boolean(root.querySelector("#alternative")?.checked),
      timeout: Number(root.querySelector("#timeout")?.value || 30),
    };
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    const draft = this.shadowRoot.querySelector("#controller") ? this._values() : null;
    const remotes = this._remotes();
    const buttons = this._buttons();
    this.shadowRoot.innerHTML = `<style>${sharedStyles()}
      .wrap{padding:16px}.statusline{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.statusline strong{font-size:15px}.status{font-size:11px;color:${this._error ? "#ff8299" : "#62e7ad"}}
      .panels{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.panel{padding:17px;border-radius:22px;border:1px solid var(--ir-border);background:linear-gradient(150deg,rgba(255,255,255,.06),rgba(255,255,255,.018))}.panel-head{display:flex;align-items:center;gap:10px;margin-bottom:14px}.panel-head .icon{width:39px;height:39px;border-radius:13px;display:grid;place-items:center;color:var(--ir-accent);background:rgba(75,212,255,.10);border:1px solid rgba(75,212,255,.24)}.panel-head h2{font-size:14px;margin:0}.panel-head p{font-size:10px;margin:2px 0 0;color:var(--ir-muted)}
      .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.wide{grid-column:1/-1}label{display:grid;gap:5px;font-size:10px;color:var(--ir-muted)}select,input{width:100%;box-sizing:border-box}.check{display:flex;align-items:center;gap:8px;min-height:38px}.check input{width:auto}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:13px}.action{border:1px solid rgba(117,231,255,.28);border-radius:14px;padding:9px 13px;color:var(--ir-accent);background:rgba(117,231,255,.09);cursor:pointer;font:inherit;font-size:11px}.action.primary{color:#061018;background:linear-gradient(135deg,#78eaff,#7290ff);border:0;font-weight:700}.action.danger{color:#ff91a5;border-color:rgba(255,117,143,.28);background:rgba(255,117,143,.08)}.action:disabled{opacity:.4;cursor:not-allowed}
      @media(max-width:600px){.wrap{padding:10px}.panel{padding:15px}.grid{grid-template-columns:1fr}}
    </style><ha-card><div class="wrap">
      <div class="statusline"><strong>Learn &amp; Manage</strong><span class="status">${this._escape(this._message)}</span></div>
      <div class="panels">
        <section class="panel"><div class="panel-head"><span class="icon"><ha-icon icon="mdi:remote-plus"></ha-icon></span><div><h2>Learn or register</h2><p>Create a reusable button without exposing learned payloads</p></div></div>
          <div class="grid">
            <label class="wide">Controller<select id="controller">${remotes.map((state) => `<option value="${this._escape(state.entity_id)}">${this._escape(this._name(state))}</option>`).join("")}</select></label>
            <label>Area<input id="area" placeholder="Living Room"></label><label>Device<input id="device" placeholder="television"></label>
            <label class="wide">Command<input id="command" placeholder="power"></label>
            <label>Type<select id="type"><option value="ir">IR</option><option value="rf">RF</option></select></label><label>Timeout<input id="timeout" type="number" min="5" max="120" value="30"></label>
            <label class="check wide"><input id="alternative" type="checkbox"> Learn alternative toggle-bit code</label>
          </div>
          <div class="actions"><button id="learn" class="action primary" ${this._busy || !remotes.length ? "disabled" : ""}>Learn command</button><button id="register" class="action" ${this._busy || !remotes.length ? "disabled" : ""}>Register existing</button></div>
        </section>
        <section class="panel"><div class="panel-head"><span class="icon"><ha-icon icon="mdi:remote-tv"></ha-icon></span><div><h2>Test or remove</h2><p>Select one generated command button</p></div></div>
          <label>Command<select id="button">${buttons.map((state) => `<option value="${this._escape(state.entity_id)}">${this._escape(this._label(state))}</option>`).join("")}</select></label>
          <div class="actions"><button id="test" class="action primary" ${this._busy || !buttons.length ? "disabled" : ""}>Test</button><button id="remove" class="action danger" ${this._busy || !buttons.length ? "disabled" : ""}>Remove</button></div>
        </section>
      </div>
    </div></ha-card>`;

    if (draft) {
      for (const [id, value] of Object.entries({
        controller: draft.controller,
        area: draft.area,
        device: draft.device,
        command: draft.command,
        type: draft.command_type,
        timeout: draft.timeout,
      })) {
        const field = this.shadowRoot.querySelector(`#${id}`);
        if (field && value !== "") field.value = value;
      }
      const alternative = this.shadowRoot.querySelector("#alternative");
      if (alternative) alternative.checked = draft.alternative;
    }

    this.shadowRoot.querySelector("#learn")?.addEventListener("click", () => {
      const data = this._values();
      if (!data.controller || !data.area || !data.device || !data.command) return this._setError("Complete all command fields");
      this._call("learn_command", data, "Waiting for remote input…", `${data.command} learned`);
    });
    this.shadowRoot.querySelector("#register")?.addEventListener("click", () => {
      const data = this._values();
      if (!data.controller || !data.area || !data.device || !data.command) return this._setError("Complete all command fields");
      this._call("register_command", { controller: data.controller, area: data.area, device: data.device, command: data.command }, "Registering…", `${data.command} registered`);
    });
    this.shadowRoot.querySelector("#test")?.addEventListener("click", () => {
      const entity_id = this.shadowRoot.querySelector("#button")?.value;
      if (entity_id) this._callButton(entity_id);
    });
    this.shadowRoot.querySelector("#remove")?.addEventListener("click", () => {
      const command_button = this.shadowRoot.querySelector("#button")?.value;
      if (command_button && confirm("Delete this learned command from the remote and library?")) this._call("remove_command", { command_button }, "Removing…", "Command removed");
    });
  }

  async _callButton(entity_id) {
    await this._call("__button_press__", { entity_id }, "Sending test…", "Test command sent");
  }

  async _call(service, data, pending, success) {
    if (this._busy) return;
    this._busy = true; this._message = pending; this._error = false; this._render();
    try {
      if (service === "__button_press__") await this._hass.callService("button", "press", data);
      else await this._hass.callService(IR_DOMAIN, service, data);
      this._message = success;
    } catch (error) { this._message = error?.message || "Action failed"; this._error = true; }
    finally { this._busy = false; this._render(); }
  }

  _setError(message) { this._message = message; this._error = true; this._render(); }
  _escape(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
}

function sharedStyles() {
  return `:host{display:block;color:var(--primary-text-color);--ir-accent:#75e7ff;--ir-muted:rgba(255,255,255,.52);--ir-border:rgba(255,255,255,.10)}ha-card{overflow:hidden;border-radius:28px;border:1px solid var(--ir-border);background:linear-gradient(145deg,rgba(20,27,40,.95),rgba(7,11,20,.98));box-shadow:0 24px 60px rgba(0,0,0,.34)}input,select{border:1px solid rgba(255,255,255,.11);border-radius:14px;padding:9px 11px;outline:0;color:var(--primary-text-color);background:rgba(255,255,255,.05);font:inherit;font-size:11px}input:focus,select:focus{border-color:rgba(117,231,255,.48);box-shadow:0 0 0 2px rgba(117,231,255,.08)}.empty{min-height:190px;display:grid;place-content:center;justify-items:center;gap:9px;text-align:center;color:var(--ir-muted);padding:28px}.empty ha-icon{--mdc-icon-size:34px;color:var(--ir-accent)}.empty strong{color:var(--primary-text-color)}.empty span{font-size:11px}`;
}

if (!customElements.get("ir-command-library-card")) customElements.define("ir-command-library-card", IRCommandLibraryCard);
if (!customElements.get("ir-command-manager-card")) customElements.define("ir-command-manager-card", IRCommandManagerCard);
window.customCards = window.customCards || [];
for (const card of [
  { type: "ir-command-library-card", name: "IR Command Library", description: "Automatic learned-command remotes." },
  { type: "ir-command-manager-card", name: "IR Command Manager", description: "Learn, register, test, and remove remote commands." },
]) {
  if (!window.customCards.some((item) => item.type === card.type)) window.customCards.push({ ...card, preview: true });
}
