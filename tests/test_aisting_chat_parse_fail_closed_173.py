"""173회차: 실제 채팅 수신 프레임·페이지 손상 시 무음 폐기 방지 계약검사.

이 검사는 가상 입력만 사용한다. 실제 플랫폼·시청자·권리 있는
음성 모델·Windows EXE·OBS·24시간 실방송을 검증하지 않는다.
"""
import json
import unittest

from ai_broadcaster.multiplatform_readonly import (
    parse_chzzk_frame,
    parse_soop_frame,
    parse_youtube_page,
    YouTubeChatResumeState,
)


def 치지직(항목):
    return json.dumps({"cmd": 93101, "bdy": 항목}, ensure_ascii=False)


def 유튜브(항목):
    return {"items": 항목}


def 유튜브채팅(내용="가상 채팅", 종류="textMessageEvent"):
    return {
        "id": "가상-이벤트-1",
        "snippet": {"type": 종류, "displayMessage": 내용},
        "authorDetails": {"displayName": "가상 시청자"},
    }


class 손상프레임미확정검사(unittest.TestCase):
    def test_치지직_정상채팅_두건_모두_유지(self):
        result = parse_chzzk_frame(
            치지직([{"msg": "첫째", "uid": "가상1"},
                    {"msg": "둘째", "uid": "가상2"}]), "가상방")
        self.assertEqual([x.text for x in result], ["첫째", "둘째"])

    def test_치지직_정상항목뒤_손상항목은_프레임전체_실패(self):
        with self.assertRaisesRegex(ValueError, "치지직 채팅 항목"):
            parse_chzzk_frame(치지직([{"msg": "첫째"}, 3]), "가상방")

    def test_치지직_본문이_문자열이_아니면_실패(self):
        with self.assertRaisesRegex(ValueError, "치지직 채팅 본문"):
            parse_chzzk_frame(치지직([{"msg": "첫째"}, {"msg": None}]), "가상방")

    def test_치지직_빈문자열_기존처리_유지(self):
        self.assertEqual(parse_chzzk_frame(치지직([{"msg": ""}]), "가상방"), [])

    def test_치지직_비채팅명령_기존처리_유지(self):
        self.assertEqual(parse_chzzk_frame(json.dumps({"cmd": 0}), "가상방"), [])

    def test_SOOP_정상0005_두건_순서_유지(self):
        packet = ("\x1b\t000500000000\x0c첫째\x0c가상1\x0c"
                  "\x1b\t000500000000\x0c둘째\x0c가상2\x0c")
        self.assertEqual([x.text for x in parse_soop_frame(packet, "가상방")],
                         ["첫째", "둘째"])

    def test_SOOP_정상뒤_잘린0005는_프레임전체_실패(self):
        packet = "\x1b\t000500000000\x0c첫째\x0c가상\x0c\x1b\t0005"
        with self.assertRaisesRegex(ValueError, "SOOP 채팅 프레임 길이"):
            parse_soop_frame(packet, "가상방")

    def test_SOOP_채팅필드_부족하면_실패(self):
        with self.assertRaisesRegex(ValueError, "SOOP 채팅 필드"):
            parse_soop_frame("\x1b\t000500000000\x0c본문", "가상방")

    def test_SOOP_비채팅_제어명령은_기존대로_무시(self):
        self.assertEqual(parse_soop_frame("\x1b\t000100000000\x0c", "가상방"), [])

    def test_유튜브_정상채팅_두건_유지(self):
        first = 유튜브채팅("첫째")
        second = 유튜브채팅("둘째")
        second["id"] = "가상-이벤트-2"
        result = parse_youtube_page(유튜브([first, second]), "가상방")
        self.assertEqual([x.text for x in result], ["첫째", "둘째"])

    def test_유튜브_정상뒤_손상항목_전체페이지_실패(self):
        with self.assertRaisesRegex(ValueError, "유튜브 채팅 페이지 항목"):
            parse_youtube_page(유튜브([유튜브채팅(), None]), "가상방")

    def test_유튜브_본문정보가_없으면_페이지_실패(self):
        with self.assertRaisesRegex(ValueError, "유튜브 채팅 페이지 내용"):
            parse_youtube_page(유튜브([{"id": "가상"}]), "가상방")

    def test_유튜브_지원하는채팅의_본문누락은_페이지_실패(self):
        bad = 유튜브채팅()
        del bad["snippet"]["displayMessage"]
        with self.assertRaisesRegex(ValueError, "유튜브 채팅 본문"):
            parse_youtube_page(유튜브([bad]), "가상방")

    def test_유튜브_작성자정보_형식오류는_페이지_실패(self):
        bad = 유튜브채팅()
        bad["authorDetails"] = ["손상"]
        with self.assertRaisesRegex(ValueError, "유튜브 채팅 작성자"):
            parse_youtube_page(유튜브([bad]), "가상방")

    def test_유튜브_비채팅_제어이벤트는_기존대로_제외(self):
        control = 유튜브채팅(종류="messageDeletedEvent")
        self.assertEqual(parse_youtube_page(유튜브([control]), "가상방"), [])

    def test_유튜브_손상페이지는_커서_확정전_단계에서_중단(self):
        resume = YouTubeChatResumeState()
        resume.bind_chat("가상채팅방")
        with self.assertRaises(ValueError):
            resume.stage_page(
                parse_youtube_page(
                    유튜브([유튜브채팅(), {"snippet": {
                        "type": "textMessageEvent"}}]), "가상방"),
                "다음페이지", 1000, False)
        self.assertFalse(resume.pending_page_active)
        self.assertEqual(resume.next_page_token, "")
        self.assertEqual(len(resume.pending_page_chats), 0)


if __name__ == "__main__":
    unittest.main()
