"""Tests for QQ Bot adapter (Official API v2)."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gateway.platforms.qq import QQAdapter, _coerce_list, check_qq_requirements
from gateway.config import PlatformConfig, Platform
from gateway.platforms.base import MessageType


def _make_config(**extra_kwargs):
    """Helper to create a QQ PlatformConfig with common defaults."""
    extra = {"app_id": "test-app-id", "client_secret": "test-secret"}
    extra.update(extra_kwargs)
    return PlatformConfig(enabled=True, extra=extra)


# ---------------------------------------------------------------------------
# Unit tests (no async, no gateway runner)
# ---------------------------------------------------------------------------

class TestQQRequirements:
    def test_check_returns_bool(self):
        result = check_qq_requirements()
        assert isinstance(result, bool)


class TestQQAdapterInit:
    def test_basic_attributes(self):
        cfg = _make_config()
        adapter = QQAdapter(cfg)
        assert adapter.name == "QQ"
        assert adapter.platform == Platform.QQ
        assert adapter._app_id == "test-app-id"
        assert adapter._client_secret == "test-secret"

    def test_env_var_fallback(self):
        with patch.dict(os.environ, {"QQ_APP_ID": "env-id", "QQ_CLIENT_SECRET": "env-sec"}):
            cfg = PlatformConfig(enabled=True, extra={})
            adapter = QQAdapter(cfg)
            assert adapter._app_id == "env-id"
            assert adapter._client_secret == "env-sec"

    def test_dm_policy_defaults_open(self):
        adapter = QQAdapter(_make_config())
        assert adapter._dm_policy == "open"

    def test_group_policy_defaults_open(self):
        adapter = QQAdapter(_make_config())
        assert adapter._group_policy == "open"

    def test_allowlist_parsing(self):
        adapter = QQAdapter(_make_config(allow_from=["u1", "u2"]))
        assert adapter._allow_from == ["u1", "u2"]

    def test_allowlist_from_comma_string(self):
        adapter = QQAdapter(_make_config(allow_from="u1, u2, u3"))
        assert adapter._allow_from == ["u1", "u2", "u3"]


class TestCoerceList:
    def test_none(self):
        assert _coerce_list(None) == []

    def test_string(self):
        assert _coerce_list("a, b, c") == ["a", "b", "c"]

    def test_list(self):
        assert _coerce_list(["a", "b"]) == ["a", "b"]

    def test_empty_string(self):
        assert _coerce_list("") == []


class TestIsVoiceContentType:
    def test_voice(self):
        assert QQAdapter._is_voice_content_type("voice", "") is True
        assert QQAdapter._is_voice_content_type("audio/mp3", "") is True
        assert QQAdapter._is_voice_content_type("audio/silk", "") is True
        assert QQAdapter._is_voice_content_type("", "recording.silk") is True
        assert QQAdapter._is_voice_content_type("", "voice.amr") is True

    def test_non_voice(self):
        assert QQAdapter._is_voice_content_type("image/jpeg", "photo.jpg") is False
        assert QQAdapter._is_voice_content_type("application/octet-stream", "doc.pdf") is False


class TestStripAtMention:
    def test_strips_at_mention(self):
        adapter = QQAdapter(_make_config())
        result = adapter._strip_at_mention("@bot hello world")
        assert result == "hello world"

    def test_no_mention(self):
        adapter = QQAdapter(_make_config())
        assert adapter._strip_at_mention("hello") == "hello"


class TestDmAllowed:
    def test_open_policy(self):
        adapter = QQAdapter(_make_config(dm_policy="open"))
        assert adapter._is_dm_allowed("anyone") is True

    def test_disabled_policy(self):
        adapter = QQAdapter(_make_config(dm_policy="disabled"))
        assert adapter._is_dm_allowed("anyone") is False

    def test_allowlist_match(self):
        adapter = QQAdapter(_make_config(dm_policy="allowlist", allow_from=["u1", "u2"]))
        assert adapter._is_dm_allowed("u1") is True
        assert adapter._is_dm_allowed("u3") is False


class TestGroupAllowed:
    def test_open_policy(self):
        adapter = QQAdapter(_make_config(group_policy="open"))
        assert adapter._is_group_allowed("g1", "anyone") is True

    def test_allowlist_match(self):
        adapter = QQAdapter(_make_config(group_policy="allowlist", group_allow_from=["g1"]))
        assert adapter._is_group_allowed("g1", "u1") is True
        assert adapter._is_group_allowed("g2", "u1") is False


class TestResolveSTTConfig:
    def test_no_config_returns_none(self):
        adapter = QQAdapter(_make_config())
        with patch.dict(os.environ, {}, clear=False):
            # Remove QQ_STT env vars if present
            for k in list(os.environ.keys()):
                if k.startswith("QQ_STT"):
                    del os.environ[k]
            assert adapter._resolve_stt_config() is None

    def test_env_var_config(self):
        adapter = QQAdapter(_make_config())
        with patch.dict(os.environ, {
            "QQ_STT_API_KEY": "test-key",
            "QQ_STT_BASE_URL": "https://example.com/v1",
            "QQ_STT_MODEL": "test-model",
        }):
            cfg = adapter._resolve_stt_config()
            assert cfg is not None
            assert cfg["api_key"] == "test-key"
            assert cfg["base_url"] == "https://example.com/v1"
            assert cfg["model"] == "test-model"

    def test_extra_config(self):
        adapter = QQAdapter(_make_config(stt={
            "baseUrl": "https://custom.example.com/api",
            "apiKey": "custom-key",
            "model": "custom-model",
        }))
        with patch.dict(os.environ, {}, clear=False):
            for k in list(os.environ.keys()):
                if k.startswith("QQ_STT"):
                    del os.environ[k]
            cfg = adapter._resolve_stt_config()
            assert cfg is not None
            assert cfg["base_url"] == "https://custom.example.com/api"
            assert cfg["api_key"] == "custom-key"
            assert cfg["model"] == "custom-model"


class TestDetectMessageType:
    def test_no_media(self):
        assert QQAdapter._detect_message_type([], []) == MessageType.TEXT

    def test_image(self):
        assert QQAdapter._detect_message_type(["/tmp/img.jpg"], ["image/jpeg"]) == MessageType.PHOTO

    def test_voice(self):
        assert QQAdapter._detect_message_type(["/tmp/voice.wav"], ["audio/wav"]) == MessageType.VOICE

    def test_video(self):
        assert QQAdapter._detect_message_type(["/tmp/vid.mp4"], ["video/mp4"]) == MessageType.VIDEO
