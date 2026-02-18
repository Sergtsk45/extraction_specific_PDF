# Исправление DNS в WSL (ошибка «Failed to resolve openrouter.ai»)

Если при конвертации появляется ошибка **«Ошибка сети: не удалось подключиться к API»** и в тексте есть **Failed to resolve 'openrouter.ai'** или **NameResolutionError**, в WSL не работает разрешение имён.

**Частая причина:** VPN. Если включён VPN, в WSL часто ломается DNS (в том числе для openrouter.ai). Решение: отключить VPN на время конвертации или настроить VPN так, чтобы DNS работал в WSL.

Ниже — другие варианты, если VPN не при чём.

## Способ 1: Один раз прописать DNS (рекомендуется)

В терминале WSL выполните:

```bash
# Сделать resolv.conf неизменяемым и прописать Google DNS
sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf && echo "nameserver 8.8.4.4" >> /etc/resolv.conf && chattr +i /etc/resolv.conf'
```

Проверка:

```bash
ping -c 2 openrouter.ai
```

Если пинг идёт — перезапустите backend и повторите конвертацию.

Чтобы потом разрешить системе снова менять `/etc/resolv.conf`:

```bash
sudo chattr -i /etc/resolv.conf
```

---

## Способ 2: Через wsl.conf (постоянно)

1. Создайте или отредактируйте файл:

```bash
sudo nano /etc/wsl.conf
```

2. Добавьте (или допишите) блок:

```ini
[network]
generateResolvConf = false
```

3. Сохраните (Ctrl+O, Enter, Ctrl+X).

4. Создайте свой resolv.conf:

```bash
sudo rm -f /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
```

5. Перезапустите WSL: в **Windows** в PowerShell выполните `wsl --shutdown`, затем снова откройте терминал WSL.

---

## Способ 3: Только для текущей сессии

```bash
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

После перезагрузки WSL или Windows настройка может сброситься — тогда используйте способ 1 или 2.
