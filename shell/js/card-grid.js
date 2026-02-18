/**
 * @file: card-grid.js
 * @description: ServiceCard — Web Component (Custom Element + Shadow DOM).
 *   Реализует карточку сервиса: Quick mode (drag-and-drop → дефолтная обработка),
 *   индикатор статуса (health check), badges (Vision/Error), кнопку Advanced mode.
 * @dependencies: config.js
 * @created: 2026-02-18
 */

import { CONFIG } from './config.js';

/* ============================================================
   ServiceCard Custom Element
   ============================================================ */

export class ServiceCard extends HTMLElement {
  /** @type {object|null} manifest.json данного сервиса */
  #manifest = null;

  /** @type {'checking'|'online'|'offline'} */
  #status = 'checking';

  #visionBadge = false;
  #errorBadge  = false;
  #healthTimer = null;
  #shadow      = null;

  constructor() {
    super();
    this.#shadow = this.attachShadow({ mode: 'open' });
  }

  /* ------------------------------------------------------------------
     Lifecycle
     ------------------------------------------------------------------ */

  connectedCallback() {
    this.#render();
    if (this.#manifest) this.#startHealthCheck();
  }

  disconnectedCallback() {
    this.#stopHealthCheck();
  }

  /* ------------------------------------------------------------------
     Public API
     ------------------------------------------------------------------ */

  /** Передать манифест и перерисовать карточку */
  setManifest(manifest) {
    this.#manifest = manifest;
    this.#render();
    if (this.isConnected) this.#startHealthCheck();
  }

  /** Публичный геттер — используется service-registry для фильтрации */
  get manifest() {
    return this.#manifest;
  }

  setStatus(status) {
    this.#status = status;
    this.#updateStatusDOM();
  }

  setVisionBadge(active) {
    this.#visionBadge = active;
    this.#updateBadgesDOM();
  }

  setErrorBadge(active) {
    this.#errorBadge = active;
    this.#updateCardErrorClass();
  }

  /* ------------------------------------------------------------------
     Rendering
     ------------------------------------------------------------------ */

  #render() {
    if (!this.#manifest) {
      this.#shadow.innerHTML = `<style>:host{display:block;height:100%}</style>
        <div style="height:100%;background:#1c1c2e;border-radius:16px;border:1px solid rgba(255,255,255,0.07)"></div>`;
      return;
    }

    this.#shadow.innerHTML = `<style>${ServiceCard.#css()}</style>${ServiceCard.#html()}`;
    this.#populate();
    this.#bindEvents();
    this.#updateStatusDOM();
    this.#updateBadgesDOM();
  }

  #populate() {
    const m = this.#manifest;
    const root = this.#shadow;

    root.querySelector('.card__icon').textContent        = m.icon || '📋';
    root.querySelector('.card__title').textContent       = m.name || 'Сервис';
    root.querySelector('.card__description').textContent = m.description || '';

    const accepts = Array.isArray(m.accepts) ? m.accepts : [];
    const acceptLabel = accepts
      .map(t => t.split('/').pop().toUpperCase())
      .join(', ');
    root.querySelector('.dropzone__accept').textContent = acceptLabel
      ? `Принимает: ${acceptLabel}`
      : '';

    const input = root.querySelector('.dropzone__input');
    if (accepts.length > 0) input.accept = accepts.join(',');

    if (m.status === 'planned') {
      root.querySelector('.card').classList.add('card--planned');
      root.querySelector('.dropzone').classList.add('dropzone--disabled');
      root.querySelector('.card__open-btn').disabled = true;
      root.querySelector('.dropzone__text').textContent = 'Скоро доступно';
    }
  }

  /* ------------------------------------------------------------------
     Event Binding
     ------------------------------------------------------------------ */

  #bindEvents() {
    const root    = this.#shadow;
    const dropzone = root.querySelector('.dropzone');
    const input    = root.querySelector('.dropzone__input');
    const openBtn  = root.querySelector('.card__open-btn');

    if (!dropzone) return;

    /* ---- Drag-and-drop ---- */
    dropzone.addEventListener('dragenter', e => {
      e.preventDefault();
      if (!this.#isDisabled()) dropzone.classList.add('dropzone--over');
    });
    dropzone.addEventListener('dragover', e => {
      e.preventDefault();
      if (!this.#isDisabled()) dropzone.classList.add('dropzone--over');
    });
    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dropzone--over');
    });
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('dropzone--over');
      if (this.#isDisabled()) return;
      const file = e.dataTransfer?.files?.[0];
      if (file) this.#onFileSelected(file);
    });

