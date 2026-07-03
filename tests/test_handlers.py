from unittest.mock import patch, MagicMock


def make_message(text="hello", user_id=123, chat_id=456, chat_type="private"):
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = user_id
    msg.chat.id = chat_id
    msg.chat.type = chat_type
    msg.reply_to_message = None
    return msg


HANDLER_PATCHES = {
    "bot.handlers.should_respond": True,
    "bot.handlers.is_rate_limited": False,
    "bot.handlers.BOT_INFO": MagicMock(id=42, username="testbot"),
}


def test_handle_message_calls_ask_ai():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", return_value="AI reply") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message(text="hello")
        handle_message(msg)
        mock_ask.assert_called_once_with(123, "hello")
        mock_send.assert_called_once_with(msg, "AI reply")


def test_handle_message_skips_when_not_responding():
    with (
        patch("bot.handlers.should_respond", return_value=False),
        patch("bot.handlers.ask_ai") as mock_ask,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        mock_ask.assert_not_called()


def test_handle_message_rate_limited():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=True),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        mock_ask.assert_not_called()
        mock_bot.send_message.assert_called_once()
        assert "daily limit" in mock_bot.send_message.call_args[0][1]


def test_handle_message_sends_generic_error():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", side_effect=Exception("API key invalid")),
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        error_msg = mock_bot.send_message.call_args[0][1]
        assert "Something went wrong" in error_msg
        assert "API key" not in error_msg


def test_handle_message_none_text_skipped():
    """Stickers/photos/edits arriving with text=None must NOT call ask_ai
    (would burn rate limit and AI quota for no reason)."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message()
        msg.text = None
        handle_message(msg)
        mock_ask.assert_not_called()
        mock_send.assert_not_called()


def test_handle_message_mention_only_skipped():
    """In a group, '@testbot' alone strips to empty — don't call ask_ai."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.send_reply"),
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message(text="@testbot")
        handle_message(msg)
        mock_ask.assert_not_called()


# ── /about ────────────────────────────────────────────────────────────────────


