/**
 * @file: history.js
 * @description: Менеджер истории операций. Хранит последние 10 записей
 *   в localStorage. Предоставляет методы добавления, получения, очистки
 *   и рендера истории в панели.
 * @dependencies: —
 * @created: 2026-02-18
 */

const STORAGE_KEY = 'docplatform:history';
const MAX_ENTRIES = 10;

export class HistoryManager {
  /* ------------------------------------------------------------------
     Static Data Methods
     ------------------------------------------------------------------ */

  /**
   * Добавить запись в историю.
   * @param {{ filename, serviceName, serviceId, status, visionFallback? }} entry
   */
  static add(entry) {
    const history = HistoryManager.getAll();
    history.unshift({
      id:           Date.now(),
      timestamp:    new Date().toISOString(),
      filename:     entry.filename     ?? 'Файл',
      serviceName:  entry.serviceName  ?? '',
      serviceId:    entry.serviceId    ?? '',
      status:       entry.status       ?? 'success',
      visionFallback: entry.visionFallback ?? false,
    });

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, MAX_ENTRIES)));
    } catch (err) {
      console.warn('[HistoryManager] Не удалось сохранить историю:', err.message);
    }
  }

  /** @returns {Array} все записи истории */
  static getAll() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
    } catch {
      return [];
    }
  }

  /** Очистить историю */
  static clear() {
    localStorage.removeItem(STORAGE_KEY);
  }

  /* ------------------------------------------------------------------
     Render
     ------------------------------------------------------------------ */

  /**
   * Отрендерить историю в указанный контейнер.
   * @param {HTMLElement} containerEl
   */
  static render(containerEl) {
    const items = HistoryManager.getAll();

    if (items.length === 0) {
      containerEl.innerHTML = '<p class="history-empty">История пуста</p>';
      return;
    }

    containerEl.innerHTML = items.map(item => {
      const icon   = item.status === 'success' ? '✓' : '✗';
      const date   = HistoryManager.#formatDate(item.timestamp);
      const vision = item.visionFallback ? ' · 👁 Vision' : '';

      return `
        <div class="history-item history-item--${item.status}">
          <div class="history-item__icon">${icon}</div>
          <div class="history-item__info">
            <div class="history-item__name" title="${HistoryManager.#esc(item.filename)}">
              ${HistoryManager.#esc(item.filename)}
            </div>
            <div class="history-item__meta">
              ${HistoryManager.#esc(item.serviceName)}${item.serviceName ? ' · ' : ''}${date}${vision}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  /* ------------------------------------------------------------------
     Private Helpers
     ------------------------------------------------------------------ */

  static #formatDate(iso) {
    try {
      return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return iso;
    }
  }

  static #esc(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
}
