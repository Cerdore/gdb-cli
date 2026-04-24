"""Tests for safety module.

Tests safety.py: 命令白名单 + 安全过滤
- 所有 FORBIDDEN_COMMANDS 被拦截（包括 python）
- SafetyLevel.READONLY/READWRITE/FULL 行为正确
- SafetyFilter.check_command() 返回正确的分类和原因
"""

import unittest

from gdb_cli.safety import (
    FORBIDDEN_COMMANDS,
    SafetyFilter,
    SafetyLevel,
    classify_command,
    is_command_allowed,
)


class TestForbiddenCommands(unittest.TestCase):
    """Test that all forbidden commands are blocked."""

    def test_all_forbidden_commands_blocked(self):
        """Every FORBIDDEN_COMMAND is blocked at all safety levels."""
        for cmd in sorted(FORBIDDEN_COMMANDS):
            for level in ("readonly", "readwrite", "full"):
                with self.subTest(command=cmd, level=level):
                    self.assertFalse(
                        is_command_allowed(cmd, level),
                        f"Command '{cmd}' should be blocked at level '{level}'"
                    )

    def test_python_command_blocked(self):
        """python command must be in FORBIDDEN_COMMANDS (Issue #1 fix)."""
        self.assertIn("python", FORBIDDEN_COMMANDS)

    def test_python_variations_blocked(self):
        """python with arguments is also blocked."""
        sf = SafetyFilter(SafetyLevel.FULL)
        for cmd in ("python import os", "python os.system('id')", "python\nprint(1)"):
            allowed, reason = sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked, got reason={reason}")

    def test_shell_blocked(self):
        """shell command is blocked."""
        sf = SafetyFilter(SafetyLevel.FULL)
        allowed, _ = sf.filter_command("shell")
        self.assertFalse(allowed)

    def test_quit_blocked(self):
        """quit command is blocked."""
        sf = SafetyFilter(SafetyLevel.FULL)
        allowed, _ = sf.filter_command("quit")
        self.assertFalse(allowed)

    def test_attach_detach_blocked(self):
        """attach and detach are blocked."""
        sf = SafetyFilter(SafetyLevel.FULL)
        for cmd in ("attach 12345", "detach", "target extended-remote :3333"):
            allowed, _ = sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked")

    def test_signal_blocked(self):
        """signal is blocked at all levels."""
        for cmd in ("signal", "signal SIGCONT", "signal 9"):
            for level in SafetyLevel:
                sf = SafetyFilter(level)
                allowed, _ = sf.filter_command(cmd)
                self.assertFalse(
                    allowed, f"'{cmd}' should be blocked at {level}"
                )


class TestReadonlySafetyLevel(unittest.TestCase):
    """Test SafetyLevel.READONLY restrictions."""

    def setUp(self):
        self.sf = SafetyFilter(SafetyLevel.READONLY)

    def test_allows_read_commands(self):
        for cmd in ("bt", "backtrace", "info threads", "print foo",
                     "p x", "x", "ptype my_struct",
                     "frame", "up", "down", "disassemble main",
                     "info locals", "info args", "thread 1"):
            allowed, reason = self.sf.filter_command(cmd)
            self.assertTrue(allowed, f"'{cmd}' should be allowed, got: {reason}")

    def test_blocks_write_commands(self):
        for cmd in ("set variable x=1", "set var y=2", "assign z=3"):
            allowed, reason = self.sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked")

    def test_blocks_call_commands(self):
        for cmd in ("call foo()", "call malloc(100)"):
            allowed, reason = self.sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked")

    def test_allows_execution_control_with_confirmation(self):
        for cmd in ("continue", "c", "step", "s", "next", "n", "finish"):
            result = self.sf.check_command(cmd)
            self.assertTrue(result.allowed, f"'{cmd}' should be allowed")
            self.assertTrue(result.requires_confirmation, f"'{cmd}' should require confirmation")

    def test_blocks_unknown_commands(self):
        allowed, reason = self.sf.filter_command("some_unknown_command_xyz")
        self.assertFalse(allowed)


class TestReadwriteSafetyLevel(unittest.TestCase):
    """Test SafetyLevel.READWRITE restrictions."""

    def setUp(self):
        self.sf = SafetyFilter(SafetyLevel.READWRITE)

    def test_allows_read_commands(self):
        for cmd in ("bt", "info threads", "print foo", "disassemble main"):
            allowed, _ = self.sf.filter_command(cmd)
            self.assertTrue(allowed)

    def test_allows_write_commands(self):
        for cmd in ("set variable x=1", "set var y=2", "assign z=3"):
            allowed, reason = self.sf.filter_command(cmd)
            self.assertTrue(allowed, f"'{cmd}' should be allowed, got: {reason}")

    def test_blocks_call_commands(self):
        for cmd in ("call foo()", "call danger()"):
            allowed, _ = self.sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked")


