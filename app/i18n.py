"""Простая локализация: ключ — русская строка, перевод — английская."""
_lang = "ru"

EN = {
    # навигация
    "Главная": "Home", "Автоподбор": "Auto-tune", "Диагностика": "Diagnostics", "Профили": "Profiles",
    "DNS": "DNS", "Файлы": "Files", "Настройки": "Settings",
    # главная
    "Активен": "Active", "Остановлен": "Stopped", "Запускается…": "Starting…",
    "Пресет не запущен": "No preset running", "Выберите пресет в списке и нажмите «Активировать»":
        "Select a preset in the list and press “Activate”",
    "Активировать": "Activate", "Остановить winws": "Stop winws", "Поиск пресетов…": "Search presets…",
    "Все движки": "All engines", "Только избранные": "Favorites only", "Все": "All",
    "Встроенные": "Built-in", "Мои": "Mine", "В избранное": "Add to favorites",
    "Убрать из избранного": "Remove from favorites", "Копировать и изменить": "Duplicate & edit",
    "Открыть файл": "Open file", "Изменить": "Edit", "Описание отсутствует": "No description",
    "Результаты тестов у вашего провайдера": "Test results for your ISP",
    "Пресет ещё не тестировался. Запустите автоподбор.": "Not tested yet. Run auto-tune.",
    "Лучший для провайдера": "Best for ISP", "Встроенный": "Built-in", "Пользовательский": "Custom",
    "Работает": "Uptime", "пресетов": "presets", "Обновить": "Refresh",
    "Обнаружен запущенный winws (запущен не из программы)": "Detected winws started outside the app",
    "Не удалось запустить": "Failed to start", "Запущен": "Started", "Остановлено": "Stopped",
    "Игровой фильтр": "Game filter",
    # автоподбор
    "Провайдер": "ISP", "Определить": "Detect", "Определение…": "Detecting…", "Неизвестно": "Unknown",
    "Что должно работать": "What must work", "Набор пресетов": "Preset set",
    "Все пресеты": "All presets", "Только Zapret 2": "Zapret 2 only", "Только Zapret 1": "Zapret 1 only",
    "Избранные": "Favorites", "Без игрового фильтра": "Without game filter",
    "Таймаут проверки, с": "Check timeout, s", "Прогрев после запуска, с": "Warm-up after start, s",
    "Остановиться на первом, где работает всё": "Stop at the first preset where everything works",
    "Начать подбор": "Start", "Остановить": "Stop", "Пресет": "Preset", "Движок": "Engine",
    "Итог": "Score", "Активировать выбранный": "Activate selected", "Применить лучший": "Apply best",
    "Очистить результаты": "Clear results", "Подбор завершён": "Auto-tune finished",
    "Проверяется": "Testing", "Готов к подбору": "Ready", "Подбор остановлен": "Auto-tune stopped",
    "Лучший пресет": "Best preset", "Сохранено для провайдера": "Saved for ISP",
    "Подбор займёт примерно": "Auto-tune will take about", "мин": "min",
    "Во время подбора текущий пресет будет остановлен.": "The current preset will be stopped during auto-tune.",
    "Результаты сохраняются для каждого провайдера отдельно.": "Results are saved per ISP.",
    "ошибка запуска": "start error",
    # категории
    "YouTube": "YouTube", "Discord": "Discord", "Telegram": "Telegram", "Игры": "Games",
    "ИИ-сервисы": "AI services", "Свои": "Custom",
    # диагностика
    "Проверить сейчас": "Check now", "Проверка…": "Checking…", "Сервис": "Service", "Статус": "Status",
    "Время": "Time", "Подробности": "Details", "Доступен": "Available", "Недоступен": "Blocked",
    "Добавить сайт": "Add site", "домен, например example.com": "domain, e.g. example.com",
    "Удалить выбранный": "Remove selected", "Проверка DNS-подмены": "DNS spoofing check",
    "Системный DNS": "System DNS", "Через DoH (Google)": "Via DoH (Google)", "Подозрительно": "Suspicious",
    "Норма": "OK", "Проверяется текущее состояние сети с активным пресетом.":
        "Checks the network right now with the active preset.",
    "Матрица совместимости": "Compatibility matrix",
    "Какие сервисы работают на каждом проверенном пресете у текущего провайдера.":
        "Which services work on each tested preset for the current ISP.",
    "необязательно": "optional",
    # профили
    "Мои профили": "My profiles", "Новый профиль": "New profile", "Название": "Name", "Описание": "Description",
    "Основа": "Base", "Пустой": "Empty", "Копия выбранного на главной": "Copy of the preset selected on Home",
    "Сохранить": "Save", "Сохранить и активировать": "Save & activate", "Удалить": "Delete",
    "Вставить стратегию": "Insert strategy", "Вставить список": "Insert list", "Новый блок (--new)": "New block (--new)",
    "Вставить": "Insert", "как hostlist": "as hostlist", "как ipset": "as ipset",
    "Сохранено": "Saved", "Профиль удалён": "Profile deleted", "Удалить профиль?": "Delete profile?",
    "Введите название": "Enter a name", "Создать": "Create", "Отмена": "Cancel",
    "Встроенные пресеты нельзя изменять — создайте копию.": "Built-in presets are read-only — make a copy.",
    "Нет своих профилей. Нажмите «Новый профиль».": "No custom profiles yet. Press “New profile”.",
    "Цвет метки": "Label color", "Категория": "Category",
    # dns
    "Сетевой адаптер": "Network adapter", "Все активные адаптеры": "All active adapters",
    "Текущие DNS": "Current DNS", "Применить": "Apply", "Сбросить (автоматически)": "Reset (automatic)",
    "Очистить кэш DNS": "Flush DNS cache", "Использовать DNS-over-HTTPS (Windows 11)":
        "Use DNS-over-HTTPS (Windows 11)", "DoH доступен только в Windows 11": "DoH requires Windows 11",
    "DNS изменён": "DNS changed", "DNS сброшен на автоматический": "DNS reset to automatic",
    "Кэш DNS очищен": "DNS cache flushed", "Ошибка": "Error", "Пинг": "Ping", "автоматически": "automatic",
    "dns_desc_cloudflare": "Быстрый и приватный", "dns_desc_google": "Стабильный публичный DNS",
    "dns_desc_xbox": "Для игр и сервисов Xbox / Microsoft", "dns_desc_adguard": "Блокирует рекламу и трекеры",
    "dns_desc_quad9": "Защита от вредоносных сайтов",
    # файлы
    "Папка Zapret": "Zapret folder", "Пресеты Zapret 2": "Zapret 2 presets", "Пресеты Zapret 1": "Zapret 1 presets",
    "Мои пресеты Zapret 2": "My Zapret 2 presets", "Мои пресеты Zapret 1": "My Zapret 1 presets",
    "Списки доменов и IP": "Domain & IP lists", "Бинарные файлы (bin)": "Binary files (bin)",
    "Программы winws": "winws executables", "Lua-скрипты": "Lua scripts", "Логи программы": "App logs",
    "Данные программы": "App data", "Каталоги стратегий": "Strategy catalogs", "Открыть": "Open",
    "Сменить папку Zapret…": "Change Zapret folder…", "Выберите папку Zapret": "Select the Zapret folder",
    "В папке нет exe\\winws.exe или exe\\winws2.exe": "No exe\\winws.exe or exe\\winws2.exe in this folder",
    "Лог winws": "winws log",
    # настройки
    "Оформление": "Appearance", "Тема": "Theme", "Тёмная": "Dark", "Светлая": "Light",
    "Акцентный цвет": "Accent color", "Эффект окна": "Window effect", "Акрил": "Acrylic", "Размытие": "Blur",
    "Без эффекта": "None", "Прозрачность": "Transparency", "Язык": "Language",
    "Запуск": "Startup", "Запускать вместе с Windows": "Start with Windows",
    "Активировать последний пресет при запуске": "Activate the last preset on start",
    "Значок в трее": "Tray icon", "Сворачивать в трей при закрытии": "Minimize to tray on close",
    "Полная остановка (выгружать драйвер WinDivert)": "Full stop (unload the WinDivert driver)",
    "О программе": "About", "Язык изменится после перезапуска": "Language will change after restart",
    "Перезапустить": "Restart", "Позже": "Later", "Автозапуск включён": "Autostart enabled",
    "Автозапуск выключен": "Autostart disabled", "Не удалось изменить автозапуск": "Failed to change autostart",
    # трей / окно
    "Показать": "Show", "Выход": "Exit", "Программа свёрнута в трей": "The app is minimized to tray",
    "Нет прав администратора — запуск winws и смена DNS работать не будут.":
        "No administrator rights — winws and DNS changes won't work.",
    "Папка Zapret не найдена": "Zapret folder not found",
    "Положите программу в папку Zapret (рядом с папками exe, presets, lists) или укажите её вручную.":
        "Put the app into the Zapret folder (next to exe, presets, lists) or select it manually.",
    "Указать папку…": "Select folder…",
}