    /* ---- File input ---- */
    input?.addEventListener('change', () => {
      const file = input.files?.[0];
      if (file) this.#onFileSelected(file);
      input.value = '';
    });

    /* ---- Open Advanced mode ---- */
    openBtn?.addEventListener('click', e => {
      e.stopPropagation();
      this.dispatchEvent(new CustomEvent('card:open-advanced', {
        bubbles: true,
        composed: true,
        detail: { manifest: this.#manifest },
      }));
    });
  }

  /* ------------------------------------------------------------------
     File Handling (Quick mode)
     ------------------------------------------------------------------ */

  #onFileSelected(file) {
    const validationError = this.#validateFile(file);
    if (validationError) {
      this.#showDropzoneMessage(`⚠️ ${validationError}`, 'error', 4000);
      return;
    }
    this.#processFileQuick(file);
  }

  #validateFile(file) {
    const m = this.#manifest;
    const accepts = Array.isArray(m?.accepts) ? m.accepts : [];

    if (accepts.length > 0 && !accepts.includes(file.type)) {
      const allowed = accepts.map(t => t.split('/').pop()).join(', ');
      return `Неверный тип файла. Ожидается: ${allowed.toUpperCase()}`;
    }

    const maxSize = this.#parseFileSize(m?.maxFileSize) ?? CONFIG.defaultMaxFileSize;
    if (file.size > maxSize) {
      return `Файл слишком большой. Максимум: ${m?.maxFileSize ?? '50MB'}`;
    }

    return null;
  }

  async #processFileQuick(file) {
    const m        = this.#manifest;
    const dropzone = this.#shadow.querySelector('.dropzone');

    this.setErrorBadge(false);
    this.setVisionBadge(false);
    dropzone.classList.add('dropzone--processing');
    this.#setDropzoneText('⏳ Обработка...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const endpoint = this.#buildEndpoint(m.endpoints?.base, m.endpoints?.convert);
      const response = await fetch(endpoint, { method: 'POST', body: formData });

      if (!response.ok) {
        const errMsg = await this.#extractErrorMessage(response);
        throw new Error(errMsg);
      }

      const visionFallback = response.headers.get('X-Vision-Fallback') === 'true';
      const blob     = await response.blob();
      const filename = this.#extractFilename(response, m);

      this.#triggerDownload(blob, filename);
      this.setVisionBadge(visionFallback);

      dropzone.classList.remove('dropzone--processing');
      dropzone.classList.add('dropzone--success');
      this.#setDropzoneText('✓ Готово! Файл скачан');

      this.dispatchEvent(new CustomEvent('card:process-complete', {
        bubbles: true, composed: true,
        detail: { manifest: m, filename: file.name, status: 'success', visionFallback },
      }));

      setTimeout(() => {
        dropzone.classList.remove('dropzone--success');
        this.#resetDropzoneText();
      }, 3500);

    } catch (error) {
      dropzone.classList.remove('dropzone--processing');
      dropzone.classList.add('dropzone--error');
      this.setErrorBadge(true);
      this.#setDropzoneText(`✗ ${error.message}`);

      this.dispatchEvent(new CustomEvent('card:process-error', {
        bubbles: true, composed: true,
        detail: { manifest: m, filename: file.name, error: error.message },
      }));

      setTimeout(() => {
        dropzone.classList.remove('dropzone--error');
        this.setErrorBadge(false);
        this.#resetDropzoneText();
      }, 6000);
    }
  }

  /* ------------------------------------------------------------------
     DOM Updates
     ------------------------------------------------------------------ */

  #updateStatusDOM() {
    const dot  = this.#shadow.querySelector('.status-dot');
    const text = this.#shadow.querySelector('.status-text');
    if (!dot || !text) return;

    dot.className = `status-dot status-dot--${this.#status}`;
    const labels = { checking: 'Проверка...', online: 'Онлайн', offline: 'Офлайн' };
    text.textContent = labels[this.#status] ?? this.#status;
  }

  #updateBadgesDOM() {
    const badges = this.#shadow.querySelector('.card__badges');
    if (!badges) return;
    badges.innerHTML = '';
    if (this.#visionBadge) {
      const b = document.createElement('span');
      b.className = 'badge badge--vision';
      b.title     = 'Использован Vision API (LLM fallback)';
      b.textContent = '👁 Vision';
      badges.appendChild(b);
    }
  }

  #updateCardErrorClass() {
    const card = this.#shadow.querySelector('.card');
    if (!card) return;
    card.classList.toggle('card--error', this.#errorBadge);
  }

  #setDropzoneText(text) {
    const el = this.#shadow.querySelector('.dropzone__text');
    if (el) el.textContent = text;
  }

  #resetDropzoneText() {
    const el = this.#shadow.querySelector('.dropzone__text');
    if (el) el.textContent = 'Перетащите файл';
  }

  #showDropzoneMessage(msg, type = 'error', duration = 3000) {
    const dropzone = this.#shadow.querySelector('.dropzone');
    this.#setDropzoneText(msg);
    dropzone?.classList.add(`dropzone--${type}`);
    setTimeout(() => {
      dropzone?.classList.remove(`dropzone--${type}`);
      this.#resetDropzoneText();
    }, duration);
  }

  /* ------------------------------------------------------------------
     Health Check
     ------------------------------------------------------------------ */

  async #startHealthCheck() {
    if (!this.#manifest?.endpoints?.health) {
      this.setStatus('online');
      return;
    }
    await this.#checkHealth();
    this.#healthTimer = setInterval(
      () => this.#checkHealth(),
      CONFIG.healthCheckInterval
    );
  }

  #stopHealthCheck() {
    if (this.#healthTimer) {
      clearInterval(this.#healthTimer);
      this.#healthTimer = null;
    }
  }

  async #checkHealth() {
    const m = this.#manifest;
    if (!m?.endpoints) return;

    const healthPath = m.endpoints.health?.replace(/^GET\s+/i, '') ?? '/health';
    const url = `${CONFIG.servicesBase}${m.endpoints.base}${healthPath}`;

    try {
      const resp = await fetch(url, {
        method: 'GET',
        signal: AbortSignal.timeout(CONFIG.healthCheckTimeout),
      });
      this.setStatus(resp.ok ? 'online' : 'offline');
    } catch {
      this.setStatus('offline');
    }
  }

  /* ------------------------------------------------------------------
     Helpers
     ------------------------------------------------------------------ */

  #isDisabled() {
    return this.#manifest?.status === 'planned' ||
           !!this.#shadow.querySelector('.dropzone--processing');
  }

  #buildEndpoint(base = '', convert = 'POST /convert') {
    const path = convert.replace(/^POST\s+/i, '');
    return `${CONFIG.servicesBase}${base}${path}`;
  }

  #parseFileSize(str) {
    if (!str) return null;
    const m = String(str).match(/^(\d+(?:\.\d+)?)\s*(KB|MB|GB|B)?$/i);
    if (!m) return null;
    const multipliers = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3 };
    return parseFloat(m[1]) * (multipliers[(m[2] ?? 'B').toUpperCase()] ?? 1);
  }

  async #extractErrorMessage(response) {
    try {
      const json = await response.clone().json();
      return json.error ?? json.message ?? `HTTP ${response.status}`;
    } catch {
      return `HTTP ${response.status}`;
    }
  }

  #extractFilename(response, manifest) {
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (match?.[1]) return match[1].replace(/^['"]|['"]$/g, '');

    const ext = (manifest?.outputMime ?? '').includes('spreadsheet') ? 'xlsx' : 'bin';
    return `result.${ext}`;
  }

  #triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ------------------------------------------------------------------
     Shadow DOM: HTML Template
     ------------------------------------------------------------------ */

  static #html() {
    return `
      <article class="card">
        <header class="card__header">
          <span class="card__icon" aria-hidden="true"></span>
          <div class="card__meta">
            <h3 class="card__title"></h3>
            <div class="card__status">
              <span class="status-dot" aria-hidden="true"></span>
              <span class="status-text" aria-live="polite"></span>
            </div>
          </div>
        </header>

        <p class="card__description"></p>

        <div class="dropzone" role="region" aria-label="Зона загрузки файла">
          <span class="dropzone__icon" aria-hidden="true">📎</span>
          <span class="dropzone__text">Перетащите файл</span>
          <span class="dropzone__accept"></span>
          <input type="file" class="dropzone__input" aria-label="Выбрать файл">
        </div>

        <footer class="card__footer">
          <div class="card__badges" aria-live="polite"></div>
          <button class="card__open-btn" type="button">Открыть ↗</button>
        </footer>
      </article>
    `;
  }

  /* ------------------------------------------------------------------
     Shadow DOM: Styles
     ------------------------------------------------------------------ */

  static #css() {
    return `
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

      :host { display: block; height: 100%; }

      /* ---- Card ---- */
      .card {
        background: #1c1c2e;
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.25rem;
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 0.875rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        position: relative;
      }

      .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        border-color: rgba(99,102,241,0.45);
      }

      .card--planned {
        opacity: 0.55;
      }

      .card--error {
        border-color: rgba(239,68,68,0.5) !important;
        box-shadow: 0 0 0 2px rgba(239,68,68,0.15) !important;
      }

      /* ---- Header ---- */
      .card__header {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
      }

      .card__icon {
        font-size: 2rem;
        line-height: 1;
        flex-shrink: 0;
      }

      .card__meta {
        flex: 1;
        min-width: 0;
      }

      .card__title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #eeeef8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.3;
      }

      .card__status {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-top: 4px;
      }

      /* ---- Status dot ---- */
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
        transition: background-color 0.4s;
      }
      .status-dot--online   { background: #22c55e; box-shadow: 0 0 6px rgba(34,197,94,0.6); }
      .status-dot--offline  { background: #ef4444; }
      .status-dot--checking {
        background: #f59e0b;
        animation: blink 1.4s ease-in-out infinite;
      }
      @keyframes blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.35; }
      }

      .status-text {
        font-size: 0.72rem;
        color: #8888aa;
      }

      /* ---- Description ---- */
      .card__description {
        font-size: 0.82rem;
        color: #8888aa;
        line-height: 1.55;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      /* ---- Dropzone ---- */
      .dropzone {
        border: 2px dashed rgba(255,255,255,0.13);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        flex: 1;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 5px;
        min-height: 90px;
        transition: border-color 0.2s, background-color 0.2s, transform 0.15s;
        position: relative;
        user-select: none;
      }
      .dropzone:hover:not(.dropzone--disabled):not(.dropzone--processing) {
        border-color: rgba(99,102,241,0.55);
        background: rgba(99,102,241,0.05);
      }
      .dropzone--over {
        border-color: #6366f1 !important;
        background: rgba(99,102,241,0.1) !important;
        transform: scale(1.015);
      }
      .dropzone--processing {
        border-color: rgba(245,158,11,0.5) !important;
        background: rgba(245,158,11,0.05) !important;
        cursor: wait;
        pointer-events: none;
      }
      .dropzone--success {
        border-color: rgba(34,197,94,0.6) !important;
        background: rgba(34,197,94,0.06) !important;
      }
      .dropzone--error {
        border-color: rgba(239,68,68,0.6) !important;
        background: rgba(239,68,68,0.06) !important;
      }
      .dropzone--disabled {
        cursor: not-allowed;
        opacity: 0.5;
        pointer-events: none;
      }

      .dropzone__icon  { font-size: 1.4rem; pointer-events: none; }
      .dropzone__text  { font-size: 0.78rem; color: #8888aa; pointer-events: none; }
      .dropzone__accept {
        font-size: 0.68rem;
        color: rgba(136,136,170,0.55);
        pointer-events: none;
      }
      .dropzone__input {
        position: absolute;
        inset: 0;
        opacity: 0;
        cursor: pointer;
        width: 100%;
        height: 100%;
      }

      /* ---- Footer ---- */
      .card__footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        flex-shrink: 0;
      }

      .card__badges {
        display: flex;
        gap: 5px;
        align-items: center;
        flex-wrap: wrap;
      }

      .badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 99px;
        font-size: 0.7rem;
        font-weight: 500;
      }
      .badge--vision {
        background: rgba(99,102,241,0.18);
        color: #818cf8;
        border: 1px solid rgba(99,102,241,0.3);
      }

      /* ---- Open button ---- */
      .card__open-btn {
        background: rgba(99,102,241,0.12);
        color: #818cf8;
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 8px;
        padding: 0.35rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s, color 0.2s, border-color 0.2s;
        white-space: nowrap;
        flex-shrink: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      .card__open-btn:hover:not(:disabled) {
        background: rgba(99,102,241,0.28);
        color: #c7d2fe;
        border-color: rgba(99,102,241,0.5);
      }
      .card__open-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    `;
  }
}

if (!customElements.get('service-card')) {
  customElements.define('service-card', ServiceCard);
}