def test_cmd_about_calls_ai_and_sends_reply():
    """cmd_about should call generate() with the system prompt and relay the reply."""
    with (
        patch("bot.handlers.generate", return_value="I'm Ferris!") as mock_gen,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_about

        msg = make_message()
        cmd_about(msg)
        mock_gen.assert_called_once()
        messages_arg = mock_gen.call_args[0][1]
        assert any(m["role"] == "system" for m in messages_arg)
        mock_send.assert_called_once_with(msg, "I'm Ferris!")


def test_cmd_about_fallback_on_ai_error():
    """On AI failure, /about should send a static fallback rather than raise."""
    with (
        patch("bot.handlers.generate", side_effect=Exception("timeout")),
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot") as mock_bot,
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_about

        cmd_about(make_message())
        assert mock_bot.send_message.called
        fallback = mock_bot.send_message.call_args[0][1]
        assert "Ferris" in fallback


# ── /teach ────────────────────────────────────────────────────────────────────


def test_cmd_teach_calls_ai_with_language():
    """cmd_teach should pass the requested language into the AI prompt and relay the reply."""
    with (
        patch("bot.handlers.generate", return_value="Here's your Python lesson!") as mock_gen,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_teach

        msg = make_message(text="/teach python")
        cmd_teach(msg)
        mock_gen.assert_called_once()
        messages_arg = mock_gen.call_args[0][1]
        user_prompt = next(m["content"] for m in messages_arg if m["role"] == "user")
        assert "python" in user_prompt
        mock_send.assert_called_once_with(msg, "Here's your Python lesson!")


def test_cmd_teach_no_arg_shows_usage():
    """/teach with no language should show usage and NOT call the AI."""
    with (
        patch("bot.handlers.generate") as mock_gen,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_teach

        cmd_teach(make_message(text="/teach"))
        mock_gen.assert_not_called()
        sent = mock_bot.send_message.call_args[0][1]
        assert "Usage" in sent and "/teach" in sent


def test_cmd_teach_fallback_on_ai_error():
    """On AI failure, /teach should send a fallback naming the language rather than raise."""
    with (
        patch("bot.handlers.generate", side_effect=Exception("timeout")),
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot") as mock_bot,
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_teach

        cmd_teach(make_message(text="/teach rust"))
        assert mock_bot.send_message.called
        fallback = mock_bot.send_message.call_args[0][1]
        assert "rust" in fallback


def test_cmd_teach_uses_saved_level_in_prompt():
    """cmd_teach should feed the user's saved level into the AI prompt."""
    with (
        patch("bot.handlers.get_level", return_value="intermediate"),
        patch("bot.handlers.generate", return_value="lesson") as mock_gen,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.send_reply"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_teach

        cmd_teach(make_message(text="/teach python"))
        user_prompt = next(
            m["content"] for m in mock_gen.call_args[0][1] if m["role"] == "user"
        )
        assert "intermediate" in user_prompt


# ── /help ─────────────────────────────────────────────────────────────────────


def test_cmd_help_sends_static_command_list():
    """cmd_help sends the static command list directly, without calling the AI."""
    with (
        patch("bot.handlers.generate") as mock_gen,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_help

        msg = make_message(text="/help")
        cmd_help(msg)
        mock_gen.assert_not_called()
        assert mock_bot.send_message.called
        sent = mock_bot.send_message.call_args[0][1]
        assert "/help" in sent and "/joke" in sent and "/teach" in sent
        assert "/level" in sent and "/quiz" in sent


def test_cmd_help_fallback_on_ai_error():
    """On AI failure, /help should fall back to sending the plain command list."""
    with (
        patch("bot.handlers.generate", side_effect=Exception("timeout")),
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot") as mock_bot,
    ):
        mock_bot.message_handlers = [
            {"filters": {"commands": ["start"]}, "function": MagicMock(__doc__="welcome message")},
        ]
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_help

        cmd_help(make_message(text="/help"))
        assert mock_bot.send_message.called
        sent = mock_bot.send_message.call_args[0][1]
        assert "/start" in sent


# ── /sha ─────────────────────────────────────────────────────────────────────


def test_cmd_sha_reports_live_commit_sha():
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.COMMIT_SHA", "abc1234"),
    ):
        from bot.handlers import cmd_sha

        cmd_sha(make_message())
        mock_bot.send_message.assert_called_once_with(456, "Live SHA: abc1234")


def test_cmd_sha_reports_unknown_when_git_sha_unavailable():
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.COMMIT_SHA", ""),
    ):
        from bot.handlers import cmd_sha

        cmd_sha(make_message())
        mock_bot.send_message.assert_called_once_with(456, "Live SHA: unknown")


# ── /level ─────────────────────────────────────────────────────────────────────


def test_cmd_level_no_arg_shows_current():
    with (
        patch("bot.handlers.get_level", return_value="beginner"),
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_level

        cmd_level(make_message(text="/level"))
        sent = mock_bot.send_message.call_args[0][1]
        assert "beginner" in sent
        assert "/level intermediate" in sent


def test_cmd_level_sets_valid_level():
    with (
        patch("bot.handlers.set_level", return_value=True) as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_level

        cmd_level(make_message(text="/level intermediate"))
        mock_set.assert_called_once_with(123, "intermediate")
        assert "intermediate" in mock_bot.send_message.call_args[0][1]


def test_cmd_level_invalid_choice():
    with (
        patch("bot.handlers.set_level") as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_level

        cmd_level(make_message(text="/level expert"))
        mock_set.assert_not_called()
        assert "Invalid" in mock_bot.send_message.call_args[0][1]


def test_cmd_level_save_failure_reports_error():
    with (
        patch("bot.handlers.set_level", return_value=False),
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_level

        cmd_level(make_message(text="/level beginner"))
        assert "Could not save" in mock_bot.send_message.call_args[0][1]


# ── /quiz, /explain, /example, /roadmap ─────────────────────────────────────────


def _run_ai_arg_command(cmd, text):
    """Call an AI-backed command with generate/keep_typing/send_reply patched;
    return the user-role prompt string that was sent to the AI."""
    with (
        patch("bot.handlers.generate", return_value="ok") as mock_gen,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        cmd(make_message(text=text))
        mock_gen.assert_called_once()
        mock_send.assert_called_once()
        return next(m["content"] for m in mock_gen.call_args[0][1] if m["role"] == "user")


def _no_arg_usage_message(cmd, text):
    """Call an AI-backed command with no argument; assert it skips the AI and return the reply."""
    with (
        patch("bot.handlers.generate") as mock_gen,
        patch("bot.handlers.bot") as mock_bot,
    ):
        cmd(make_message(text=text))
        mock_gen.assert_not_called()
        return mock_bot.send_message.call_args[0][1]


def test_cmd_quiz_calls_ai_with_language():
    from bot.handlers import cmd_quiz
    assert "python" in _run_ai_arg_command(cmd_quiz, "/quiz python")


def test_cmd_quiz_no_arg_shows_usage():
    from bot.handlers import cmd_quiz
    assert "Usage" in _no_arg_usage_message(cmd_quiz, "/quiz")


def test_cmd_explain_calls_ai_with_term():
    from bot.handlers import cmd_explain
    assert "recursion" in _run_ai_arg_command(cmd_explain, "/explain recursion")


def test_cmd_explain_no_arg_shows_usage():
    from bot.handlers import cmd_explain
    assert "Usage" in _no_arg_usage_message(cmd_explain, "/explain")


def test_cmd_example_calls_ai_with_topic():
    from bot.handlers import cmd_example
    assert "python loops" in _run_ai_arg_command(cmd_example, "/example python loops")


def test_cmd_example_no_arg_shows_usage():
    from bot.handlers import cmd_example
    assert "Usage" in _no_arg_usage_message(cmd_example, "/example")


def test_cmd_roadmap_calls_ai_with_language():
    from bot.handlers import cmd_roadmap
    assert "python" in _run_ai_arg_command(cmd_roadmap, "/roadmap python")


def test_cmd_roadmap_no_arg_shows_usage():
    from bot.handlers import cmd_roadmap
    assert "Usage" in _no_arg_usage_message(cmd_roadmap, "/roadmap")


# ── /model command ────────────────────────────────────────────────────────────


def _import_cmd_model_with_hf_enabled():
    """Re-import handlers module with HF_SPACE_ID set so cmd_model exists."""
    import importlib
    import bot.config
    import bot.handlers

    original = bot.config.HF_SPACE_ID
    bot.config.HF_SPACE_ID = "fake/space"
    # Also patch the import in handlers module (already imported via `from ... import HF_SPACE_ID`)
    bot.handlers.HF_SPACE_ID = "fake/space"
    importlib.reload(bot.handlers)
    cmd_model = getattr(bot.handlers, "cmd_model", None)
    # Restore
    bot.config.HF_SPACE_ID = original
    bot.handlers.HF_SPACE_ID = original
    return cmd_model


def test_cmd_model_no_args_shows_current():
    cmd_model = _import_cmd_model_with_hf_enabled()
    assert cmd_model is not None
    with (
        patch("bot.handlers.get_provider", return_value="main"),
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model")
        cmd_model(msg)
        sent = mock_bot.send_message.call_args[0][1]
        assert "Current provider: main" in sent
        assert "/model main" in sent
        assert "/model hf" in sent


def test_cmd_model_switch_to_hf():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=True) as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model hf")
        cmd_model(msg)
        mock_set.assert_called_once_with(123, "hf")
        sent = mock_bot.send_message.call_args[0][1]
        assert "hf" in sent
        assert "Armenian" in sent


def test_cmd_model_switch_to_main():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=True) as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model main")
        cmd_model(msg)
        mock_set.assert_called_once_with(123, "main")
        sent = mock_bot.send_message.call_args[0][1]
        assert "Main" in sent


def test_cmd_model_invalid_choice():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider") as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model bogus")
        cmd_model(msg)
        mock_set.assert_not_called()
        assert "Invalid" in mock_bot.send_message.call_args[0][1]


def test_cmd_model_redis_error_reports_failure():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=False),
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model hf")
        cmd_model(msg)
        assert "Could not save" in mock_bot.send_message.call_args[0][1]


def test_cmd_model_not_registered_without_hf_space_id():
    """When HF_SPACE_ID is empty, cmd_model should not exist."""
    import importlib
    import bot.config
    import bot.handlers

    bot.config.HF_SPACE_ID = ""
    bot.handlers.HF_SPACE_ID = ""
    # reload() doesn't delete existing attributes, so clear it first
    if hasattr(bot.handlers, "cmd_model"):
        delattr(bot.handlers, "cmd_model")
    importlib.reload(bot.handlers)
    assert not hasattr(bot.handlers, "cmd_model")


def test_handle_message_uses_keep_typing():
    """handle_message should wrap ask_ai in the keep_typing context."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", return_value="reply"),
        patch("bot.handlers.send_reply"),
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import handle_message

        msg = make_message()
        handle_message(msg)
        mock_keep.assert_called_once_with(456)
