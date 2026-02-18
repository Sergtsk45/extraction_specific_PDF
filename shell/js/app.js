/**
 * @file: app.js
 * @description: Точка входа Shell App. Инициализирует ServiceRegistry, Sidebar,
 *   AdvancedModal, HistoryManager. Связывает события поиска, фильтрации,
 *   Quick mode и Advanced mode в единый поток управления.
 * @dependencies: service-registry.js, sidebar.js, history.js, modal.js, card-grid.js
 * @created: 2026-02-18
 */

import './card-grid.js';                      // Регистрирует <service-card>
import { ServiceRegistry } from './service-registry.js';
import { Sidebar }         from './sidebar.js';
import { HistoryManager }  from './history.js';
import { AdvancedModal }   from './modal.js';

/* ==========================================================================
   Initialization
   ========================================================================== */

async function init() {
  const gridEl         = document.getElementById('card-grid');
  const sidebarEl      = document.getElementById('sidebar');
  const searchInput    = document.getElementById('search-input');
  const historyBtn     = document.getElementById('history-btn');
  const historyPanel   = document.getElementById('history-panel');
  const historyCloseBtn = document.getElementById('history-close-btn');
  const historyClearBtn = document.getElementById('history-clear-btn');
  const historyListEl  = document.getElementById('history-list');
  const categoryTitle  = document.getElementById('category-title');
  const servicesCount  = document.getElementById('services-count');

  const registry = new ServiceRegistry();
  const modal    = new AdvancedModal();

  let currentCategory = 'all';
  let searchText      = '';

  /* ------------------------------------------------------------------
     Sidebar callback
     ------------------------------------------------------------------ */
  const CATEGORY_LABELS = {
    all:        'Все сервисы',
    converters: 'Конвертеры',
    validation: 'Проверка / Нормоконтроль',
    generators: 'Генераторы документов',
  };

  const sidebar = new Sidebar(sidebarEl, (categoryId) => {
    currentCategory = categoryId;
    categoryTitle.textContent = CATEGORY_LABELS[categoryId] ?? categoryId;

    registry.filter(currentCategory, searchText);
    updateCount();
  });

  /* ------------------------------------------------------------------
     Load services
     ------------------------------------------------------------------ */
  await registry.init(gridEl);

  /* Сервисы загружены — строим сайдбар и обновляем счётчик */
  sidebar.buildFromManifests(registry.manifests);
  updateCount();

  /* ------------------------------------------------------------------
     Search
     ------------------------------------------------------------------ */
  searchInput?.addEventListener('input', () => {
    searchText = searchInput.value.toLowerCase();
    registry.filter(currentCategory, searchText);
    updateCount();
  });

  /* ------------------------------------------------------------------
     History panel
     ------------------------------------------------------------------ */
  historyBtn?.addEventListener('click', () => {
    HistoryManager.render(historyListEl);
    historyPanel.hidden = false;
  });

  historyCloseBtn?.addEventListener('click', () => {
    historyPanel.hidden = true;
  });

  historyClearBtn?.addEventListener('click', () => {
    HistoryManager.clear();
    HistoryManager.render(historyListEl);
  });

  /* Close history panel on Escape */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !historyPanel.hidden) {
      historyPanel.hidden = true;
    }
  });

  /* ------------------------------------------------------------------
     Advanced mode: open on card event
     ------------------------------------------------------------------ */
  document.addEventListener('card:open-advanced', (e) => {
    modal.open(e.detail.manifest);
  });

  /* ------------------------------------------------------------------
     History: Quick mode events
     ------------------------------------------------------------------ */
  document.addEventListener('card:process-complete', (e) => {
    const { manifest, filename, status, visionFallback } = e.detail;
    HistoryManager.add({
      filename,
      serviceName:   manifest?.name,
      serviceId:     manifest?.id,
      status,
      visionFallback,
    });
  });

  document.addEventListener('card:process-error', (e) => {
    const { manifest, filename } = e.detail;
    HistoryManager.add({
      filename,
      serviceName: manifest?.name,
      serviceId:   manifest?.id,
      status:      'error',
    });
  });

  /* ------------------------------------------------------------------
     History: Advanced mode events
     ------------------------------------------------------------------ */
  document.getElementById('advanced-modal')?.addEventListener('modal:process-complete', (e) => {
    const { manifest, filename, status, visionFallback } = e.detail;
    HistoryManager.add({
      filename,
      serviceName:   manifest?.name,
      serviceId:     manifest?.id,
      status,
      visionFallback,
    });
    /* Если панель истории открыта — обновить */
    if (!historyPanel.hidden) HistoryManager.render(historyListEl);
  });

  document.getElementById('advanced-modal')?.addEventListener('modal:process-error', (e) => {
    const { manifest, filename } = e.detail;
    HistoryManager.add({
      filename,
      serviceName: manifest?.name,
      serviceId:   manifest?.id,
      status:      'error',
    });
    if (!historyPanel.hidden) HistoryManager.render(historyListEl);
  });

  /* ------------------------------------------------------------------
     Helpers
     ------------------------------------------------------------------ */
  function updateCount() {
    const count = registry.visibleCount;
    const suffix = count === 1 ? 'сервис' : (count < 5 ? 'сервиса' : 'сервисов');
    servicesCount.textContent = `${count} ${suffix}`;
  }
}

init().catch(err => {
  console.error('[App] Критическая ошибка инициализации:', err);
});
