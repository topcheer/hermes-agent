from gateway.platforms.telegram import TelegramAdapter
from gateway.platforms.discord import DiscordAdapter
from gateway.platforms.whatsapp import WhatsAppAdapter
from gateway.platforms.slack import SlackAdapter
from gateway.platforms.signal import SignalAdapter
from gateway.platforms.mattermost import MattermostAdapter
from gateway.platforms.matrix import MatrixAdapter
from gateway.platforms.api_server import APIServerAdapter
from gateway.platforms.homeassistant import HomeAssistantAdapter
from gateway.platforms.email import EmailAdapter
from gateway.platforms.sms import SmsAdapter
from gateway.platforms.webhook import WebhookAdapter
from gateway.platforms.dingtalk import DingTalkAdapter
from gateway.platforms.feishu import FeishuAdapter
from gateway.platforms.wecom import WeComAdapter
from gateway.platforms.bluebubbles import BlueBubblesAdapter
from gateway.platforms.qq import QQAdapter

__all__ = [
    "TelegramAdapter",
    "DiscordAdapter",
    "WhatsAppAdapter",
    "SlackAdapter",
    "SignalAdapter",
    "MattermostAdapter",
    "MatrixAdapter",
    "APIServerAdapter",
    "HomeAssistantAdapter",
    "EmailAdapter",
    "SmsAdapter",
    "WebhookAdapter",
    "DingTalkAdapter",
    "FeishuAdapter",
    "WeComAdapter",
    "BlueBubblesAdapter",
    "QQAdapter",
]
