"""14단계 준비: 필요한 프로그램과 비용의 *사전 안내*만 제공한다.

이 모듈은 고정된 안내 문구만 조합한다. PC 사양/설치 현황/가격을 조회하지 않고
인터넷·파일·프로세스·설치·결제·사용자 승인 상태를 건드리지 않는다.
원본 기획안의 도구 '추천'과 현재 소스에서 '사용 중'인 도구를 구분한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramCostItem:
    category: str
    name: str
    purpose: str
    usage: str
    cost: str
    caution: str


@dataclass(frozen=True)
class SoftwareCostGuide:
    items: tuple[ProgramCostItem, ...]
    checked_pc_installations: bool = False
    checked_current_prices: bool = False
    installation_approved: bool = False
    payment_approved: bool = False
    live_broadcast_ready: bool = False

    def describe(self) -> str:
        lines = [
            "14단계 · 필요한 프로그램·비용 일괄 사전 안내",
            "현재 AISTING 소스와 원본 기획안의 *향후 후보*를 구분한 목록입니다.",
            "PC 설치 여부/가격을 조회한 결과가 아닙니다. 모든 가격은 현재 시세 미확인입니다.",
            "이 안내는 설치·다운로드·구매·사용권 확보·15단계 승인에 해당하지 않습니다.",
            "",
            "[비용 요약]",
            "- 기본 모의 채팅·설정·2D 샘플: 기존 Windows PC와 Python 실행 환경을 보유한 경우 추가 클라우드 AI API 요금 없이 사용하도록 설계됨.",
            "- Windows/PC 구입·추가 음성·아바타 제작·모델별 하드웨어·전기·저장장치 비용은 0원이라고 보장할 수 없음.",
            "- 유료 항목은 자동 구매하지 않으며, 선택 전에 라이선스·상업적 방송 이용 조건·최신 가격을 직접 확인해야 함.",
            "- 전체 예상 총액: 미산정 (PC 보유/모델/아바타/음성/실방송 방식 및 실제 가격 미확인).",
            "",
        ]
        previous_category = None
        for item in self.items:
            if item.category != previous_category:
                lines.extend([f"[{item.category}]", ""])
                previous_category = item.category
            lines.extend([
                f"■ {item.name} — {item.usage}",
                f"  용도: {item.purpose}",
                f"  비용: {item.cost}",
                f"  주의: {item.caution}",
                "",
            ])
        lines.extend([
            "[설치 전 승인·검증 경계]",
            "- 운영자 PC의 실제 설치 프로그램, Windows 라이선스, GPU/메모리, 모델 파일은 자동 조회하지 않았습니다.",
            "- 10단계 최종 개발 기준 승인, 11~13단계 실제 PC 검증, 15단계 프로그램 설치 승인은 모두 별도입니다.",
            "- 프로그램 설치, 계정 로그인, 인터넷 다운로드, OBS 송출, 원격 제어, 자동 과금은 실행하지 않습니다.",
            "- 로컬 AI 모델 다운로드·설치, 실제 음성/아바타 라이선스 확보는 별도 사용자 결정이 필요합니다.",
            "- 이 안내만으로 방송 준비 완료나 Windows 실기기 호환성 검증을 주장하지 않습니다.",
        ])
        return "\n".join(lines)


def build_software_cost_guide() -> SoftwareCostGuide:
    """항목 전체를 항상 한 번에 반환한다. 설정이나 시스템 정보를 조회하지 않는다."""
    entries = (
        ProgramCostItem("현재 로컬 소스 실행", "Windows PC / Windows 라이선스", "AISTING 실행 대상 운영체제", "사용자 보유 환경 확인 필요", "이미 보유했다면 추가 OS 구매 불필요할 수 있음; 신규 Windows/PC 구입 비용 미확인", "Windows 10/11 x64 실기기 실행 검증 전. PC·OS를 무료라고 간주하지 않음"),
        ProgramCostItem("현재 로컬 소스 실행", "Python 3.11 이상", "소스 ZIP을 Python으로 실행", "소스 실행에 필요", "무료로 이용 가능한 Python 배포본 있음; 별도 설치 필요 여부 미확인", "PC에 이미 있는지 미확인; 사용자가 설치 승인하기 전 자동 설치 없음"),
        ProgramCostItem("현재 로컬 소스 실행", "Tkinter · sqlite3 · JSON", "화면·로컬 기억·설정 파일", "현재 Python 표준 라이브러리 기반 구현", "일반 Python 배포에 포함되는 구성 요소로 별도 유료 API 필요 없음", "설치된 Python 빌드에 Tkinter 등이 있는지 실제 확인 필요"),
        ProgramCostItem("현재 로컬 소스 실행", "AISTING 내장 2D 샘플", "간단한 아바타 화면 표시", "현재 소스에 포함", "샘플 사용에 추가 외부 모델 구매 필요 없음", "실제 Live2D 모델/VRM·방송 송출 기능과 다름"),
        ProgramCostItem("현재 로컬 소스 실행", "Windows System.Speech 한국어 음성", "PC에 이미 설치된 음성으로 읽기", "선택형 기본 TTS 연동 구현", "이미 사용 가능한 OS 음성 사용 시 별도 클라우드 TTS 요금 없음", "한국어 음성이 설치됐는지·음성별 사용권은 확인 필요; 자동 추가 설치 없음"),
        ProgramCostItem("선택형 로컬 AI / 빌드", "Ollama", "운영자가 직접 실행한 로컬 텍스트 AI 연결", "선택형 localhost 연동 코드만 있음", "무료로 이용 가능한 로컬 실행 선택지; 모델·배포조건은 별도 확인", "사용자 PC에 설치/모델 다운로드 여부 미확인, 자동 다운로드 없음"),
        ProgramCostItem("선택형 로컬 AI / 빌드", "로컬 LLM 모델 파일", "Ollama에서 사용할 실제 AI 모델", "모델 미포함, 별도 선택 필요", "모델별 라이선스·저장 공간·전기료/하드웨어 비용 확인 필요", "무료 모델이라도 상업적 방송 이용 허용 여부와 PC 자원 요구량 확인"),
        ProgramCostItem("선택형 로컬 AI / 빌드", "PyInstaller", "Windows EXE 파일 만들기", "빌드 배치 파일 제공, EXE 미제공", "무료로 이용 가능한 빌드 도구; 별도 설치 여부 미확인", "Windows x64에서 실제 빌드·실행하지 않았으며 자동 설치 없음"),
        ProgramCostItem("향후 실방송 기능 (현재 미구현)", "OBS Studio · obs-websocket", "방송 화면·송출·자동 제어", "실제 연동/송출 미구현", "무료 이용 가능한 방송 소프트웨어 선택지; 최신 이용 조건 확인", "플랫폼 계정 연결/스트림 시작/OBS 설치는 승인 없이 실행 금지"),
        ProgramCostItem("향후 실방송 기능 (현재 미구현)", "실제 2D Live2D 모델 · VTube Studio", "완성형 2D 아바타·표정·립싱크", "기획안 후보, 현재 2D 샘플과 별개", "모델 제작·구매·상업 이용권·도구별 라이선스 비용 미확인", "현재 소스에 연동되지 않음; 특정 유료 제품을 필수로 확정하지 않음"),
        ProgramCostItem("향후 실방송 기능 (현재 미구현)", "3D VRM 모델 · 렌더러", "3D 캐릭터 화면·움직임", "운영자 선택형 향후 후보", "무료/유료 모델별 라이선스 및 제작비 미확인", "현재 3D 렌더러가 없으며 2D 샘플을 3D로 속여 표시하지 않음"),
        ProgramCostItem("향후 실방송 기능 (현재 미구현)", "가상 오디오 케이블 (예: VB-CABLE)", "음성 출력을 OBS로 전달", "기획안의 선택형 후보", "제품별 사용권·기부/상업 이용 조건 확인 필요", "필요 여부는 오디오 경로 설계 뒤 결정; 자동 설치 없음"),
        ProgramCostItem("향후 확장 후보 (미확정)", "Open-LLM-VTuber", "원본 기획안에서 권장한 방송 코어", "현재 AISTING 코드의 실제 기반 아님", "프로젝트·의존성별 라이선스 확인 필요; 최신 설치비 미확인", "현재 코드에 통합했다고 주장하지 않음; 설치/교체는 별도 결정"),
        ProgramCostItem("향후 확장 후보 (미확정)", "GPT-SoVITS / RVC 등 로컬 음성", "고급 한국어 음성 합성·선택형 학습", "미구현 후보", "도구·모델·음성 자료의 사용권과 PC 자원 비용 확인 필요", "음성 제공자 동의·라이선스·사용자 승인 없이 녹음/복제/학습 금지"),
        ProgramCostItem("향후 확장 후보 (미확정)", "Letta / ChromaDB", "확장형 장기기억", "기획안 후보; 현재는 SQLite 기억만 구현", "구성·배포 방식별 비용 및 라이선스 미확인", "서버·클라우드 연결을 기본값으로 추가하지 않음"),
        ProgramCostItem("향후 확장 후보 (미확정)", "공지 연동 도구 (예: discord.py)", "향후 방송 공지", "기획안 후보, 미구현", "도구 자체 외 플랫폼/API 정책·비용 미확인", "계정 연결·외부 공지 전송·API 호출은 승인 없이 하지 않음"),
        ProgramCostItem("기타 실사용 비용", "전기·저장 공간·하드웨어·인터넷", "장시간 PC 구동, 모델 저장, 향후 방송", "실제 사용 시 조건별로 발생", "사용량·PC 보유 여부·지역 요금에 따라 달라 총액 미산정", "무료 소프트웨어라도 전기료·네트워크·GPU 업그레이드 비용이 0원이라는 뜻은 아님"),
    )
    return SoftwareCostGuide(items=entries)
