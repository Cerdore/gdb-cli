"""
Russian Catalog - Русский каталог переводов
"""

RU_CATALOG = {
    # === CLI Group ===
    "cli.group.help": "GDB CLI для ИИ - Тонкий клиент CLI + встроенный Python RPC Server GDB",

    # === load command ===
    "cli.load.doc": "Загрузить core dump и запустить постоянный процесс GDB",
    "cli.load.binary_help": "Путь к исполняемому файлу",
    "cli.load.core_help": "Путь к файлу core dump",
    "cli.load.sysroot_help": "Путь sysroot (для межмашинной отладки)",
    "cli.load.solib_prefix_help": "Префикс разделяемых библиотек",
    "cli.load.source_dir_help": "Каталог исходного кода",
    "cli.load.timeout_help": "Таймаут пульса в секундах (по умолчанию: 600)",
    "cli.load.gdb_path_help": "Путь к исполняемому файлу GDB",

    # === attach command ===
    "cli.attach.doc": "Подключиться к запущенному процессу",
    "cli.attach.pid_help": "PID целевого процесса",
    "cli.attach.binary_help": "Путь к исполняемому файлу (опционально)",
    "cli.attach.scheduler_locking_help": "Включить scheduler-locking",
    "cli.attach.non_stop_help": "Включить режим non-stop",
    "cli.attach.timeout_help": "Таймаут пульса в секундах (по умолчанию: 600)",
    "cli.attach.allow_write_help": "Разрешить изменение памяти",
    "cli.attach.allow_call_help": "Разрешить вызовы функций",

    # === eval-cmd command ===
    "cli.eval_cmd.doc": "Вычислить выражение C/C++",
    "cli.eval_cmd.session_help": "ID сессии",
    "cli.eval_cmd.max_depth_help": "Лимит глубины рекурсии",
    "cli.eval_cmd.max_elements_help": "Лимит элементов массива",

    # === threads command ===
    "cli.threads.doc": "Список потоков",
    "cli.threads.session_help": "ID сессии",
    "cli.threads.range_help": "Диапазон потоков (напр., 3-10)",
    "cli.threads.limit_help": "Максимальное количество",
    "cli.threads.filter_state_help": "Фильтр по состоянию (running/stopped)",

    # === bt command ===
    "cli.bt.doc": "Получить backtrace",
    "cli.bt.session_help": "ID сессии",
    "cli.bt.thread_help": "Указать ID потока",
    "cli.bt.limit_help": "Максимальное количество фреймов",
    "cli.bt.full_help": "Включить локальные переменные",
    "cli.bt.range_help": "Диапазон фреймов (напр., 5-15)",

    # === frame command ===
    "cli.frame.doc": "Выбрать стековый фрейм",
    "cli.frame.session_help": "ID сессии",

    # === locals-cmd command ===
    "cli.locals_cmd.doc": "Получить локальные переменные",
    "cli.locals_cmd.session_help": "ID сессии",
    "cli.locals_cmd.thread_help": "ID потока",
    "cli.locals_cmd.frame_help": "Номер фрейма",

    # === exec command ===
    "cli.exec.doc": "Выполнить сырую команду GDB",
    "cli.exec.session_help": "ID сессии",
    "cli.exec.safety_level_help": "Уровень безопасности (readonly/readwrite/full)",

    # === stop command ===
    "cli.stop.doc": "Остановить сессию и безопасно выйти из GDB",
    "cli.stop.session_help": "ID сессии",

    # === sessions command ===
    "cli.sessions.doc": "Список всех активных сессий",

    # === status command ===
    "cli.status.doc": "Проверить статус сессии",
    "cli.status.session_help": "ID сессии",

    # === eval-element command ===
    "cli.eval_element.doc": "Доступ к элементу массива/контейнера",
    "cli.eval_element.session_help": "ID сессии",
    "cli.eval_element.index_help": "Индекс элемента",
    "cli.eval_element.max_depth_help": "Лимит глубины рекурсии",

    # === thread-apply command ===
    "cli.thread_apply.doc": "Пакетные операции над потоками",
    "cli.thread_apply.session_help": "ID сессии",
    "cli.thread_apply.threads_help": "Список ID потоков (напр., 1,3,5)",
    "cli.thread_apply.all_help": "Применить ко всем потокам",

    # === args command ===
    "cli.args.doc": "Получить аргументы функции",
    "cli.args.session_help": "ID сессии",
    "cli.args.thread_help": "ID потока",
    "cli.args.frame_help": "Номер фрейма",

    # === registers command ===
    "cli.registers.doc": "Просмотреть значения регистров",
    "cli.registers.session_help": "ID сессии",
    "cli.registers.names_help": "Имена регистров (через запятую, напр., rax,rbx,rip)",
    "cli.registers.thread_help": "ID потока",
    "cli.registers.frame_help": "Номер фрейма",

    # === memory command ===
    "cli.memory.doc": "Проверить содержимое памяти",
    "cli.memory.session_help": "ID сессии",
    "cli.memory.size_help": "Байты для чтения (по умолчанию: 64, макс: 4096)",
    "cli.memory.fmt_help": "Формат вывода (hex/bytes/string)",

    # === ptype command ===
    "cli.ptype.doc": "Просмотреть информацию о типе выражения",
    "cli.ptype.session_help": "ID сессии",

    # === thread-switch command ===
    "cli.thread_switch.doc": "Переключить текущий поток",
    "cli.thread_switch.session_help": "ID сессии",

    # === up command ===
    "cli.up.doc": "Переместиться к вызывающему в стеке",
    "cli.up.session_help": "ID сессии",

    # === down command ===
    "cli.down.doc": "Переместиться к вызываемому в стеке",
    "cli.down.session_help": "ID сессии",

    # === sharedlibs command ===
    "cli.sharedlibs.doc": "Просмотреть загруженные разделяемые библиотеки",
    "cli.sharedlibs.session_help": "ID сессии",

    # === disasm command ===
    "cli.disasm.doc": "Дизассемблировать",
    "cli.disasm.session_help": "ID сессии",
    "cli.disasm.start_help": "Начальный адрес или имя функции (по умолчанию: текущий PC)",
    "cli.disasm.count_help": "Количество инструкций (по умолчанию: 20)",
    "cli.disasm.thread_help": "ID потока",
    "cli.disasm.frame_help": "Номер фрейма",

    # === env-check command ===
    "cli.env_check.doc": "Проверка окружения: версия GDB, права ptrace, версия Python",

    # === Errors ===
    "errors.session_not_found": "Сессия не найдена: {session_id}",
    "errors.connection_error": "Ошибка соединения",
    "errors.variable_not_found.suggestion": "Проверьте правильность имени переменной, используйте 'info locals' для просмотра переменных в текущей области видимости",
    "errors.syntax_error.suggestion": "Проверьте синтаксис выражения, убедитесь, что формат C/C++ правильный",
    "errors.invalid_thread.suggestion": "Используйте команду 'threads' для просмотра списка доступных потоков",
    "errors.invalid_frame.suggestion": "Используйте команду 'bt' для просмотра списка фреймов",
    "errors.memory_access_failed.suggestion": "Целевая область памяти недоступна, переменная может быть оптимизирована",
    "errors.no_debug_info.suggestion": "Попробуйте загрузить debuginfo: 'dnf debuginfo-install' или проверьте файл .debug",
    "errors.process_not_found.suggestion": "Проверьте существование процесса: 'ps aux | grep <имя_процесса>'",
    "errors.ptrace_denied.suggestion": "Выполните: 'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope'",
    "errors.command_blocked.suggestion": "Команда заблокирована политикой безопасности, используйте флаг --allow-write или --allow-call",
    "errors.command_timeout.suggestion": "Таймаут команды, попробуйте увеличить --timeout или упростить операцию",
    "errors.load_timeout.suggestion": "Таймаут загрузки core файла, файл может быть слишком большим, попробуйте увеличить таймаут",
    "errors.socket_not_found.suggestion": "Сессия GDB могла завершиться, перезапустите 'gdb-cli load' или 'gdb-cli attach'",
    "errors.connection_refused.suggestion": "GDB RPC Server не отвечает, проверьте, запущен ли процесс GDB",

    # === Environment Check ===
    "env_check.gdb_not_found.error": "GDB не найден в PATH",
    "env_check.gdb_not_found.suggestion": "Установите GDB: 'brew install gdb' (macOS) или 'yum install gdb' (Linux)",
    "env_check.gdb_below_minimum.error": "Версия GDB {version} ниже минимальной {minimum}",
    "env_check.gdb_below_minimum.suggestion": "Обновите GDB до версии 9.0 или выше",
    "env_check.gdb_version_warning": "Версия GDB {version} поддерживается, но рекомендуется {recommended}+",
    "env_check.gdb_recommended_suggestion": "Рекомендуется обновить до GDB 15+ для лучшей совместимости с rockylinux/el9",
    "env_check.ptrace_restricted.warning": "ptrace ограничен (scope=1). Можно подключаться только к дочерним процессам.",
    "env_check.ptrace_heavily_restricted.error": "ptrace сильно ограничен (scope={scope})",
    "env_check.ptrace_heavily_restricted.suggestion": "Выполните: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope",
    "env_check.ptrace_sysctl_suggestion": "Или выполните: sysctl kernel.yama.ptrace_scope=0",
    "env_check.ptrace_scope_read_error.warning": "Невозможно прочитать ptrace_scope (доступ запрещён)",
    "env_check.debuginfo_not_found.suggestion": "Бинарный файл лишён отладочной информации (no debug info)",
    "env_check.debuginfo_install_rhel": "RHEL/CentOS: dnf debuginfo-install {package}",
    "env_check.debuginfo_install_ubuntu": "Ubuntu/Debian: apt-get install {package}-dbgsym",
    "env_check.debuginfo_install_fedora": "Fedora: dnf install {package}-debuginfo",
    "env_check.debuginfo_separate_file": "Или используйте отдельный .debug файл: add-symbol-file /path/to/{package}.debug",

    # === Runtime messages ===
    "errors.session_no_socket": "Сессия не имеет сокета: {session_id}",
    "cli.load.session_reused_message": "Сессия для этого core-файла уже существует",
    "cli.load.failed": "Не удалось запустить GDB",
    "cli.attach.session_reused_message": "Сессия для этого PID уже существует",
    "cli.attach.failed": "Не удалось подключиться к процессу",
    "cli.target.invalid_format": "Неверный формат удалённого адреса: {remote}",
    "cli.target.session_reused_message": "Сессия для этой удалённой цели уже существует",
    "cli.target.failed": "Не удалось подключиться к цели",
    "cli.status.gdb_loading_message": "Процесс GDB жив, пока не отвечает",
    "cli.status.session_dead": "Сессия завершена",
    "cli.status.gdb_process_dead": "Процесс GDB {pid} больше не существует",
    "cli.thread_apply.require_target": "Необходимо указать --all или --threads",

    # === JSON output hints ===
    "hints.threads_pagination": "используйте 'threads --range START-END' для конкретных потоков",
    "hints.bt_pagination": "используйте 'bt --range START-END' для конкретных фреймов",
    "hints.eval_large_array": "используйте 'eval-element' для доступа к конкретным индексам массива",
}
