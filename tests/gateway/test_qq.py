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


# ── Additional tests for WebSocket keep-alive and message processing ──


class TestQQCloseError:
    """QQCloseError carries close code and reason for reconnect logic."""

    def test_attributes(self):
        from gateway.platforms.qq import QQCloseError
        err = QQCloseError(4004, "not authenticated")
        assert err.code == 4004
        assert err.reason == "not authenticated"
        assert "4004" in str(err)
        assert "not authenticated" in str(err)

    def test_code_none(self):
        from gateway.platforms.qq import QQCloseError
        err = QQCloseError(None, "")
        assert err.code is None
        assert err.reason == ""

    def test_code_string_conversion(self):
        from gateway.platforms.qq import QQCloseError
        err = QQCloseError("4008", "rate limited")
        assert err.code == 4008


class TestDispatchPayload:
    """_dispatch_payload routes op codes correctly."""

    def test_unknown_op_ignored(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        adapter._dispatch_payload({"op": 99, "d": None, "s": None, "t": None})

    def test_op10_updates_heartbeat_interval(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        assert adapter._heartbeat_interval == 30.0
        adapter._dispatch_payload({
            "op": 10,
            "d": {"heartbeat_interval": 50000},
        })
        assert adapter._heartbeat_interval == 40.0  # 50000 / 1000 * 0.8

    def test_op11_heartbeat_ack_no_error(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        adapter._dispatch_payload({"op": 11})

    def test_seq_tracking(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        adapter._dispatch_payload({"op": 0, "s": 42, "t": "READY", "d": {}})
        assert adapter._last_seq == 42
        adapter._dispatch_payload({"op": 0, "s": 30, "t": "READY", "d": {}})
        assert adapter._last_seq == 42
        adapter._dispatch_payload({"op": 0, "s": 50, "t": "READY", "d": {}})
        assert adapter._last_seq == 50


class TestReadyHandling:
    """READY dispatch stores session_id."""

    def test_ready_stores_session(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        adapter._dispatch_payload({
            "op": 0,
            "s": 1,
            "t": "READY",
            "d": {"session_id": "test-session-123", "user": {"id": "bot-1"}},
        })
        assert adapter._session_id == "test-session-123"

    def test_resumed_preserves_session(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        adapter._session_id = "existing"
        adapter._dispatch_payload({"op": 0, "s": 1, "t": "RESUMED", "d": {}})
        assert adapter._session_id == "existing"


class TestParseJson:
    """_parse_json handles malformed JSON gracefully."""

    def test_valid_json(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        result = adapter._parse_json('{"op": 10}')
        assert result == {"op": 10}

    def test_invalid_json_returns_none(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        result = adapter._parse_json("not json")
        assert result is None

    def test_none_input_returns_none(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        assert adapter._parse_json(None) is None


class TestBuildTextBody:
    """_build_text_body produces correct message body."""

    def test_plain_text(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        result = adapter._build_text_body("hello")
        assert "markdown" in result
        assert result["markdown"]["content"] == "hello"

    def test_truncation(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        long_text = "x" * 5000
        result = adapter._build_text_body(long_text)
        text = result["markdown"]["content"]
        assert len(text) <= 4000

    def test_empty_string(self):
        from gateway.platforms.qq import QQAdapter
        adapter = QQAdapter(_make_config())
        result = adapter._build_text_body("")
        assert result["markdown"]["content"] == ""