def set_lang(lang: str):
    global _lang
    _lang = lang if lang in ("ru", "en") else "ru"


def lang() -> str:
    return _lang


RU_OVERRIDES = {k: v for k, v in EN.items() if k.startswith("dns_desc_")}
EN_DNS = {"dns_desc_cloudflare": "Fast and private", "dns_desc_google": "Reliable public DNS",
          "dns_desc_xbox": "For Xbox / Microsoft games and services", "dns_desc_adguard": "Blocks ads and trackers",
          "dns_desc_quad9": "Protection from malicious sites"}


def tr(key: str, **kw) -> str:
    if key.startswith("dns_desc_"):
        s = EN_DNS.get(key, key) if _lang == "en" else RU_OVERRIDES.get(key, key)
    else:
        s = EN.get(key, key) if _lang == "en" else key
    return s.format(**kw) if kw else s


CAT_LABEL = {"youtube": "YouTube", "discord": "Discord", "telegram": "Telegram", "games": "Игры",
             "ai": "ИИ-сервисы", "custom": "Свои"}


def cat_label(c: str) -> str:
    return tr(CAT_LABEL.get(c, c))

EN.update({"копия": "copy", "Попробуйте сменить DNS на вкладке DNS.": "Try changing DNS on the DNS tab.",
           "winws завершился": "winws has exited"})

