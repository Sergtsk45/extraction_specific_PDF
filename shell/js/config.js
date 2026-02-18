/**
 * @file: config.js
 * @description: Глобальная конфигурация Shell App (пути к API, интервалы)
 * @dependencies: Используется всеми JS-модулями оболочки
 * @created: 2026-02-18
 */

export const CONFIG = {
  /**
   * Базовый URL для сервисов.
   * В production (через Nginx): '' — относительные пути (/services/{id}/...)
   * В dev без Nginx: 'http://localhost:5001' — прямой доступ
   */
  servicesBase: '',

  /** Путь к JSON-индексу зарегистрированных сервисов */
  servicesIndex: '/shell/services.json',

  /** Интервал health-check опроса (мс) */
  healthCheckInterval: 30_000,

  /** Таймаут health-check запроса (мс) */
  healthCheckTimeout: 5_000,

  /** Таймаут запроса на конвертацию (мс, 0 = без таймаута) */
  convertTimeout: 0,

  /** Максимальный размер файла по умолчанию (байт) — 50 MB */
  defaultMaxFileSize: 50 * 1024 * 1024,

  /** Категории с метаданными */
  categories: {
    converters:  { label: 'Конвертеры',              icon: '🔄' },
    validation:  { label: 'Проверка / Нормоконтроль', icon: '✅' },
    generators:  { label: 'Генераторы документов',    icon: '📄' },
  },
};
