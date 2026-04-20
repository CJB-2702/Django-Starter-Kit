/**
 * Bulma-styled search field with a dropdown of <li> results (light DOM / slot).
 * HTMX loads fragments into the host element; use format=htmx-search-results on the collection URL.
 */
class SearchDropdown extends HTMLElement {
  static formAssociated = true;

  constructor() {
    super();
    this.internals = this.attachInternals();
    this.attachShadow({ mode: "open" });
    this._value = "";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: relative;
          width: 100%;
          font-family: BlinkMacSystemFont, -apple-system, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        input {
          width: 100%;
          box-sizing: border-box;
          align-items: center;
          border: 1px solid #dbdbdb;
          border-radius: 4px;
          box-shadow: inset 0 0.0625em 0.125em rgba(10, 10, 10, 0.05);
          display: inline-flex;
          font-size: 1rem;
          height: 2.5em;
          justify-content: flex-start;
          line-height: 1.5;
          padding: calc(0.5em - 1px) calc(0.75em - 1px);
          background-color: #fff;
          color: #363636;
        }
        input:hover { border-color: #b5b5b5; }
        input:focus {
          border-color: #485fc7;
          box-shadow: 0 0 0 0.125em rgba(72, 95, 199, 0.25);
          outline: none;
        }
        input::placeholder { color: rgba(54, 54, 54, 0.3); }
        .dropdown {
          position: absolute;
          left: 0;
          right: 0;
          top: calc(100% + 2px);
          z-index: 20;
          display: none;
          list-style: none;
          margin: 0;
          padding: 0.5rem 0;
          background-color: #fff;
          border-radius: 4px;
          box-shadow: 0 0.5em 1em -0.125em rgba(10, 10, 10, 0.1), 0 0 0 1px rgba(10, 10, 10, 0.02);
          max-height: 16rem;
          overflow-y: auto;
        }
        :host([open]) .dropdown { display: block; }
        ::slotted(li) {
          padding: 0.5rem 0.75rem;
          cursor: pointer;
          font-size: 0.875rem;
          line-height: 1.4;
          color: #363636;
        }
        ::slotted(li):hover,
        ::slotted(li):focus {
          background-color: #f5f5f5;
        }
        ::slotted(li.is-disabled),
        ::slotted(li[aria-disabled="true"]) {
          cursor: default;
          color: #7a7a7a;
        }
        ::slotted(li.is-family-monospace) {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          font-size: 0.8125rem;
        }
      </style>
      <input type="text" autocomplete="off" placeholder="Search…">
      <ul class="dropdown" role="listbox">
        <slot></slot>
      </ul>
    `;
  }

  connectedCallback() {
    this.input = this.shadowRoot.querySelector("input");

    const passThrough = [
      "hx-get",
      "hx-post",
      "hx-trigger",
      "hx-target",
      "hx-swap",
      "hx-indicator",
      "hx-headers",
      "hx-vals",
      "hx-params",
      "hx-include",
      "hx-sync",
    ];
    passThrough.forEach((attr) => {
      if (this.hasAttribute(attr)) {
        this.input.setAttribute(attr, this.getAttribute(attr));
      }
    });

    if (this.hasAttribute("placeholder")) {
      this.input.setAttribute("placeholder", this.getAttribute("placeholder"));
    }

    if (!this.input.hasAttribute("hx-trigger")) {
      this.input.setAttribute("hx-trigger", "keyup changed delay:350ms, search");
    }

    if (!this.input.hasAttribute("hx-target")) {
      if (!this.id) {
        this.id = `search-dropdown-${Math.random().toString(36).slice(2, 11)}`;
      }
      // HTMX resolves bare #id from the trigger's root (shadow root here), so the host id is invisible.
      // "global " forces document-scoped querySelector (htmx hx-target extended syntax).
      this.input.setAttribute("hx-target", `global #${this.id}`);
    }

    if (!this.input.hasAttribute("hx-swap")) {
      this.input.setAttribute("hx-swap", "innerHTML");
    }

    this.input.setAttribute("name", "q");

    if (window.htmx) {
      htmx.process(this.input);
    }

    this.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (!li || !this.contains(li)) {
        return;
      }
      if (!li.hasAttribute("data-value")) {
        return;
      }
      const raw = li.getAttribute("data-value");
      if (raw === null || raw === "") {
        return;
      }
      this.value = raw;
      this.input.value = li.innerText.trim();
      this.removeAttribute("open");
    });

    this.input.addEventListener("focus", () => this.setAttribute("open", ""));
    this.input.addEventListener("blur", () => {
      setTimeout(() => this.removeAttribute("open"), 200);
    });
  }

  get value() {
    return this._value;
  }

  set value(v) {
    this._value = v;
    this.setAttribute("value", v);
    this.internals.setFormValue(v);
  }

  get name() {
    return this.getAttribute("name");
  }
}

if (!customElements.get("search-dropdown")) {
  customElements.define("search-dropdown", SearchDropdown);
}
