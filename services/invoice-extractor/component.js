/**
 * @file: component.js
 * @description: Web Component для сервиса invoice-extractor.
 *   Базовая реализация без кастомизации UI.
 *   Использует стандартный ServiceCard из Shell App.
 * @dependencies: /shell/js/card-grid.js
 * @created: 2026-03-01
 */

import { ServiceCard } from '/shell/js/card-grid.js';

/**
 * Карточка экстрактора счетов-фактур PDF → JSON.
 * 
 * Использует стандартный функционал ServiceCard:
 * - Quick mode (drag-and-drop)
 * - Health check индикатор
 * - Кнопка Advanced mode
 * 
 * При необходимости можно переопределить методы для кастомизации:
 * - showResult(result) — кастомное отображение результата
 * - showProgress() — специфичный прогресс
 * - handleError() — обработка ошибок
 */
class InvoiceExtractorCard extends ServiceCard {
  constructor() {
    super();
  }

  // Placeholder для будущей кастомизации отображения результата
  // showResult(result) {
  //   const invoiceNumber = result.invoice_number || 'N/A';
  //   const itemsCount = result.items?.length || 0;
  //   
  //   // Показываем базовый результат
  //   super.showResult(result);
  //   
  //   // Добавляем кастомную информацию
  //   this.showMessage(`Счёт №${invoiceNumber}, позиций: ${itemsCount}`, 'success');
  // }
}

/* ------------------------------------------------------------------ */
/*  Регистрация Custom Element                                         */
/* ------------------------------------------------------------------ */

if (!customElements.get('service-card-invoice-extractor')) {
  customElements.define('service-card-invoice-extractor', InvoiceExtractorCard);
}