EN.update({
    "Редактор": "Editor", "Свои сайты": "Custom sites", "Пресет": "Preset",
    "Добавить сайты, на которых этот пресет будет обходить блокировку": "Add sites this preset should unblock",
    "Вставьте один или несколько сайтов — по одному на строку, через пробел или запятую.\nНапример: example.com, https://site.org/page, 1.2.3.4":
        "Paste one or more sites — one per line, separated by spaces or commas.\nE.g.: example.com, https://site.org/page, 1.2.3.4",
    "Добавить": "Add", "Поиск…": "Search…", "Удалить выбранные": "Delete selected", "Очистить всё": "Clear all",
    "Стратегия": "Strategy", "Авто — как у основного блока пресета": "Auto — same as the preset's main block",
    "Также добавлять IP-адреса сайтов (ipset)": "Also add site IP addresses (ipset)",
    "IP определяются через DoH. Осторожно: у сайтов на Cloudflare/CDN один IP общий для множества других сайтов — обход будет работать и на них.":
        "IPs are resolved via DoH. Note: sites on Cloudflare/CDNs share IPs with many other sites — they will be affected too.",
    "Обновить IP": "Refresh IPs", "Отмена": "Cancel", "Сохранить": "Save", "Добавлено сайтов": "Sites added",
    "Найдено IP": "IPs found", "Добавлено": "Added", "уже были": "already present", "не распознано": "not recognized",
    "Определяю IP-адреса…": "Resolving IP addresses…", "не удалось определить": "failed to resolve",
    "Сайты сохранены, пресет перезапускается": "Sites saved, restarting preset", "Сайты сохранены": "Sites saved",
    "Удалить пресет?": "Delete preset?", "Пресет удалён": "Preset deleted",
    "Быстрый доступ к вашим пресетам, спискам и логам": "Quick access to your presets, lists and logs",
    "Мои пресеты": "My presets", "Лог winws": "winws log", "Логи программы": "App logs",
    "Встроенные пресеты Zapret 2": "Built-in Zapret 2 presets", "Встроенные пресеты Zapret 1": "Built-in Zapret 1 presets",
    "Папка движка": "Engine folder", "Движок": "Engine", "Сменить папку движка…": "Change engine folder…",
    "Выберите папку движка": "Select engine folder", "Показать системные файлы (для опытных)": "Show system files (advanced)",
    "Профиль": "Profile",
    "Профиль — один файл со всеми настройками, вашими пресетами, своими сайтами и результатами тестов. Его можно сохранить куда угодно и загрузить на этом или другом ПК.":
        "A profile is a single file with all settings, your presets, custom sites and test results. Save it anywhere and load it on this or another PC.",
    "Сохранить профиль…": "Save profile…", "Загрузить профиль…": "Load profile…",
    "Сохранить только настройки…": "Save settings only…", "Перенести данные из Zapret Studio…": "Import data from Zapret Studio…",
    "Сохранить профиль": "Save profile", "Профиль ZapretCloud": "ZapretCloud profile", "Профиль сохранён": "Profile saved",
    "Сохранить настройки": "Save settings", "Настройки сохранены": "Settings saved", "Загрузить профиль": "Load profile",
    "Профиль или настройки": "Profile or settings",
    "Текущие настройки будут заменены данными из файла. Продолжить?": "Current settings will be replaced with the file's data. Continue?",
    "Файл не похож на профиль ZapretCloud": "This file is not a ZapretCloud profile",
    "Профиль загружен. Перезапустить программу, чтобы применить его?": "Profile loaded. Restart the app to apply it?",
    "Папка со старой программой (где лежит ZapretStudio_data)": "Old program folder (containing ZapretStudio_data)",
    "В папке не найдены данные Zapret Studio": "No Zapret Studio data found in this folder",
    "Данные перенесены. Перезапустить программу?": "Data imported. Restart the app?",
    "Обход блокировок на основе zapret (bol-van): winws / winws2, WinDivert.": "Censorship bypass based on zapret (bol-van): winws / winws2, WinDivert.",
    "Не найдены файлы движка (папка engine)": "Engine files not found (engine folder)",
    "Переустановите программу или укажите папку с exe\\winws.exe вручную.": "Reinstall the app or select a folder with exe\\winws.exe manually.",
})

