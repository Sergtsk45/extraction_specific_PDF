/**
 * @file: modal.js
 * @description: AdvancedModal — управляет <dialog> Advanced mode.
 *   Drag-and-drop, выбор Vision-провайдера, лог обработки, индикатор прогресса,
 *   кнопка скачивания. Эмитирует события 'modal:process-complete' и 'modal:process-error'.
 * @dependencies: config.js
 * @created: 2026-02-18
 */

import { CONFIG } from './config.js';

export class AdvancedModal {
  /** @type {HTMLDialogElement} */
  #dialog = null;

  /** @type {object|null} manifest текущего сервиса */
  #manifest = null;

  /** @type {Blob|null} результат последней обработки */
  #resultBlob = null;

  /** @type {string|null} */
  #resultFilename = null;

  constructor() {
    this.#dialog = document.getElementById('advanced-modal');
    this.#bindStaticEvents();
  }

  /* ------------------------------------------------------------------
     Public API
     ------------------------------------------------------------------ */

  /**
   * Открыть модальное окно для данного сервиса.
   * @param {object} manifest
   */
  open(manifest) {
    this.#manifest      = manifest;
    this.#resultBlob    = null;
    this.#resultFilename = null;

    this.#populateHeader(manifest);
    this.#resetBody();
    this.#configureOptions(manifest);

    this.#dialog.hidden = false;
    this.#dialog.classList.add('is-open');
    document.getElementById('overlay').hidden = false;
    document.body.style.overflow = 'hidden';
  }

  close() {
    this.#dialog.classList.remove('is-open');
    this.#dialog.hidden = true;
    document.getElementById('overlay').hidden = true;
    document.body.style.overflow = '';
    this.#manifest = null;
  }

  /* ------------------------------------------------------------------
     Static Events (bound once in constructor)
     ------------------------------------------------------------------ */

  #bindStaticEvents() {
    /* ---- Close ---- */
    document.getElementById('modal-close-btn')
      ?.addEventListener('click', () => this.close());

    /* Клик на overlay или на backdrop самого dialog */
    document.getElementById('overlay')
      ?.addEventListener('click', () => this.close());

