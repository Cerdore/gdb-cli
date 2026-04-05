"""
Chinese (Simplified) Catalog - 简体中文翻译目录
"""

ZH_CN_CATALOG = {
    # === CLI Group ===
    "cli.group.help": "GDB CLI for AI - 瘦客户端 CLI + GDB 内置 Python RPC Server",

    # === load command ===
    "cli.load.doc": "加载 core dump，启动 GDB 常驻进程",
    "cli.load.binary_help": "可执行文件路径",
    "cli.load.core_help": "Core dump 文件路径",
    "cli.load.sysroot_help": "sysroot 路径 (跨机器调试)",
    "cli.load.solib_prefix_help": "共享库前缀",
    "cli.load.source_dir_help": "源码目录",
    "cli.load.timeout_help": "心跳超时秒数 (默认 600)",
    "cli.load.gdb_path_help": "GDB 可执行文件路径",

    # === attach command ===
    "cli.attach.doc": "Attach 到运行中进程",
    "cli.attach.pid_help": "目标进程 PID",
    "cli.attach.binary_help": "可执行文件路径 (可选)",
    "cli.attach.scheduler_locking_help": "启用 scheduler-locking",
    "cli.attach.non_stop_help": "启用 non-stop 模式",
    "cli.attach.timeout_help": "心跳超时秒数 (默认 600)",
    "cli.attach.allow_write_help": "允许内存修改",
    "cli.attach.allow_call_help": "允许函数调用",

    # === eval-cmd command ===
    "cli.eval_cmd.doc": "求值 C/C++ 表达式",
    "cli.eval_cmd.session_help": "会话 ID",
    "cli.eval_cmd.max_depth_help": "递归深度限制",
    "cli.eval_cmd.max_elements_help": "数组元素限制",

    # === threads command ===
    "cli.threads.doc": "列出线程",
    "cli.threads.session_help": "会话 ID",
    "cli.threads.range_help": "线程范围 (如 3-10)",
    "cli.threads.limit_help": "最大返回数量",
    "cli.threads.filter_state_help": "过滤状态 (running/stopped)",

    # === bt command ===
    "cli.bt.doc": "获取 backtrace",
    "cli.bt.session_help": "会话 ID",
    "cli.bt.thread_help": "指定线程 ID",
    "cli.bt.limit_help": "最大帧数",
    "cli.bt.full_help": "包含局部变量",
    "cli.bt.range_help": "帧范围 (如 5-15)",

    # === frame command ===
    "cli.frame.doc": "选择栈帧",
    "cli.frame.session_help": "会话 ID",

    # === locals-cmd command ===
    "cli.locals_cmd.doc": "获取局部变量",
    "cli.locals_cmd.session_help": "会话 ID",
    "cli.locals_cmd.thread_help": "线程 ID",
    "cli.locals_cmd.frame_help": "栈帧编号",

    # === exec command ===
    "cli.exec.doc": "执行原始 GDB 命令",
    "cli.exec.session_help": "会话 ID",
    "cli.exec.safety_level_help": "安全级别 (readonly/readwrite/full)",

    # === stop command ===
    "cli.stop.doc": "停止会话，安全退出 GDB",
    "cli.stop.session_help": "会话 ID",

    # === sessions command ===
    "cli.sessions.doc": "列出所有活跃会话",

    # === status command ===
    "cli.status.doc": "查看会话状态",
    "cli.status.session_help": "会话 ID",

    # === eval-element command ===
    "cli.eval_element.doc": "访问数组/容器中的特定元素",
    "cli.eval_element.session_help": "会话 ID",
    "cli.eval_element.index_help": "元素索引",
    "cli.eval_element.max_depth_help": "递归深度限制",

    # === thread-apply command ===
    "cli.thread_apply.doc": "批量线程操作",
    "cli.thread_apply.session_help": "会话 ID",
    "cli.thread_apply.threads_help": "线程 ID 列表 (如 1,3,5)",
    "cli.thread_apply.all_help": "应用于所有线程",

    # === args command ===
    "cli.args.doc": "获取函数参数",
    "cli.args.session_help": "会话 ID",
    "cli.args.thread_help": "线程 ID",
    "cli.args.frame_help": "栈帧编号",

    # === registers command ===
    "cli.registers.doc": "查看寄存器值",
    "cli.registers.session_help": "会话 ID",
    "cli.registers.names_help": "寄存器名列表，逗号分隔 (如 rax,rbx,rip)",
    "cli.registers.thread_help": "线程 ID",
    "cli.registers.frame_help": "栈帧编号",

    # === memory command ===
    "cli.memory.doc": "检查内存内容",
    "cli.memory.session_help": "会话 ID",
    "cli.memory.size_help": "读取字节数 (默认 64, 最大 4096)",
    "cli.memory.fmt_help": "输出格式 (hex/bytes/string)",

    # === ptype command ===
    "cli.ptype.doc": "查看表达式的类型信息",
    "cli.ptype.session_help": "会话 ID",

    # === thread-switch command ===
    "cli.thread_switch.doc": "切换当前线程",
    "cli.thread_switch.session_help": "会话 ID",

    # === up command ===
    "cli.up.doc": "向调用者方向移动栈帧",
    "cli.up.session_help": "会话 ID",

    # === down command ===
    "cli.down.doc": "向被调用者方向移动栈帧",
    "cli.down.session_help": "会话 ID",

    # === sharedlibs command ===
    "cli.sharedlibs.doc": "查看加载的共享库",
    "cli.sharedlibs.session_help": "会话 ID",

    # === disasm command ===
    "cli.disasm.doc": "反汇编",
    "cli.disasm.session_help": "会话 ID",
    "cli.disasm.start_help": "起始地址或函数名 (默认当前 PC)",
    "cli.disasm.count_help": "指令数量 (默认 20)",
    "cli.disasm.thread_help": "线程 ID",
    "cli.disasm.frame_help": "栈帧编号",

    # === env-check command ===
    "cli.env_check.doc": "环境自检：gdb版本、ptrace权限、Python版本",

    # === Errors ===
    "errors.session_not_found": "会话未找到: {session_id}",
    "errors.connection_error": "连接错误",
    "errors.variable_not_found.suggestion": "检查变量名是否正确，使用 'info locals' 查看当前作用域的变量",
    "errors.syntax_error.suggestion": "检查表达式语法，确保 C/C++ 表达式格式正确",
    "errors.invalid_thread.suggestion": "使用 'threads' 命令查看可用线程列表",
    "errors.invalid_frame.suggestion": "使用 'bt' 命令查看栈帧列表",
    "errors.memory_access_failed.suggestion": "目标内存区域不可访问，可能是优化导致变量被优化掉",
    "errors.no_debug_info.suggestion": "尝试加载 debuginfo: 'dnf debuginfo-install' 或检查 .debug 文件",
    "errors.process_not_found.suggestion": "检查进程是否存在: 'ps aux | grep <进程名>'",
    "errors.ptrace_denied.suggestion": "运行: 'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope'",
    "errors.command_blocked.suggestion": "该命令被安全策略阻止，使用 --allow-write 或 --allow-call 参数",
    "errors.command_timeout.suggestion": "命令执行超时，尝试增加 --timeout 参数或简化操作",
    "errors.load_timeout.suggestion": "core 文件加载超时，可能文件过大，尝试增加超时时间",
    "errors.socket_not_found.suggestion": "GDB 会话可能已终止，重新运行 'gdb-cli load' 或 'gdb-cli attach'",
    "errors.connection_refused.suggestion": "GDB RPC Server 未响应，检查 GDB 进程是否正常运行",

    # === Environment Check ===
    "env_check.gdb_not_found.error": "GDB 不在 PATH 中",
    "env_check.gdb_not_found.suggestion": "安装 GDB: 'brew install gdb' (macOS) 或 'yum install gdb' (Linux)",
    "env_check.gdb_below_minimum.error": "GDB 版本 {version} 低于最低要求 {minimum}",
    "env_check.gdb_below_minimum.suggestion": "升级 GDB 到 9.0 或更高版本",
    "env_check.gdb_version_warning": "GDB 版本 {version} 支持，但推荐 {recommended}+",
    "env_check.gdb_recommended_suggestion": "建议升级到 GDB 15+ 以获得与 rockylinux/el9 的最佳兼容性",
    "env_check.ptrace_restricted.warning": "ptrace 受限 (scope=1)。只能 attach 子进程。",
    "env_check.ptrace_heavily_restricted.error": "ptrace 严重受限 (scope={scope})",
    "env_check.ptrace_heavily_restricted.suggestion": "运行: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope",
    "env_check.ptrace_sysctl_suggestion": "或运行: sysctl kernel.yama.ptrace_scope=0",
    "env_check.ptrace_scope_read_error.warning": "无法读取 ptrace_scope (权限不足)",
    "env_check.debuginfo_not_found.suggestion": "二进制文件已被剥离符号 (无调试信息)",
    "env_check.debuginfo_install_rhel": "RHEL/CentOS: dnf debuginfo-install {package}",
    "env_check.debuginfo_install_ubuntu": "Ubuntu/Debian: apt-get install {package}-dbgsym",
    "env_check.debuginfo_install_fedora": "Fedora: dnf install {package}-debuginfo",
    "env_check.debuginfo_separate_file": "或使用独立的 .debug 文件: add-symbol-file /path/to/{package}.debug",

    # === JSON output hints ===
    "hints.threads_pagination": "使用 'threads --range START-END' 查看特定线程",
    "hints.bt_pagination": "使用 'bt --range START-END' 查看特定栈帧",
    "hints.eval_large_array": "使用 'eval-element' 访问特定数组索引",
}