EN.update({
    # конфликты
    "GoodbyeDPI (служба)": "GoodbyeDPI (service)", "WinDivert (чужой драйвер)": "WinDivert (foreign driver)",
    "WinDivert 1.4 (чужой драйвер)": "WinDivert 1.4 (foreign driver)", "winws (другой zapret)": "winws (another zapret)",
    "winws2 (другой zapret)": "winws2 (another zapret)", "winws (служба)": "winws (service)", "winws2 (служба)": "winws2 (service)",
    "zapret (служба Flowseal)": "zapret (Flowseal service)", "Обнаружены мешающие программы": "Conflicting programs detected",
    "Они используют тот же драйвер или тоже обходят блокировки — вместе с ZapretCloud обход может не работать.":
        "They use the same driver or also bypass blocking — together with ZapretCloud the bypass may not work.",
    "VPN останавливать не нужно — просто учтите, что он может мешать.": "No need to stop the VPN — just keep in mind it may interfere.",
    "Запустить всё равно": "Start anyway", "Остановить мешающее и запустить": "Stop them and start",
    "Остановить мешающее": "Stop conflicting", "Пропустить": "Skip", "Включён VPN — он может мешать обходу": "VPN is on — it may interfere",
    "Мешающих программ не найдено": "No conflicting programs found",
    # проверка сайта
    "Проверка сайта": "Site check", "Узнайте, почему сайт не открывается, и включите для него обход":
        "Find out why a site doesn't open and enable bypass for it",
    "Адрес сайта, например rutracker.org или https://site.com/page": "Site address, e.g. rutracker.org or https://site.com/page",
    "Проверить": "Check", "Проверяю…": "Checking…", "Добавить в «Свои сайты»": "Add to “Custom sites”",
    "Также добавить IP-адреса (ipset)": "Also add IP addresses (ipset)", "Добавить и применить": "Add and apply",
    "Проверено с активным пресетом": "Checked with active preset", "Проверено без обхода (пресет не запущен)":
        "Checked without bypass (no preset running)",
    "Сайт открывается": "Site is reachable", "Блокировки не обнаружено.": "No blocking detected.",
    "Блокировка через DNS": "DNS blocking", "Провайдер подменяет адрес сайта. Включите DoH на вкладке DNS — обычно этого достаточно.":
        "Your ISP spoofs the site's address. Enable DoH on the DNS tab — usually that's enough.",
    "Блокировка по IP-адресу": "IP blocking",
    "Подключение к серверу не устанавливается. Добавьте сайт в «Свои сайты» с галочкой «добавлять IP».":
        "Can't connect to the server. Add the site to “Custom sites” with “add IPs” checked.",
    "Блокировка DPI (по имени сайта)": "DPI blocking (by site name)",
    "Провайдер обрывает защищённое соединение. Добавьте сайт в «Свои сайты» — пресет начнёт обходить блокировку.":
        "Your ISP breaks the secure connection. Add the site to “Custom sites” — the preset will bypass it.",
    "Сайт отвечает с ошибкой": "Site responds with an error",
    "Соединение есть, но сервер не ответил нормально. Возможна блокировка или сайт временно не работает.":
        "Connected, but the server didn't respond properly. It may be blocked or temporarily down.",
    "Сайт не найден": "Site not found", "Домен не существует или нет интернета. Проверьте адрес.":
        "The domain doesn't exist or there's no internet. Check the address.",
    "Неверный адрес": "Invalid address", "Введите адрес сайта, например example.com": "Enter a site address, e.g. example.com",
    # сторож / виджет
    "Сторож и мини-виджет": "Watchdog and mini widget",
    "Сторож: проверять, что обход работает, и предлагать другой пресет": "Watchdog: check that bypass works and suggest another preset",
    "Интервал проверки (несколько лёгких запросов, нагрузка минимальна)": "Check interval (a few light requests, minimal load)",
    "мин": "min", "мс": "ms", "Плавающий мини-виджет со статусом и кнопкой вкл/выкл": "Floating mini widget with status and on/off button",
    "Мини-виджет": "Mini widget", "Включить / выключить обход": "Turn bypass on / off", "Обход выключен": "Bypass is off",
    "включите кнопкой справа": "use the button on the right", "Открыть ZapretCloud": "Open ZapretCloud", "Скрыть виджет": "Hide widget",
    "Похоже, обход перестал работать": "Bypass seems to have stopped working", "Пресет не открывает ваши сервисы":
        "The preset doesn't unblock your services", "Не открываются": "Not opening",
    "Предлагаем переключиться на": "We suggest switching to", "у вашего провайдера": "with your ISP", "Применить": "Apply",
    "Других проверенных пресетов пока нет — запустите автоподбор.": "No other tested presets yet — run auto-tune.",
    "Отказаться": "Dismiss",
    # обновления
    "Обновления движка": "Engine updates",
    "winws2 и lua — из bol-van/zapret2, winws — из bol-van/zapret, списки сайтов — из Flowseal (только добавление новых адресов). Перед обновлением делается резервная копия.":
        "winws2 and lua from bol-van/zapret2, winws from bol-van/zapret, site lists from Flowseal (new entries are only added). A backup is made before updating.",
    "Проверять обновления автоматически (раз в 24 часа)": "Check for updates automatically (every 24 hours)",
    "Проверить обновления": "Check for updates", "Обновить выбранное": "Update selected",
    "Откатить последнее обновление": "Roll back last update", "Не удалось проверить": "Check failed", "неизвестно": "unknown",
    "ошибка": "error", "актуально": "up to date", "Доступны обновления": "Updates available", "Всё актуально": "Everything is up to date",
    "Обновление установлено": "Update installed", "Движок обновлён": "Engine updated", "Всё уже актуально": "Already up to date",
    "Откат": "Rollback", "Вернуть файлы движка, которые были до последнего обновления?": "Restore engine files from before the last update?",
    "Откат выполнен": "Rolled back", "Новая версия не запустилась с пресетом — выполнен откат":
        "The new version failed to start with the preset — rolled back",
    "Доступно обновление движка": "Engine update available",
    "Доступна новая версия ZapretCloud": "A new ZapretCloud version is available",
    "Любой результат": "Any result", "от 50%": "50%+", "от 75%": "75%+", "от 90%": "90%+",
    "Показывать только пресеты, которые при автоподборе у вашего провайдера открыли не меньше указанной доли сайтов":
        "Show only presets that opened at least this share of sites during auto-tune with your ISP",
    "нет пресетов с таким результатом — запустите автоподбор или выберите меньший процент":
        "no presets with this result — run auto-tune or choose a lower percentage",
    "Устанавливаю новую версию…": "Installing the new version…",
    "Не удалось скачать обновление": "Failed to download the update",
    "Не удалось запустить установщик": "Failed to start the installer", "Позже": "Later", "Обновить": "Update",
    "Zapret 2 (winws2 + lua)": "Zapret 2 (winws2 + lua)", "Zapret 1 (winws)": "Zapret 1 (winws)",
    "Списки сайтов (Flowseal)": "Site lists (Flowseal)",
    # мастер
    "Мастер настройки": "Setup wizard", "Запустить мастер": "Run wizard",
    "Пройти первоначальную настройку заново: язык, тема, проверка конфликтов, автоподбор.":
        "Go through the initial setup again: language, theme, conflict check, auto-tune.",
    "Добро пожаловать в ZapretCloud": "Welcome to ZapretCloud", "Пропустить мастер": "Skip wizard", "Назад": "Back",
    "Далее": "Next", "Готово": "Finish", "Шаг": "Step", "Тему и цвет можно изменить позже в настройках.":
        "Theme and color can be changed later in settings.",
    "Проверка конфликтов": "Conflict check",
    "Другие программы обхода (GoodbyeDPI, другие сборки zapret и т.п.) мешают работе ZapretCloud.":
        "Other bypass tools (GoodbyeDPI, other zapret builds, etc.) interfere with ZapretCloud.",
    "Проверить снова": "Check again", "Параметры": "Options", "Всё это можно изменить позже в настройках.":
        "All of this can be changed later in settings.",
    "Всё готово!": "All set!",
    "Осталось подобрать пресет, который лучше всего работает у вашего провайдера. Автоподбор по очереди проверит пресеты на YouTube, Discord, Telegram, играх и ИИ-сервисах — это займёт несколько минут.":
        "Now let's find the preset that works best with your ISP. Auto-tune will test presets on YouTube, Discord, Telegram, games and AI services — it takes a few minutes.",
    "Запустить автоподбор сейчас": "Run auto-tune now",
    "Подсказка: если какой-то сайт не открывается — вкладка «Проверка сайта» покажет причину и добавит сайт в обход в один клик.":
        "Tip: if a site doesn't open, the “Site check” tab shows why and adds it to the bypass in one click.",
})