    /* Клик на сам div-modal вне inner-контента закрывает */
    this.#dialog.addEventListener('click', e => {
      if (e.target === this.#dialog) this.close();
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && this.#dialog.classList.contains('is-open')) {
        e.preventDefault();
        this.close();
      }
    });

    /* ---- Dropzone ---- */
    const dropzone = document.getElementById('modal-dropzone');
    const fileInput = document.getElementById('modal-file-input');

    dropzone?.addEventListener('dragenter', e => {
      e.preventDefault();
      dropzone.classList.add('adv-dropzone--over');
    });
    dropzone?.addEventListener('dragover', e => {
      e.preventDefault();
      dropzone.classList.add('adv-dropzone--over');
    });
    dropzone?.addEventListener('dragleave', () => {
      dropzone.classList.remove('adv-dropzone--over');
    });
    dropzone?.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('adv-dropzone--over');
      const file = e.dataTransfer?.files?.[0];
      if (file) this.#processFile(file);
    });
    dropzone?.addEventListener('click', e => {
      if (e.target !== fileInput && !this.#isProcessing()) {
        fileInput?.click();
      }
    });
    fileInput?.addEventListener('change', () => {
      const file = fileInput.files?.[0];
      if (file) this.#processFile(file);
      fileInput.value = '';
    });

    /* ---- Download ---- */
    document.getElementById('modal-download-btn')
      ?.addEventListener('click', () => this.#downloadResult());

    /* ---- Clear log ---- */
    document.getElementById('modal-log-clear')
      ?.addEventListener('click', () => {
        document.getElementById('modal-log-content').innerHTML = '';
      });
  }

  /* ------------------------------------------------------------------
     Populate / Reset
     ------------------------------------------------------------------ */

  #populateHeader(manifest) {
    document.getElementById('modal-icon').textContent        = manifest.icon    ?? '📋';
    document.getElementById('modal-title').textContent       = manifest.name    ?? '';
    document.getElementById('modal-version').textContent     = `v${manifest.version ?? '?'}`;
    document.getElementById('modal-description').textContent = manifest.description ?? '';

    const fileInput = document.getElementById('modal-file-input');
    const accepts   = Array.isArray(manifest.accepts) ? manifest.accepts : [];
    fileInput.accept = accepts.join(',');
  }

  #configureOptions(manifest) {
    const optEl = document.getElementById('modal-options');
    /* Показываем опции Vision только если сервис это поддерживает */
    optEl.hidden = !manifest.supportsVisionOptions;
  }

  #resetBody() {
    /* Прогресс */
    const progress = document.getElementById('modal-progress');
    progress.hidden = true;
    document.getElementById('modal-progress-bar').style.width = '30%';
    document.getElementById('modal-progress-status').textContent = 'Обработка...';

    /* Лог */
    document.getElementById('modal-log').hidden        = true;
    document.getElementById('modal-log-content').innerHTML = '';

    /* Результат */
    document.getElementById('modal-result').hidden          = true;
    document.getElementById('modal-result-badges').innerHTML = '';

    /* Dropzone */
    const dz = document.getElementById('modal-dropzone');
    dz.classList.remove(
      'adv-dropzone--processing',
      'adv-dropzone--success',
      'adv-dropzone--error',
    );

    /* Сбросить чекбокс и селект */
    const providerSel = document.getElementById('modal-provider-select');
    const visionOnly  = document.getElementById('modal-vision-only');
    if (providerSel) providerSel.value = '';
    if (visionOnly)  visionOnly.checked = false;
  }

  /* ------------------------------------------------------------------
     File Processing
     ------------------------------------------------------------------ */

  async #processFile(file) {
    if (this.#isProcessing()) return;

    const m = this.#manifest;
    if (!m) return;

    /* Validate */
    const validationError = this.#validateFile(file, m);
    if (validationError) {
      this.#log(`⚠️ ${validationError}`, 'error');
      document.getElementById('modal-log').hidden = false;
      return;
    }

    const dropzone = document.getElementById('modal-dropzone');
    const progress = document.getElementById('modal-progress');

    dropzone.classList.add('adv-dropzone--processing');
    progress.hidden = false;

    document.getElementById('modal-log').hidden = false;
    this.#log(`Файл: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
    this.#log('Отправка на сервер...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const provider = document.getElementById('modal-provider-select')?.value;
      if (provider) formData.append('provider', provider);

      const visionOnly = document.getElementById('modal-vision-only')?.checked;
      if (visionOnly) formData.append('vision_only', 'true');

      const endpoint = this.#buildEndpoint(m);
      this.#log(`Эндпоинт: ${endpoint}`);
      document.getElementById('modal-progress-status').textContent = 'Обработка на сервере...';

      const response = await fetch(endpoint, { method: 'POST', body: formData });

      if (!response.ok) {
        const errMsg = await this.#extractErrorMessage(response);
        throw new Error(errMsg);
      }

      const visionFallback = response.headers.get('X-Vision-Fallback') === 'true';
      const blob     = await response.blob();
      const filename = this.#extractFilename(response, m);

      this.#resultBlob     = blob;
      this.#resultFilename = filename;

      /* UI: success */
      dropzone.classList.remove('adv-dropzone--processing');
      dropzone.classList.add('adv-dropzone--success');
      progress.hidden = true;

      if (visionFallback) {
        this.#log('Использован Vision API (LLM fallback)', 'warning');
        this.#addBadge('👁 Vision', 'vision');
      }

      this.#log(`✓ Готово! Файл: ${filename}`, 'success');
      document.getElementById('modal-result').hidden = false;

      /* Автоскачивание */
      this.#downloadResult();

      this.#dialog.dispatchEvent(new CustomEvent('modal:process-complete', {
        bubbles: true,
        detail: { manifest: m, filename: file.name, status: 'success', visionFallback },
      }));

    } catch (error) {
      dropzone.classList.remove('adv-dropzone--processing');
      dropzone.classList.add('adv-dropzone--error');
      progress.hidden = true;

      this.#log(`✗ Ошибка: ${error.message}`, 'error');

      this.#dialog.dispatchEvent(new CustomEvent('modal:process-error', {
        bubbles: true,
        detail: { manifest: m, filename: file.name, error: error.message },
      }));
    }
  }

  #downloadResult() {
    if (!this.#resultBlob || !this.#resultFilename) return;
    const url = URL.createObjectURL(this.#resultBlob);
    const a   = document.createElement('a');
    a.href     = url;
    a.download = this.#resultFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ------------------------------------------------------------------
     Log
     ------------------------------------------------------------------ */

  #log(msg, type = 'info') {
    const content = document.getElementById('modal-log-content');
    if (!content) return;

    const line = document.createElement('div');
    line.className = `log-line log-line--${type}`;
    const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    line.textContent = `[${time}] ${msg}`;
    content.appendChild(line);
    content.scrollTop = content.scrollHeight;
  }

  #addBadge(text, type) {
    const container = document.getElementById('modal-result-badges');
    if (!container) return;
    const badge = document.createElement('span');
    badge.className = `result-badge result-badge--${type}`;
    badge.textContent = text;
    container.appendChild(badge);
  }

  /* ------------------------------------------------------------------
     Helpers
     ------------------------------------------------------------------ */

  #isProcessing() {
    return document.getElementById('modal-dropzone')
      ?.classList.contains('adv-dropzone--processing') ?? false;
  }

  #validateFile(file, manifest) {
    const accepts = Array.isArray(manifest.accepts) ? manifest.accepts : [];
    if (accepts.length > 0 && !accepts.includes(file.type)) {
      const allowed = accepts.map(t => t.split('/').pop().toUpperCase()).join(', ');
      return `Неверный тип файла. Ожидается: ${allowed}`;
    }
    const maxBytes = this.#parseFileSize(manifest.maxFileSize) ?? CONFIG.defaultMaxFileSize;
    if (file.size > maxBytes) {
      return `Файл слишком большой. Максимум: ${manifest.maxFileSize ?? '50MB'}`;
    }
    return null;
  }

  #buildEndpoint(manifest) {
    const base    = manifest.endpoints?.base    ?? '';
    const convert = manifest.endpoints?.convert ?? 'POST /convert';
    const path    = convert.replace(/^POST\s+/i, '');
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
}
