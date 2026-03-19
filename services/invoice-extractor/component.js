/**
 * @file: component.js
 * @description: Web Component для сервиса invoice-extractor.
 *   Добавляет переключатель output-режима (Excel / Odoo / JSON / Оба)
 *   поверх стандартной карточки ServiceCard.
 * @dependencies: /shell/js/card-grid.js
 * @created: 2026-03-01
 */

import { ServiceCard } from '/shell/js/card-grid.js';

const OUTPUT_MODES = [
  { value: 'xlsx',      label: 'Excel', icon: '📊', title: 'Таблица Excel (.xlsx)' },
  { value: 'odoo_xlsx', label: 'Odoo',  icon: '🏢', title: 'Импорт товаров в Odoo (.xlsx)' },
  { value: 'json',      label: 'JSON',  icon: '{ }', title: 'JSON-данные счёта' },
  { value: 'both',      label: 'Оба',   icon: '🔀', title: 'JSON + ссылка на Excel' },
];

class InvoiceExtractorCard extends ServiceCard {
  /** Выбранный output-режим, сохраняется между перерисовками */
  #selectedOutput = 'xlsx';

  /* ------------------------------------------------------------------
     Overrides: инжектируем селектор после каждой отрисовки
     ------------------------------------------------------------------ */

  setManifest(manifest) {
    super.setManifest(manifest);
    // Если элемент ещё не в DOM, connectedCallback добавит кнопки позже
    if (!this.isConnected) return;
    this._injectOutputSelector();
  }

  connectedCallback() {
    // super.connectedCallback() вызывает #render() — shadow DOM пересоздаётся
    super.connectedCallback();
    // Инжектируем кнопки ПОСЛЕ перерисовки родителя
    this._injectOutputSelector();
  }

  /* ------------------------------------------------------------------
     Hook: добавляем output в FormData перед отправкой
     ------------------------------------------------------------------ */

  _buildFormData(formData) {
    formData.set('output', this.#selectedOutput);
  }

  /* ------------------------------------------------------------------
     Inject output selector into Shadow DOM (above dropzone)
     ------------------------------------------------------------------ */

  _injectOutputSelector() {
    const root = this.shadowRoot;
    if (!root) return;

    const dropzone = root.querySelector('.dropzone');
    if (!dropzone) return;

    // Добавляем стили один раз
    if (!root.querySelector('#output-selector-style')) {
      const style = document.createElement('style');
      style.id = 'output-selector-style';
      style.textContent = this.#selectorCss();
      root.appendChild(style);
    }

    // Удаляем старый селектор если есть (при повторном вызове setManifest)
    root.querySelector('.output-selector')?.remove();

    // Создаём переключатель
    const selector = document.createElement('div');
    selector.className = 'output-selector';
    selector.setAttribute('role', 'group');
    selector.setAttribute('aria-label', 'Формат результата');

    selector.innerHTML = OUTPUT_MODES.map(m => `
      <button
        type="button"
        class="output-btn${m.value === this.#selectedOutput ? ' output-btn--active' : ''}"
        data-value="${m.value}"
        title="${m.title}"
        aria-pressed="${m.value === this.#selectedOutput}"
      >
        <span class="output-btn__icon" aria-hidden="true">${m.icon}</span>
        <span class="output-btn__label">${m.label}</span>
      </button>
    `).join('');

    // Вставляем перед dropzone
    dropzone.parentNode.insertBefore(selector, dropzone);

    // Привязываем события — stopPropagation чтобы не триггерить file input
    selector.querySelectorAll('.output-btn').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        this.#selectedOutput = btn.dataset.value;
        selector.querySelectorAll('.output-btn').forEach(b => {
          b.classList.toggle('output-btn--active', b === btn);
          b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
        });
      });
    });
  }

  /* ------------------------------------------------------------------
     CSS для переключателя (инжектируется в Shadow DOM)
     ------------------------------------------------------------------ */

  #selectorCss() {
    return `
      .output-selector {
        display: flex;
        gap: 4px;
      }

      .output-btn {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        padding: 6px 4px;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        background: rgba(255,255,255,0.04);
        color: #8888aa;
        cursor: pointer;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transition: background-color 0.15s, border-color 0.15s, color 0.15s;
        user-select: none;
      }

      .output-btn:hover {
        border-color: rgba(99,102,241,0.45);
        background: rgba(99,102,241,0.08);
        color: #c7d2fe;
      }

      .output-btn--active {
        border-color: rgba(99,102,241,0.7);
        background: rgba(99,102,241,0.18);
        color: #818cf8;
        font-weight: 600;
      }

      .output-btn__icon {
        font-size: 0.95rem;
        line-height: 1;
        pointer-events: none;
      }

      .output-btn__label {
        font-size: 0.62rem;
        line-height: 1;
        pointer-events: none;
      }
    `;
  }
}

/* ------------------------------------------------------------------ */
/*  Регистрация Custom Element                                         */
/* ------------------------------------------------------------------ */

if (!customElements.get('service-card-invoice-extractor')) {
  customElements.define('service-card-invoice-extractor', InvoiceExtractorCard);
}