# ---- VPN (2.2) ----
EN.update({
    "остановлен": "stopped", "подключён": "connected", "подключение…": "connecting…", "отключение…": "disconnecting…",
    "выключен": "off", "вкл": "on",
    "не открывался через zapret, теперь идёт через VPN": "didn't open via zapret, now goes through VPN",
    "Включить / выключить VPN": "Turn VPN on / off", "VPN: подключение…": "VPN: connecting…",
    "VPN: отключение…": "VPN: disconnecting…", "МБ": "MB", "с": "s", "КБ": "KB", "ГБ": "GB", "ТБ": "TB", "Б": "B",
    "VPN: весь трафик": "VPN: all traffic", "через VPN": "via VPN", "всё идёт через VPN": "everything goes via VPN",
    "сейчас всё идёт через zapret": "everything goes via zapret now", "сейчас сайты идут напрямую": "sites go direct now",
    "VPN выключен": "VPN is off",
    "Не помогло? Откройте через VPN": "Didn't help? Open it via VPN",
    "Сайт всегда будет идти через ваш VPN-сервер, остальные — как раньше, через zapret.":
        "This site will always go through your VPN server, the rest — via zapret as before.",
    "Открывать через VPN": "Open via VPN", "Добавлено": "Added",
    "Сайт добавлен в список VPN. Осталось добавить сервер на вкладке VPN":
        "Site added to the VPN list. Now add a server on the VPN tab",
    "Включаю VPN…": "Turning VPN on…", "Не удалось построить QR-код": "Couldn't build the QR code",
    "Копировать ссылку": "Copy link", "Скопировано": "Copied", "Закрыть": "Close",
    "Проверить задержку": "Check latency", "QR для телефона": "QR for phone", "Нужен компонент VPN": "VPN component required",
    "Скачать компонент": "Download component", "Серверы": "Servers",
    "Вставьте ссылку vless://, vpn:// или ссылку на подписку": "Paste a vless://, vpn:// or subscription link",
    "Из буфера": "From clipboard", "Использовать": "Use", "QR-код": "QR code", "Режим работы": "Mode",
    "TUN — весь трафик компьютера (игры, Discord, все программы)": "TUN — all PC traffic (games, Discord, all apps)",
    "Системный прокси — браузеры и программы с поддержкой прокси": "System proxy — browsers and proxy-aware apps",
    "Как подключать": "Connection type",
    "Умная — zapret, а VPN только там, где zapret не справился": "Smart — zapret, VPN only where zapret fails",
    "Только сайты из списка": "Only sites from the list", "Всё через VPN": "Everything via VPN",
    "Что пускать через VPN": "What goes via VPN",
    "Автоматически переводить на VPN сайты, которые не открываются через zapret":
        "Automatically move sites that don't open via zapret to VPN",
    "Российские сайты всегда напрямую": "Russian sites always direct",
    "Включать VPN при запуске программы": "Turn VPN on when the app starts", "Сайты": "Sites", "Через VPN": "Via VPN",
    "Всегда напрямую (через zapret)": "Always direct (via zapret)", "Сбросить выученные": "Reset learned",
    "Починить VPN": "Repair VPN", "Поддержать": "Support", "Поддержать проект": "Support the project", "Поддержать разработку ZapretCloud": "Support ZapretCloud development", "ZapretCloud бесплатный. Если программа вам помогает — можно поддержать разработку любой суммой. Спасибо! ♥": "ZapretCloud is free. If it helps you, you can support development with any amount. Thank you! ♥", "Отсканируйте камерой телефона или нажмите кнопку ниже": "Scan with your phone camera or press the button below", "Кошелёк ЮMoney:": "YooMoney wallet:", "Копировать": "Copy", "Перевести через ЮMoney": "Donate via YooMoney", "Криптовалюта (MetaMask)": "Crypto (MetaMask)", "USDT, USDC, ETH, BNB и другие токены в сетях Ethereum, BNB Chain, Polygon, Arbitrum, Base. Проверьте сеть перед отправкой.": "USDT, USDC, ETH, BNB and other tokens on Ethereum, BNB Chain, Polygon, Arbitrum, Base. Check the network before sending.", "Отсканируйте в MetaMask или другом кошельке. Проверьте сеть перед отправкой.": "Scan with MetaMask or another wallet. Check the network before sending.", "VPN отключился: запущен другой VPN": "VPN stopped: another VPN is running", "Запущен другой VPN": "Another VPN is running", "Два VPN одновременно не работают — закройте его и включите VPN снова.": "Two VPNs can't run at the same time — close it and turn the VPN on again.", "Если VPN не включается или завис: перезапустить его и убрать зависшие процессы": "If VPN won't start or hangs: restart it and clean up stuck processes",
    "Убрать сайты, которые программа перевела на VPN автоматически": "Remove sites the app moved to VPN automatically",
    "Программы": "Apps", "Добавить программу…": "Add app…", "VPN / напрямую": "VPN / direct",
    "Раздача на телефон": "Share to phone", "Раздавать в домашнюю сеть": "Share to home network", "порт": "port",
    "системный прокси": "system proxy", "умный режим": "smart mode", "только список": "list only",
    "всё через VPN": "everything via VPN", "Подключение…": "Connecting…", "Отключение…": "Disconnecting…",
    "VPN подключён": "VPN connected",
    "Добавьте свой сервер ниже — ссылкой vless://, vpn:// или подпиской.":
        "Add your server below — via a vless://, vpn:// link or a subscription.",
    "всего": "total", "задержка": "latency", "задержка: нет ответа": "latency: no response",
    "Сейчас через VPN": "Via VPN now", "и ещё": "and", "Компонент VPN установлен": "VPN component installed",
    "Не удалось скачать компонент": "Couldn't download the component", "нет ответа": "no response",
    "Серверов пока нет": "No servers yet", "Подписка": "Subscription", "из": "of", "использовано": "used",
    "до": "until", "обновлена": "updated", "Удалить подписку и её серверы": "Delete subscription and its servers",
    "Загрузка…": "Loading…", "Добавлено серверов": "Servers added", "пропущено": "skipped",
    "Ссылки не найдены": "No links found", "Удалить сервер": "Delete server", "Подписки обновлены": "Subscriptions updated",
    "Для этого сервера нет ссылки — QR-код недоступен": "This server has no link — QR code unavailable",
    "QR-код сервера": "Server QR code", "авто": "auto", "Переведён на VPN автоматически": "Moved to VPN automatically",
    "Выучено автоматически": "Learned automatically", "Неверный адрес сайта": "Invalid site address",
    "напрямую": "direct", "Программ пока нет": "No apps yet", "Выберите программу": "Choose an app",
    "Выключено. Включите галочку, затем на телефоне укажите прокси в настройках Wi-Fi.":
        "Off. Tick the box, then set the proxy in your phone's Wi-Fi settings.",
    "Заработает после включения VPN": "Will work once VPN is on", "Работает": "Working",
    "Настройки → Wi-Fi → (i) у вашей сети → Прокси → Вручную": "Settings → Wi-Fi → (i) next to your network → Configure Proxy → Manual",
    "Настройки → Wi-Fi → ваша сеть → Изменить → Прокси → Вручную": "Settings → Wi-Fi → your network → Edit → Proxy → Manual",
    "Сервер": "Server", "Порт": "Port", "Другие адреса этого ПК": "Other addresses of this PC",
    "Доступ разрешён только из домашней сети. Работает, пока ПК включён и VPN подключён.":
        "Access is allowed only from your home network. Works while the PC is on and VPN is connected.",
    "Ваш сервер подключается только там, где zapret не справляется — остальное работает напрямую, без потери скорости":
        "Your server is used only where zapret fails — everything else goes direct, at full speed",
    "VPN работает на ядре sing-box (бесплатное, с открытым кодом). Оно скачается один раз с GitHub — около 33 МБ.":
        "VPN runs on the sing-box core (free, open source). It is downloaded once from GitHub — about 33 MB.",
    "Готовые наборы — сервисы, которые сами закрыты для России или блокируются по IP (zapret им не поможет):":
        "Ready-made sets — services that block Russia themselves or are blocked by IP (zapret can't help):",
    "Выбранная программа всегда идёт через VPN или всегда напрямую — независимо от сайтов. Например: Telegram или игра через VPN, торрент-клиент напрямую. Лучше всего работает в режиме TUN.":
        "A chosen app always goes via VPN or always direct — regardless of sites. E.g. Telegram or a game via VPN, a torrent client direct. Works best in TUN mode.",
    "Телефон или другое устройство в той же Wi-Fi сети будет работать через этот компьютер: где справляется zapret — через zapret, где нет — через VPN.":
        "A phone or other device on the same Wi-Fi will work through this PC: via zapret where it works, via VPN where it doesn't.",
    "TUN перехватывает весь трафик. zapret при этом продолжает работать — программа сама перенастроит его на физическую сеть.":
        "TUN captures all traffic. zapret keeps working — the app reconfigures it for the physical network automatically.",
    "Системный прокси подхватывают браузеры и большинство программ. Игры и Discord-голос могут идти мимо — для них выберите TUN.":
        "Browsers and most apps use the system proxy. Games and Discord voice may bypass it — choose TUN for them.",
    "Отсканируйте камерой в Happ, v2RayTun или Streisand на телефоне — сервер добавится сам. Не показывайте этот код посторонним: в нём ключ доступа к серверу.":
        "Scan it in Happ, v2RayTun or Streisand on your phone — the server will be added. Don't show this code to others: it contains your server access key.",
    "Раз в 6 часов программа перепроверяет их и возвращает на zapret те, что снова открываются напрямую.":
        "Every 6 hours the app re-checks them and moves back to zapret those that open directly again.",
    "Добавьте сервер": "Add a server", "Компонент VPN не установлен": "VPN component is not installed",
    "Ошибка конфигурации": "Configuration error", "VPN не запустился": "VPN failed to start",
    "VPN не отвечает": "VPN is not responding", "VPN неожиданно отключился": "VPN disconnected unexpectedly",
    "Этот сервер уже добавлен": "This server is already added", "Не удалось загрузить подписку": "Couldn't load the subscription",
    "в ссылке нет публичного ключа Reality (pbk)": "the link has no Reality public key (pbk)",
    "транспорт XHTTP поддерживается только в Xray — переключите сервер на TCP/WS/gRPC":
        "XHTTP transport is Xray-only — switch the server to TCP/WS/gRPC",
    "не удалось разобрать адрес сервера": "couldn't parse the server address", "неверный порт": "invalid port",
    "в ссылке нет UUID": "the link has no UUID", "не удалось декодировать vmess-ссылку": "couldn't decode the vmess link",
    "не удалось декодировать ссылку vpn://": "couldn't decode the vpn:// link",
    "flow xtls-rprx-vision требует TLS или Reality": "flow xtls-rprx-vision requires TLS or Reality",
    "подписка зашифрована для Happ (happ://crypt) — попросите обычную ссылку подписки":
        "the subscription is encrypted for Happ (happ://crypt) — ask for a regular subscription link",
    "ИИ-сервисы (ChatGPT, Claude, Gemini, Copilot…)": "AI services (ChatGPT, Claude, Gemini, Copilot…)",
    "Соцсети Meta и X (Instagram, Facebook, Threads, X)": "Meta & X social networks (Instagram, Facebook, Threads, X)",
    "Стриминг и музыка (Spotify, Netflix, SoundCloud…)": "Streaming & music (Spotify, Netflix, SoundCloud…)",
    "Разработка (Docker Hub, Notion, Figma, JetBrains…)": "Development (Docker Hub, Notion, Figma, JetBrains…)",
    "VPN выключен на время автоподбора и включится после него": "VPN is paused during auto-tune and will turn back on afterwards",
    "Всегда через VPN": "Always via VPN",
    "Отметьте готовые наборы — это сервисы, которые сами закрыты для России или блокируются по IP (zapret им не поможет). Ниже можно добавить свои сайты.":
        "Tick ready-made sets — services that block Russia themselves or are blocked by IP (zapret can't help). You can add your own sites below.",
    "Свои сайты через VPN": "Your sites via VPN", "Исключения — никогда через VPN": "Exceptions — never via VPN",
    "Эти сайты всегда идут напрямую через zapret — даже в режиме «Всё через VPN» и даже если программа хотела перевести их на VPN. Например: банк, госуслуги или игра, которой VPN мешает. Обычно этот список можно оставить пустым.":
        "These sites always go direct via zapret — even in “Everything via VPN” mode and even if the app wanted to move them to VPN. E.g. a bank, government services or a game that VPN breaks. Usually this list can stay empty.",
    "Адрес сайта, например example.com": "Site address, e.g. example.com", "Удалить выбранный": "Remove selected",
    "Пока пусто — добавьте сайт ниже": "Empty for now — add a site below", "Пусто — исключений нет": "Empty — no exceptions",
    "QR для Telegram на телефоне": "QR for Telegram on phone", "Не найден адрес компьютера в домашней сети": "PC address in the home network not found",
    "Telegram через компьютер": "Telegram via this PC",
    "Telegram не использует прокси из настроек Wi-Fi, ему нужен свой. Отсканируйте код камерой телефона — откроется Telegram и предложит подключить прокси. Работает, пока телефон в домашней Wi-Fi сети, а на ПК включён VPN.":
        "Telegram ignores the Wi-Fi proxy setting and needs its own. Scan the code with your phone camera — Telegram will open and offer to connect the proxy. Works while the phone is on your home Wi-Fi and VPN is on on the PC.",
    "свой прокси — кнопка «QR для Telegram» ниже, или вручную: Настройки → Данные и память → Прокси → SOCKS5, тот же сервер и порт":
        "its own proxy — the “QR for Telegram” button below, or manually: Settings → Data and Storage → Proxy → SOCKS5, same server and port",
    "Telegram (сообщения, медиа, звонки)": "Telegram (messages, media, calls)",
    "Работа и разработка (Notion, Figma, Docker Hub, JetBrains…)": "Work & development (Notion, Figma, Docker Hub, JetBrains…)",
    "zapret: остановлен": "zapret: stopped", "zapret выключен": "zapret is off",
})
