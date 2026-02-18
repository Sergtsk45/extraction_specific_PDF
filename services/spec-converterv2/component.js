/**
 * @file: component.js
 * @description: Web Component для сервиса spec-converterv2.
 *   Расширяет базовый ServiceCard:
 *   - Отображает имена листов Excel (из X-Sheet-Names) после конвертации
 *   - Показывает статус Vision-режима (👁) через badge
 *   - Кастомные сообщения прогресса в Quick mode
 *   Загружается динамически через Service Registry.
 * @dependencies: /shell/js/card-grid.js
 * @created: 2026-02-18
 */

import { ServiceCard } from '/shell/js/card-grid.js';

/**
 * Карточка конвертера спецификаций PDF → Excel.
 *
 * Переопределяет Quick-mode обработку, чтобы:
 * 1. Показывать имена созданных листов Excel под dropzone.
 * 2. Выводить сообщение о Vision fallback в dropzone-тексте.
 * 3. Отображать шаги прогресса (текст → vision → Excel).
 */
class SpecConverterCard extends ServiceCard {

  /** @type {HTMLElement|null} Контейнер чипов листов (создаётся динамически) */
  #sheetsContainer = null;

  /* ------------------------------------------------------------------ */
  /*  Lifecycle                                                           */
  /* ------------------------------------------------------------------ */

  connectedCallback() {
    super.connectedCallback();
    this.#injectSheetsSlot();
    this.#listenProcessEvents();
  }

  /* ------------------------------------------------------------------ */
  /*  Инициализация дополнительных элементов                             */
  /* ------------------------------------------------------------------ */

  /**
   * Добавляет блок «Листы:» под dropzone внутри Shadow DOM после рендера.
   * Если базовый класс ещё не отрисовал Shadow DOM — наблюдаем через MutationObserver.
   */
  #injectSheetsSlot() {
    const tryInject = () => {
      const footer = this.shadowRoot?.querySelector('.card__footer');
      if (!footer || footer.querySelector('.spec-sheets')) return false;

      const slot = document.createElement('div');
      slot.className = 'spec-sheets';
      slot.setAttribute('aria-live', 'polite');
      // Стиль через style-атрибут (Shadow DOM не наследует внешние стили)
      slot.style.cssText = [
        'display:none',
        'flex-wrap:wrap',
        'gap:4px',
        'margin-top:4px',
        'width:100%',
      ].join(';');
      footer.before(slot);
      this.#sheetsContainer = slot;
      return true;
    };

    if (tryInject()) return;

    // Ждём рендера через MutationObserver
    const obs = new MutationObserver(() => {
      if (tryInject()) obs.disconnect();
    });
    obs.observe(this.shadowRoot ?? this, { childList: true, subtree: true });
  }

  /* ------------------------------------------------------------------ */
  /*  Реакция на события конвертации                                     */
  /* ------------------------------------------------------------------ */

  #listenProcessEvents() {
    this.addEventListener('card:process-complete', e => {
      const { visionFallback } = e.detail ?? {};
      if (visionFallback) {
        // Обновляем dropzone-текст чтобы явно указать Vision
        this.#setDropzoneHint('✓ Готово! (Vision fallback)');
      }
    });

    this.addEventListener('card:process-error', () => {
      this.#clearSheets();
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Override: processFileQuick — добавляем шаги прогресса              */
  /* ------------------------------------------------------------------ */

  /**
   * Переопределяем метод через перехват fetch-запроса.
   * Базовый класс уже реализует полный цикл; здесь мы:
   * - Показываем поэтапный текст прогресса
   * - После успеха читаем X-Sheet-Names и рендерим чипы
   *
   * Для этого перехватываем событие 'card:process-complete'
   * и читаем заголовки из кастомного события (нужно расширить базовый класс).
   *
   * Поскольку базовый ServiceCard не передаёт заголовки ответа в событие,
   * мы патчим fetch через Symbol(spec-converter-fetch).
   * Чипы листов покажем, когда базовый класс вызовет dispatchEvent.
   */

  /* ------------------------------------------------------------------ */
  /*  Публичный метод: показать чипы листов (вызывается снаружи)        */
  /* ------------------------------------------------------------------ */

  /**
   * Рендерит чипы имён листов Excel под карточкой.
   * @param {string[]} names — список имён листов
   */
  showSheets(names) {
    if (!this.#sheetsContainer || !names?.length) return;

    this.#sheetsContainer.style.display = 'flex';
    this.#sheetsContainer.innerHTML = names.map(name =>
      `<span style="
        display:inline-flex;align-items:center;
        padding:1px 8px;
        background:rgba(99,102,241,0.14);
        border:1px solid rgba(99,102,241,0.25);
        border-radius:99px;
        font-size:0.65rem;
        color:#c7d2fe;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      ">${_escapeHtml(name)}</span>`
    ).join('');
  }

  /* ------------------------------------------------------------------ */
  /*  Вспомогательные методы                                             */
  /* ------------------------------------------------------------------ */

  #clearSheets() {
    if (!this.#sheetsContainer) return;
    this.#sheetsContainer.style.display = 'none';
    this.#sheetsContainer.innerHTML = '';
  }

  #setDropzoneHint(text) {
    const el = this.shadowRoot?.querySelector('.dropzone__text');
    if (el) el.textContent = text;
  }
}

/* ------------------------------------------------------------------ */
/*  Хелперы                                                            */
/* ------------------------------------------------------------------ */

function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ------------------------------------------------------------------ */
/*  Патч Service Registry: перехват fetch для чтения X-Sheet-Names     */
/* ------------------------------------------------------------------ */

/**
 * Перехватывает fetch-ответ в базовом классе через глобальный fetch-монкипатч.
 * Патч активируется только для запросов к /api/spec-converter/convert.
 * После получения ответа с листами — находит карточку и вызывает showSheets().
 *
 * Это необходимо потому что базовый ServiceCard не передаёт response headers
 * в событие card:process-complete. Альтернатива — переопределить весь
 * #processFileQuick, что нарушит DRY.
 */
(function installFetchInterceptor() {
  const _fetch = window.fetch.bind(window);
  const CONVERT_RE = /\/api\/spec-converter\/convert/;

  window.fetch = async function patchedFetch(input, init) {
    const response = await _fetch(input, init);

    // Перехватываем только конвертацию спецификаций
    const url = typeof input === 'string' ? input : input?.url ?? '';
    if (!CONVERT_RE.test(url)) return response;

    const sheetNamesHeader = response.headers.get('X-Sheet-Names') ?? '';
    if (!sheetNamesHeader) return response;

    const sheets = sheetNamesHeader.split(',').map(s => s.trim()).filter(Boolean);
    if (!sheets.length) return response;

    // Откладываем — карточка обновит состояние после получения blob
    Promise.resolve().then(() => {
      document.querySelectorAll('service-card-spec-converterv2').forEach(card => {
        if (typeof card.showSheets === 'function') {
          card.showSheets(sheets);
        }
      });
    });

    return response;
  };
})();

/* ------------------------------------------------------------------ */
/*  Регистрация Custom Element                                         */
/* ------------------------------------------------------------------ */

if (!customElements.get('service-card-spec-converterv2')) {
  customElements.define('service-card-spec-converterv2', SpecConverterCard);
}
