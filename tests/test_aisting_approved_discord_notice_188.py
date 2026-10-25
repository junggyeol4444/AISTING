"""188절: 승인형 Discord 웹훅 전송 계약검사만 작성(실제 발신 없음).

실제 외부 네트워크 접속/계정 동의/방송/채팅 전송을 실행하지 않는다.
전체 기능 개발을 완료한 뒤 통합 검사에서 실행하도록 준비.
"""
import json
import unittest
from unittest.mock import Mock

from ai_broadcaster.approved_discord_notice import ApprovedDiscordNoticeSender


WEBHOOK = (
    "https://discord.com/api/webhooks/123456789012345678/"
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)


class TestApprovedDiscordNotice188(unittest.TestCase):
    def test_외부_게시_승인이_없으면_객체를_생성하지않음(self):
        with self.assertRaises(PermissionError):
            ApprovedDiscordNoticeSender(WEBHOOK)

    def test_공식_호스트외_개인정보_탈취_URL은_거절(self):
        for value in (
            WEBHOOK.replace("discord.com", "discord.com.evil.example"),
            WEBHOOK.replace("https://", "http://"),
            WEBHOOK.replace("discord.com", "localhost"),
            WEBHOOK + "?wait=true",
            WEBHOOK.replace("/api/webhooks/", "/api/users/"),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ApprovedDiscordNoticeSender(value, operator_approved=True)

    def test_명시적_게시승인과_실제_HTTP204_없이_성공이라고_하지않음(self):
        sender = ApprovedDiscordNoticeSender(WEBHOOK, operator_approved=True)
        with self.assertRaises(PermissionError):
            sender.send("운영자 작성 공지")
        response = Mock()
        response.status = 204
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        sender._opener = Mock(open=Mock(return_value=context))
        self.assertTrue(sender.send("운영자 작성 공지", operator_approved=True))
        request = sender._opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        payload = json.loads(request.data)
        self.assertEqual(payload["content"], "운영자 작성 공지")
        self.assertEqual(payload["allowed_mentions"], {"parse": []})

    def test_대량멘션과_잘못된_본문은_게시하지않음(self):
        sender = ApprovedDiscordNoticeSender(WEBHOOK, operator_approved=True)
        sender._opener = Mock()
        for value in ("", "@everyone 안녕하세요", "@here 공지", "X" * 2001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sender.send(value, operator_approved=True)
        sender._opener.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
