"""Tests for the command-menu registration helper (bot.clients.register_commands).

This runs at every PA worker boot and before local polling, so failures must
never bubble up and crash the worker. Also verifies the /model command is
menu-listed only when the HF provider is configured.
"""

from unittest.mock import patch

from bot.clients import MENU_COMMANDS


def test_menu_includes_core_commands():
    names = [name for name, _ in MENU_COMMANDS]
    for expected in ("start", "help", "teach", "level", "quiz"):
        assert expected in names


def test_menu_descriptions_start_with_emoji():
    # Every description leads with a non-ASCII (emoji) character so the menu
    # reads as an "emoji menu" — one emoji per line.
    for _, description in MENU_COMMANDS:
        assert description and ord(description[0]) > 127


def test_menu_command_names_are_valid():
    # Telegram command names must be lowercase latin/digits/underscore, 1-32 chars.
    for name, _ in MENU_COMMANDS:
        assert 1 <= len(name) <= 32
        assert name.replace("_", "").isalnum() and name.islower()


def test_register_commands_calls_set_my_commands():
    with (
        patch("bot.config.HF_SPACE_ID", ""),
        patch("bot.clients.bot") as mock_bot,
    ):
        from bot.clients import register_commands

        msg = register_commands()
        mock_bot.set_my_commands.assert_called_once()
        sent = mock_bot.set_my_commands.call_args[0][0]
        assert len(sent) == len(MENU_COMMANDS)
        assert "registered" in msg.lower()


def test_register_commands_adds_model_when_hf_configured():
    with (
        patch("bot.config.HF_SPACE_ID", "fake/space"),
        patch("bot.clients.bot") as mock_bot,
    ):
        from bot.clients import register_commands

        register_commands()
        sent = mock_bot.set_my_commands.call_args[0][0]
        assert len(sent) == len(MENU_COMMANDS) + 1


def test_register_commands_omits_model_without_hf():
    with (
        patch("bot.config.HF_SPACE_ID", ""),
        patch("bot.clients.bot") as mock_bot,
    ):
        from bot.clients import register_commands

        register_commands()
        sent = mock_bot.set_my_commands.call_args[0][0]
        assert len(sent) == len(MENU_COMMANDS)


def test_register_commands_does_not_raise_on_failure():
    """Failures are logged and swallowed after the retries are exhausted."""
    with (
        patch("bot.config.HF_SPACE_ID", ""),
        patch("bot.clients.bot") as mock_bot,
        patch("bot.clients.time.sleep") as mock_sleep,
    ):
        mock_bot.set_my_commands.side_effect = RuntimeError("Telegram down")
        from bot.clients import register_commands

        msg = register_commands()
        assert "fail" in msg.lower()
        assert mock_bot.set_my_commands.call_count == 3
        assert mock_sleep.call_count == 2


def test_register_commands_reports_telegram_false_return():
    with (
        patch("bot.config.HF_SPACE_ID", ""),
        patch("bot.clients.bot") as mock_bot,
    ):
        mock_bot.set_my_commands.return_value = False
        from bot.clients import register_commands

        msg = register_commands()
        assert "false" in msg.lower() or "fail" in msg.lower()
