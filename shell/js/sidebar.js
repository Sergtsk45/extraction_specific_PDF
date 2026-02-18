/**
 * @file: sidebar.js
 * @description: Сайдбар с категориями сервисов. Рендерит список категорий,
 *   управляет активным состоянием, генерирует события фильтрации.
 * @dependencies: config.js
 * @created: 2026-02-18
 */

import { CONFIG } from './config.js';

export class Sidebar {
  /** @type {HTMLElement} */
  #el = null;

  /** @type {string} активная категория */
  #activeCategory = 'all';

  /** @type {Function} callback при смене категории */
  #onCategoryChange = null;

  /** @type {Array<{id, label, icon, count}>} список категорий для рендера */
  #categories = [];

  /**
   * @param {HTMLElement} el — DOM-элемент сайдбара
   * @param {Function} onCategoryChange — (categoryId: string) => void
   */
  constructor(el, onCategoryChange) {
    this.#el = el;
    this.#onCategoryChange = onCategoryChange;
  }

  /* ------------------------------------------------------------------
     Public API
     ------------------------------------------------------------------ */

  /**
   * Построить список категорий из набора манифестов.
   * @param {object[]} manifests — массив manifest.json объектов
   */
  buildFromManifests(manifests) {
    const countMap = {};

    for (const m of manifests) {
      if (!m.category) continue;
      countMap[m.category] = (countMap[m.category] ?? 0) + 1;
    }

    const total = manifests.length;
    const catDefs = CONFIG.categories;

    const cats = Object.entries(countMap).map(([id, count]) => ({
      id,
      label: catDefs[id]?.label ?? id,
      icon:  catDefs[id]?.icon  ?? '📌',
      count,
    }));

    this.#categories = cats;
    this.render(total);
  }

  /**
   * Рендер сайдбара.
   * @param {number} totalCount — общее количество сервисов (для «Все»)
   */
  render(totalCount) {
    const isAll = this.#activeCategory === 'all';

    const allItem = this.#buildItem({
      id: 'all', label: 'Все сервисы', icon: '🗂️', count: totalCount,
    }, isAll);

    const catItems = this.#categories
      .map(cat => this.#buildItem(cat, this.#activeCategory === cat.id))
      .join('');

    this.#el.innerHTML = `
      <p class="sidebar__title">Категории</p>
      <ul class="sidebar__list" role="list">
        ${allItem}
        ${catItems}
      </ul>
    `;

    this.#el.querySelectorAll('.sidebar__btn').forEach(btn => {
      btn.addEventListener('click', () => this.#selectCategory(btn.dataset.category));
    });
  }

  /* ------------------------------------------------------------------
     Private
     ------------------------------------------------------------------ */

  #selectCategory(id) {
    this.#activeCategory = id;
    const total = this.#categories.reduce((s, c) => s + c.count, 0);
    this.render(total);
    this.#onCategoryChange?.(id);
  }

  #buildItem({ id, label, icon, count }, isActive) {
    return `
      <li class="sidebar__item${isActive ? ' sidebar__item--active' : ''}">
        <button class="sidebar__btn" data-category="${this.#esc(id)}" type="button">
          <span class="sidebar__btn-icon" aria-hidden="true">${icon}</span>
          <span class="sidebar__btn-label">${this.#esc(label)}</span>
          <span class="sidebar__count">${count}</span>
        </button>
      </li>
    `;
  }

  #esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
}
