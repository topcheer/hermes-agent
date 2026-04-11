---
sidebar_position: 16
title: "QQ Bot"
description: "Connect Hermes Agent to QQ via the Official QQ Bot API"
---

# QQ Bot

Connect Hermes to [QQ](https://q.qq.com/) using the Official QQ Bot API v2. The adapter connects via the QQ Bot WebSocket Gateway for real-time bidirectional communication — no public endpoint or webhook is required.

:::info
This adapter uses the **Official QQ Bot API v2** (`api.sgroup.qq.com`). Environment variables and configuration follow the official API conventions (App ID + App Secret).
:::

## Prerequisites

- A QQ Bot created at [https://q.qq.com/](https://q.qq.com/)
- App ID and App Secret from the QQ Bot management console
- Python package: `aiohttp`

Install the required dependency:

```bash
pip install aiohttp
```

For voice message transcription (SILK format decoding):

```bash
pip install pilk
```

Or install `ffmpeg` for broader audio format support:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Setup

### 1. Create a QQ Bot

1. Go to [https://q.qq.com/](https://q.qq.com/) and scan the QR code to log in
2. Create a new bot and copy the **App ID** and **App Secret**
3. Enable the required permissions:
   - C2C message (private/direct messages)
   - Group @-message (group chat)
   - Media upload (for sending images, files, voice)

### 2. Interactive Setup

Run the interactive setup wizard:

```bash
hermes setup gateway
```

Select **QQ** from the platform list and enter your credentials when prompted:

- **App ID** — from the QQ Bot management console
- **App Secret** — from the QQ Bot management console
- **Allowed user IDs** — comma-separated QQ user openIDs (leave empty to deny everyone)
- **STT provider** — choose QQ built-in ASR (free, default) or a custom STT provider

### 3. Environment Variables

Alternatively, set environment variables directly:

```bash
# Required
export QQ_APP_ID="your-app-id"
export QQ_CLIENT_SECRET="your-app-secret"

# Optional: restrict access
export QQ_ALLOWED_USERS="user_openid_1,user_openid_2"
export QQ_GROUP_ALLOWED_USERS="group_openid_1"

# Optional: home channel for cron/notifications
export QQ_HOME_CHANNEL="user_openid_for_cron"

# Optional: custom STT provider (leave empty to use QQ's built-in ASR)
export QQ_STT_API_KEY="your-stt-api-key"
export QQ_STT_BASE_URL="https://open.bigmodel.cn/api/coding/paas/v4"
export QQ_STT_MODEL="glm-asr"
```

### 4. Start the Gateway

```bash
hermes gateway run
```

## Voice Messages

The adapter supports voice message transcription with a 3-tier fallback:

1. **QQ's built-in ASR** (`asr_refer_text`) — Tencent's own speech recognition, free, zero API calls. This is used automatically whenever QQ provides it.
2. **Pre-converted WAV** (`voice_wav_url`) — QQ provides a pre-transcoded WAV download URL. The adapter downloads this directly, avoiding SILK decoding failures.
3. **Custom STT provider** — If configured, used as a fallback. Supports any OpenAI-compatible STT API (e.g. Zhipu GLM-ASR, OpenAI Whisper).

### Custom STT Configuration

Via `config.yaml`:

```yaml
platforms:
  qq:
    enabled: true
    extra:
      app_id: "your-app-id"
      client_secret: "your-app-secret"
      stt:
        provider: "zai"         # zai, openai, glm
        baseUrl: "https://open.bigmodel.cn/api/coding/paas/v4"
        apiKey: "your-stt-api-key"
        model: "glm-asr"
```

Or via environment variables (see above).

## Features

| Feature | Status |
|---------|--------|
| Private messages (C2C) | ✅ |
| Group @-messages | ✅ |
| Guild/channel messages | ✅ |
| Guild DM | ✅ |
| Text messages | ✅ |
| Markdown replies | ✅ (when `markdown_support: true`) |
| Image send/receive | ✅ |
| Voice transcription | ✅ (QQ built-in ASR + custom STT) |
| Voice replies (TTS) | ✅ |
| File send/receive | ✅ |
| Video send | ✅ |
| Typing indicator | ✅ |
| Message deduplication | ✅ |
| WebSocket reconnection | ✅ (exponential backoff) |

## Configuration Options

All options go under `platforms.qq.extra` in `config.yaml`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `app_id` | string | — | QQ Bot App ID |
| `client_secret` | string | — | QQ Bot App Secret |
| `dm_policy` | string | `open` | DM access: `open`, `allowlist`, `pairing`, `disabled` |
| `group_policy` | string | `open` | Group access: `open`, `allowlist`, `disabled` |
| `allow_from` | list/string | — | Allowed user openIDs for DM |
| `group_allow_from` | list/string | — | Allowed group openIDs |
| `markdown_support` | bool | `true` | Enable markdown formatting in replies |
| `stt.provider` | string | — | STT provider: `zai`, `openai`, `glm` |
| `stt.baseUrl` | string | — | STT API base URL |
| `stt.apiKey` | string | — | STT API key |
| `stt.model` | string | — | STT model name |

## Troubleshooting

### Connection fails

- Verify your App ID and App Secret are correct at [q.qq.com](https://q.qq.com/)
- Check that the required permissions (C2C message, Group @-message) are enabled
- Ensure `aiohttp` is installed: `pip install aiohttp`

### Voice messages not transcribed

- QQ's built-in ASR is used automatically — if it returns empty text, check if the voice message was too short or garbled
- For custom STT: verify `QQ_STT_API_KEY` is set and the provider is accessible
- For SILK decoding: install `pilk` (`pip install pilk`) or `ffmpeg`

### Bot doesn't respond to @-mentions in groups

- Ensure Group @-message permission is enabled in the QQ Bot console
- Check `group_policy` — if set to `allowlist`, the group openID must be in `group_allow_from`
- Group openIDs differ from user openIDs — use `QQ_GROUP_ALLOWED_USERS` to restrict by group
