/**
 * @file: service-registry.js
 * @description: Реестр сервисов — загружает manifest.json из /services/{id}/,
 *   создаёт ServiceCard Custom Elements, управляет фильтрацией по категории и поиску.
 * @dependencies: card-grid.js, config.js
 * @created: 2026-02-18
 */

import { CONFIG } from './config.js';

export class ServiceRegistry extends EventTarget {
  /** @type {Map<string, HTMLElement>} id → service-card element */
  #cards     = new Map();

  /** @type {object[]} загруженные манифесты */
  #manifests = [];

  /** @type {HTMLElement} контейнер карточек */
  #gridEl    = null;

  /* ------------------------------------------------------------------
     Public API
     ------------------------------------------------------------------ */

  /** Все загруженные манифесты (для построения сайдбара) */
  get manifests() {
    return this.#manifests;
  }

  /**
   * Инициализация: загрузить индекс → манифесты → компоненты → создать карточки.
   * Манифесты и компоненты загружаются параллельно; карточки создаются после
   * завершения обеих загрузок, чтобы Custom Elements были зарегистрированы.
   * @param {HTMLElement} gridEl — контейнер .card-grid
   */
  async init(gridEl) {
    this.#gridEl = gridEl;

    const serviceIds = await this.#loadServiceIndex();

    const [manifestResults] = await Promise.all([
      Promise.allSettled(serviceIds.map(id => this.#loadManifest(id))),
      Promise.allSettled(serviceIds.map(id => this.#loadComponent(id))),
    ]);

    gridEl.innerHTML = '';
    let loaded = 0;

    for (const result of manifestResults) {
      if (result.status === 'fulfilled' && result.value) {
        this.#createCard(result.value);
        loaded++;
      }
    }

    if (loaded === 0) {
      gridEl.innerHTML = '<p class="grid-empty">Нет доступных сервисов</p>';
    }

    this.dispatchEvent(new CustomEvent('registry:loaded', {
      detail: { count: loaded },
    }));
  }

  /**
   * Фильтрация карточек по категории и/или тексту поиска.
   * @param {string} category — 'all' или id категории
   * @param {string} searchText — строка поиска (lowercase)
   */
  filter(category, searchText = '') {
    const query = searchText.trim().toLowerCase();

    this.#cards.forEach((card) => {
      const m = card.manifest;
      if (!m) { card.hidden = true; return; }

      const catOk = !category || category === 'all' || m.category === category;
      const txtOk = !query
        || m.name?.toLowerCase().includes(query)
        || m.description?.toLowerCase().includes(query)
        || m.category?.toLowerCase().includes(query);

      card.hidden = !(catOk && txtOk);
    });

    this.dispatchEvent(new CustomEvent('registry:filtered'));
  }

  /** Количество видимых карточек */
  get visibleCount() {
    return [...this.#cards.values()].filter(c => !c.hidden).length;
  }

  /* ------------------------------------------------------------------
     Private: Loading
     ------------------------------------------------------------------ */

  async #loadServiceIndex() {
    try {
      const resp = await fetch(CONFIG.servicesIndex);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      return Array.isArray(data.services) ? data.services : [];
    } catch (err) {
      console.warn('[ServiceRegistry] Не удалось загрузить services.json:', err.message);
      return [];
    }
  }

  /**
   * Динамически загружает component.js сервиса.
   * Успешная загрузка регистрирует Custom Element `<service-card-{id}>`.
   * Ошибка (404, parse) игнорируется — карточка будет создана на базовом <service-card>.
   * @param {string} id
   */
  async #loadComponent(id) {
    const url = `${CONFIG.servicesBase}/services/${id}/component.js`;
    try {
      // В dev Chrome может сохранять ES-модули между обновлениями страницы (304),
      // поэтому добавляем cache-busting query для localhost, чтобы гарантировать
      // подхват свежего component.js при разработке.
      const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
      const bust = isLocalhost ? `?v=${Date.now()}` : '';
      await import(`${url}${bust}`);
      console.log(`[ServiceRegistry] Компонент "${id}" загружен`);
    } catch {
      console.info(`[ServiceRegistry] component.js для "${id}" не найден, используется базовый`);
    }
  }

  async #loadManifest(id) {
    const url = `${CONFIG.servicesBase}/services/${id}/manifest.json`;
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const manifest = await resp.json();
      if (!manifest.id) manifest.id = id;
      return manifest;
    } catch (err) {
      console.warn(`[ServiceRegistry] Манифест для "${id}" недоступен:`, err.message);
      return null;
    }
  }

  /* ------------------------------------------------------------------
     Private: Card Creation
     ------------------------------------------------------------------ */

  /**
   * Создаёт карточку сервиса.
   * Если зарегистрирован Custom Element `<service-card-{id}>` (из component.js),
   * использует его; иначе создаёт базовый `<service-card>`.
   * @param {object} manifest
   */
  #createCard(manifest) {
    this.#manifests.push(manifest);

    const specificTag = `service-card-${manifest.id}`;
    const tagName = customElements.get(specificTag) ? specificTag : 'service-card';
    const card = document.createElement(tagName);
    card.setManifest(manifest);

    this.#gridEl.appendChild(card);
    this.#cards.set(manifest.id, card);
  }
}
