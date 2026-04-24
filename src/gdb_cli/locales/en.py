"""
English Catalog - 英语翻译目录

Source language for all translations.
"""

ENGLISH_CATALOG = {
    # === CLI Group ===
    "cli.group.help": "GDB CLI for AI - Thin client CLI + GDB built-in Python RPC Server",

    # === load command ===
    "cli.load.doc": "Load core dump and start persistent GDB process",
    "cli.load.binary_help": "Executable file path",
    "cli.load.core_help": "Core dump file path",
    "cli.load.sysroot_help": "sysroot path (for cross-machine debugging)",
    "cli.load.solib_prefix_help": "Shared library prefix",
    "cli.load.source_dir_help": "Source code directory",
    "cli.load.timeout_help": "Heartbeat timeout in seconds (default: 600)",
    "cli.load.gdb_path_help": "GDB executable path",

    # === attach command ===
    "cli.attach.doc": "Attach to running process",
    "cli.attach.pid_help": "Target process PID",
    "cli.attach.binary_help": "Executable file path (optional)",
    "cli.attach.scheduler_locking_help": "Enable scheduler-locking",
    "cli.attach.non_stop_help": "Enable non-stop mode",
    "cli.attach.timeout_help": "Heartbeat timeout in seconds (default: 600)",
    "cli.attach.allow_write_help": "Allow memory modification",
    "cli.attach.allow_call_help": "Allow function calls",

    # === eval-cmd command ===
    "cli.eval_cmd.doc": "Evaluate C/C++ expression",
    "cli.eval_cmd.session_help": "Session ID",
    "cli.eval_cmd.max_depth_help": "Recursion depth limit",
    "cli.eval_cmd.max_elements_help": "Array element limit",

    # === threads command ===
    "cli.threads.doc": "List threads",
    "cli.threads.session_help": "Session ID",
    "cli.threads.range_help": "Thread range (e.g., 3-10)",
    "cli.threads.limit_help": "Maximum return count",
    "cli.threads.filter_state_help": "Filter by state (running/stopped)",

    # === bt command ===
    "cli.bt.doc": "Get backtrace",
    "cli.bt.session_help": "Session ID",
    "cli.bt.thread_help": "Specify thread ID",
    "cli.bt.limit_help": "Maximum frame count",
    "cli.bt.full_help": "Include local variables",
    "cli.bt.range_help": "Frame range (e.g., 5-15)",

    # === frame command ===
    "cli.frame.doc": "Select stack frame",
    "cli.frame.session_help": "Session ID",

    # === locals-cmd command ===
    "cli.locals_cmd.doc": "Get local variables",
    "cli.locals_cmd.session_help": "Session ID",
    "cli.locals_cmd.thread_help": "Thread ID",
    "cli.locals_cmd.frame_help": "Frame number",

    # === exec command ===
    "cli.exec.doc": "Execute raw GDB command",
    "cli.exec.session_help": "Session ID",
    "cli.exec.safety_level_help": "Safety level (readonly/readwrite/full)",

    # === stop command ===
    "cli.stop.doc": "Stop session and safely exit GDB",
    "cli.stop.session_help": "Session ID",

    # === sessions command ===
    "cli.sessions.doc": "List all active sessions",

    # === status command ===
    "cli.status.doc": "Check session status",
    "cli.status.session_help": "Session ID",

    # === eval-element command ===
    "cli.eval_element.doc": "Access array/container element",
    "cli.eval_element.session_help": "Session ID",
    "cli.eval_element.index_help": "Element index",
    "cli.eval_element.max_depth_help": "Recursion depth limit",

    # === thread-apply command ===
    "cli.thread_apply.doc": "Batch thread operations",
    "cli.thread_apply.session_help": "Session ID",
    "cli.thread_apply.threads_help": "Thread ID list (e.g., 1,3,5)",
    "cli.thread_apply.all_help": "Apply to all threads",

    # === args command ===
    "cli.args.doc": "Get function arguments",
    "cli.args.session_help": "Session ID",
    "cli.args.thread_help": "Thread ID",
    "cli.args.frame_help": "Frame number",

    # === registers command ===
    "cli.registers.doc": "View register values",
    "cli.registers.session_help": "Session ID",
    "cli.registers.names_help": "Register names (comma-separated, e.g., rax,rbx,rip)",
    "cli.registers.thread_help": "Thread ID",
    "cli.registers.frame_help": "Frame number",

    # === memory command ===
    "cli.memory.doc": "Inspect memory content",
    "cli.memory.session_help": "Session ID",
    "cli.memory.size_help": "Bytes to read (default: 64, max: 4096)",
    "cli.memory.fmt_help": "Output format (hex/bytes/string)",

    # === ptype command ===
    "cli.ptype.doc": "View type information for expression",
    "cli.ptype.session_help": "Session ID",

    # === thread-switch command ===
    "cli.thread_switch.doc": "Switch current thread",
    "cli.thread_switch.session_help": "Session ID",

    # === up command ===
    "cli.up.doc": "Move toward caller in stack",
    "cli.up.session_help": "Session ID",

    # === down command ===
    "cli.down.doc": "Move toward callee in stack",
    "cli.down.session_help": "Session ID",

    # === sharedlibs command ===
    "cli.sharedlibs.doc": "View loaded shared libraries",
    "cli.sharedlibs.session_help": "Session ID",

    # === disasm command ===
    "cli.disasm.doc": "Disassemble",
    "cli.disasm.session_help": "Session ID",
    "cli.disasm.start_help": "Start address or function name (default: current PC)",
    "cli.disasm.count_help": "Instruction count (default: 20)",
    "cli.disasm.thread_help": "Thread ID",
    "cli.disasm.frame_help": "Frame number",

    # === env-check command ===
    "cli.env_check.doc": "Environment check: GDB version, ptrace permissions, Python version",

    # === Errors ===
    "errors.session_not_found": "Session not found: {session_id}",
    "errors.connection_error": "Connection error",
    "errors.variable_not_found.suggestion": "Check if variable name is correct, use 'info locals' to see variables in current scope",
    "errors.syntax_error.suggestion": "Check expression syntax, ensure C/C++ format is correct",
    "errors.invalid_thread.suggestion": "Use 'threads' command to see available thread list",
    "errors.invalid_frame.suggestion": "Use 'bt' command to see frame list",
    "errors.memory_access_failed.suggestion": "Target memory region is not accessible, variable may be optimized out",
    "errors.no_debug_info.suggestion": "Try loading debuginfo: 'dnf debuginfo-install' or check .debug file",
    "errors.process_not_found.suggestion": "Check if process exists: 'ps aux | grep <process_name>'",
    "errors.ptrace_denied.suggestion": "Run: 'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope'",
    "errors.command_blocked.suggestion": "Command blocked by safety policy, use --allow-write or --allow-call flag",
    "errors.command_timeout.suggestion": "Command timed out, try increasing --timeout or simplifying operation",
    "errors.load_timeout.suggestion": "Core file load timed out, file may be too large, try increasing timeout",
    "errors.socket_not_found.suggestion": "GDB session may have terminated, re-run 'gdb-cli load' or 'gdb-cli attach'",
    "errors.connection_refused.suggestion": "GDB RPC Server not responding, check if GDB process is running",

    # === Environment Check ===
    "env_check.gdb_not_found.error": "GDB not found in PATH",
    "env_check.gdb_not_found.suggestion": "Install GDB: 'brew install gdb' (macOS) or 'yum install gdb' (Linux)",
    "env_check.gdb_below_minimum.error": "GDB version {version} is below minimum {minimum}",
    "env_check.gdb_below_minimum.suggestion": "Upgrade GDB to version 9.0 or later",
    "env_check.gdb_version_warning": "GDB version {version} is supported but {recommended}+ is recommended",
    "env_check.gdb_recommended_suggestion": "Consider upgrading to GDB 15+ for best compatibility with rockylinux/el9",
    "env_check.ptrace_restricted.warning": "ptrace is restricted (scope=1). Can only attach to child processes.",
    "env_check.ptrace_heavily_restricted.error": "ptrace is heavily restricted (scope={scope})",
    "env_check.ptrace_heavily_restricted.suggestion": "Run: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope",
    "env_check.ptrace_sysctl_suggestion": "Or run: sysctl kernel.yama.ptrace_scope=0",
    "env_check.ptrace_scope_read_error.warning": "Cannot read ptrace_scope (permission denied)",
    "env_check.debuginfo_not_found.suggestion": "Binary appears to be stripped (no debug info)",
    "env_check.debuginfo_install_rhel": "RHEL/CentOS: dnf debuginfo-install {package}",
    "env_check.debuginfo_install_ubuntu": "Ubuntu/Debian: apt-get install {package}-dbgsym",
    "env_check.debuginfo_install_fedora": "Fedora: dnf install {package}-debuginfo",
    "env_check.debuginfo_separate_file": "Or use separate .debug file: add-symbol-file /path/to/{package}.debug",

    # === Runtime messages ===
    "errors.session_no_socket": "Session has no socket: {session_id}",
    "cli.load.session_reused_message": "Session already exists for this core file",
    "cli.load.failed": "Failed to start GDB",
    "cli.attach.session_reused_message": "Session already exists for this PID",
    "cli.attach.failed": "Failed to attach to process",
    "cli.target.invalid_format": "Invalid remote format: {remote}",
    "cli.target.session_reused_message": "Session already exists for this remote",
    "cli.target.failed": "Failed to connect to target",
    "cli.status.gdb_loading_message": "GDB process alive, not yet responding",
    "cli.status.session_dead": "Session dead",
    "cli.status.gdb_process_dead": "GDB process {pid} no longer exists",
    "cli.thread_apply.require_target": "Must specify --all or --threads",

    # === JSON output hints ===
    "hints.threads_pagination": "use 'threads --range START-END' for specific threads",
    "hints.bt_pagination": "use 'bt --range START-END' for specific frames",
    "hints.eval_large_array": "use 'eval-element' to access specific array indices",
}