class TestFullSafetyLevel(unittest.TestCase):
    """Test SafetyLevel.FULL restrictions."""

    def setUp(self):
        self.sf = SafetyFilter(SafetyLevel.FULL)

    def test_allows_read_write_call(self):
        for cmd in ("bt", "set variable x=1", "call foo()"):
            allowed, reason = self.sf.filter_command(cmd)
            self.assertTrue(allowed, f"'{cmd}' should be allowed, got: {reason}")

    def test_call_requires_confirmation(self):
        result = self.sf.check_command("call foo()")
        self.assertTrue(result.allowed)
        self.assertTrue(result.requires_confirmation)

    def test_still_blocks_forbidden(self):
        for cmd in ("quit", "kill", "shell", "python-interactive", "signal"):
            allowed, _ = self.sf.filter_command(cmd)
            self.assertFalse(allowed, f"'{cmd}' should be blocked even at FULL")

    def test_unknown_commands_allowed_at_full(self):
        allowed, _ = self.sf.filter_command("my_custom_alias_command")
        self.assertTrue(allowed)


class TestCommandParsing(unittest.TestCase):
    """Test command parsing and normalization."""

    def test_extract_command_verb(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        self.assertEqual(sf._extract_command_verb("print foo"), "print")
        self.assertEqual(sf._extract_command_verb("set variable x=1"), "set")
        self.assertEqual(sf._extract_command_verb("  bt  "), "bt")

    def test_empty_command(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        result = sf.check_command("")
        self.assertFalse(result.allowed)  # Empty string is not a valid command

    def test_whitespace_command(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        result = sf.check_command("   ")
        self.assertFalse(result.allowed)  # Whitespace-only is not a valid command


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""

    def test_is_command_allowed_readonly(self):
        self.assertTrue(is_command_allowed("bt", "readonly"))
        self.assertFalse(is_command_allowed("set variable x=1", "readonly"))
        self.assertFalse(is_command_allowed("signal 9", "readonly"))

    def test_is_command_allowed_invalid_level(self):
        # Invalid level falls back to READONLY
        self.assertTrue(is_command_allowed("bt", "bogus_level"))
        self.assertFalse(is_command_allowed("set variable x=1", "bogus_level"))

    def test_classify_command(self):
        self.assertEqual(classify_command("bt"), "readonly")
        self.assertEqual(classify_command("set variable x=1"), "write")
        self.assertEqual(classify_command("call foo()"), "call")
        self.assertEqual(classify_command("signal 9"), "forbidden")
        self.assertEqual(classify_command("continue"), "execution")


class TestSafetyFilterInterface(unittest.TestCase):
    """Test SafetyFilter class interface."""

    def test_filter_init(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        self.assertEqual(sf.level, SafetyLevel.READONLY)

    def test_filter_check_returns_result(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        result = sf.check_command("bt")
        self.assertTrue(result.allowed)
        self.assertEqual(result.category, "readonly")
        self.assertFalse(result.requires_confirmation)

    def test_filter_check_returns_reason_when_blocked(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        result = sf.check_command("set variable x=1")
        self.assertFalse(result.allowed)
        self.assertIsNotNone(result.reason)
        self.assertIn("requires", result.reason.lower())

    def test_filter_command_returns_tuple(self):
        sf = SafetyFilter(SafetyLevel.READONLY)
        allowed, reason = sf.filter_command("bt")
        self.assertTrue(allowed)
        self.assertIsNone(reason)

        allowed, reason = sf.filter_command("signal 9")
        self.assertFalse(allowed)
        self.assertIsNotNone(reason)


class TestSafetyEdgeCases(unittest.TestCase):
    """Edge case tests for safety module."""

    def test_case_insensitive(self):
        """GDB commands are case-insensitive."""
        sf = SafetyFilter(SafetyLevel.READONLY)
        for cmd in ("BT", "Bt", "Backtrace"):
            allowed, _ = sf.filter_command(cmd)
            self.assertTrue(allowed, f"'{cmd}' should be allowed")

    def test_command_with_special_chars(self):
        sf = SafetyFilter(SafetyLevel.FULL)
        allowed, _ = sf.filter_command('print "hello world"')
        self.assertTrue(allowed)

    def test_readonly_commands_list_content(self):
        from gdb_cli.safety import READONLY_COMMANDS
        expected = {"bt", "backtrace", "info", "thread", "threads",
                     "print", "p", "x", "ptype", "whatis",
                     "frame", "up", "down", "select-frame",
                     "list", "disassemble", "source",
                     "show", "help", "pwd", "directory"}
        self.assertEqual(READONLY_COMMANDS, expected)


if __name__ == "__main__":
    unittest.main()
