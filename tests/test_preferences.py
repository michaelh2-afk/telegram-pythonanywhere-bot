from unittest.mock import patch


def test_get_provider_default_when_unset():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.return_value = None
        from bot.preferences import get_provider
        assert get_provider(123) == "main"


def test_get_provider_returns_saved_main():
    with patch("bot.preferences.store") as mock_store, \
         patch("bot.preferences.HF_SPACE_ID", "fake/space"):
        mock_store.get.return_value = "main"
        from bot.preferences import get_provider
        assert get_provider(123) == "main"


def test_get_provider_returns_saved_hf_when_configured():
    with patch("bot.preferences.store") as mock_store, \
         patch("bot.preferences.HF_SPACE_ID", "fake/space"):
        mock_store.get.return_value = "hf"
        from bot.preferences import get_provider
        assert get_provider(123) == "hf"


def test_get_provider_falls_back_to_default_when_hf_not_configured():
    """Saved value is 'hf' but HF_SPACE_ID is empty — fall back."""
    with patch("bot.preferences.store") as mock_store, \
         patch("bot.preferences.HF_SPACE_ID", ""):
        mock_store.get.return_value = "hf"
        from bot.preferences import get_provider
        assert get_provider(123) == "main"


def test_get_provider_ignores_invalid_value():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.return_value = "garbage"
        from bot.preferences import get_provider
        assert get_provider(123) == "main"


def test_get_provider_redis_down_returns_default():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.side_effect = Exception("connection refused")
        from bot.preferences import get_provider
        assert get_provider(123) == "main"


def test_set_provider_saves_to_redis():
    with patch("bot.preferences.store") as mock_store:
        from bot.preferences import set_provider
        assert set_provider(123, "hf") is True
        mock_store.set.assert_called_once_with("provider:123", "hf")


def test_set_provider_rejects_invalid():
    with patch("bot.preferences.store") as mock_store:
        from bot.preferences import set_provider
        assert set_provider(123, "bogus") is False
        mock_store.set.assert_not_called()


def test_set_provider_redis_down_returns_false():
    with patch("bot.preferences.store") as mock_store:
        mock_store.set.side_effect = Exception("connection refused")
        from bot.preferences import set_provider
        assert set_provider(123, "main") is False


# ── learning level ──────────────────────────────────────────────────────────────


def test_get_level_default_when_unset():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.return_value = None
        from bot.preferences import get_level
        assert get_level(123) == "beginner"


def test_get_level_returns_saved():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.return_value = "intermediate"
        from bot.preferences import get_level
        assert get_level(123) == "intermediate"


def test_get_level_ignores_invalid_value():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.return_value = "expert"
        from bot.preferences import get_level
        assert get_level(123) == "beginner"


def test_get_level_store_down_returns_default():
    with patch("bot.preferences.store") as mock_store:
        mock_store.get.side_effect = Exception("connection refused")
        from bot.preferences import get_level
        assert get_level(123) == "beginner"


def test_get_level_store_none_returns_default():
    with patch("bot.preferences.store", None):
        from bot.preferences import get_level
        assert get_level(123) == "beginner"


def test_set_level_saves_with_no_ttl():
    with patch("bot.preferences.store") as mock_store:
        from bot.preferences import set_level
        assert set_level(123, "intermediate") is True
        mock_store.set.assert_called_once_with("level:123", "intermediate")


def test_set_level_rejects_invalid():
    with patch("bot.preferences.store") as mock_store:
        from bot.preferences import set_level
        assert set_level(123, "expert") is False
        mock_store.set.assert_not_called()


def test_set_level_store_none_returns_false():
    with patch("bot.preferences.store", None):
        from bot.preferences import set_level
        assert set_level(123, "beginner") is False


def test_set_level_store_down_returns_false():
    with patch("bot.preferences.store") as mock_store:
        mock_store.set.side_effect = Exception("connection refused")
        from bot.preferences import set_level
        assert set_level(123, "beginner") is False
