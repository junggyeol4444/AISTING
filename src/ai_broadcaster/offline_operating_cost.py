"""Original 096: manual, offline *estimate* of operating costs in KRW.

No rates or usage are observed or downloaded. No network, account, billing,
filesystem, user PC inspection, background scheduler or payment integration.
Missing entries are unknown (never silently assumed free); even a complete
estimate is not proof of actual charges or license suitability.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import re
from collections.abc import Mapping


# Every number must be entered explicitly by the operator. Usage and price
# units are paired, with no embedded external provider prices.
COST_FIELDS = (
    ('api_input', 'LLM 입력 토큰', '100만 토큰', Decimal(1_000_000)),
    ('api_output', 'LLM 출력 토큰', '100만 토큰', Decimal(1_000_000)),
    ('server', '서버 사용 시간', '시간', Decimal(1)),
    ('tts', '음성 합성 글자 수', '1,000자', Decimal(1_000)),
    ('electricity', '전력 소비', 'kWh', Decimal(1)),
)
REQUIRED_KEYS = frozenset(
    f'{key}_{suffix}' for key, *_ in COST_FIELDS for suffix in ('usage', 'rate')
)
MONEY = Decimal('0.01')
NUMBER = re.compile(r'\d{1,12}(?:\.\d{1,6})?\Z')


class CostInputError(ValueError):
    """An invalid manual estimate input; no fallback to an assumed zero."""


def parse_number(value: str, label: str) -> Decimal | None:
    if type(value) is not str:
        raise CostInputError(f'{label}: 숫자 문자열을 입력하세요.')
    trimmed = value.strip()
    if trimmed == '':
        return None
    if not NUMBER.fullmatch(trimmed):
        raise CostInputError(f'{label}: 0 이상의 십진수만 입력하세요 (소수 6자리 이하).')
    return Decimal(trimmed)


@dataclass(frozen=True)
class CostLine:
    key: str
    name: str
    unit: str
    entered_usage: Decimal | None
    entered_rate: Decimal | None
    estimated_krw: Decimal | None

    @property
    def known(self) -> bool:
        return self.estimated_krw is not None


@dataclass(frozen=True)
class CostEstimate:
    lines: tuple[CostLine, ...]
    known_subtotal_krw: Decimal
    budget_krw: Decimal | None
    budget_status: str
    all_known: bool
    mock_only: bool = True
    actual_charge_verified: bool = False

    def describe(self) -> str:
        out = ['원본 096 · 운영 비용 수동 입력 추정 (실제 청구·결제 조회 없음)',
               '단위: KRW(원), 운영자가 직접 기입한 동일 기간의 사용량·가상/수동 단가']
        for line in self.lines:
            price = f'{line.estimated_krw:,.2f}원 (추정)' if line.known else '미산정 — 사용량 또는 단가 미입력'
            out.append(f'• {line.name} [{line.unit}당 단가]: {price}')
        out.append(f'확인 가능한 입력 기준 소계: {self.known_subtotal_krw:,.2f}원 '
                   + ('(전체 입력 완료)' if self.all_known else '(일부 항목 미산정, 총액 아님)'))
        out.append('예산: ' + (f'{self.budget_krw:,.2f}원' if self.budget_krw is not None else '미입력'))
        out.append('예산 판정: ' + self.budget_status)
        out.append('실제 과금·가격·VAT·환율·할인·무료 제공량·라이선스·PC 전기요금: 미확인')
        out.append('계산 결과는 실제 송출·클라우드 사용·요금 납부를 증명하지 않습니다.')
        return '\n'.join(out)


def estimate_operating_cost(inputs: Mapping[str, str], budget: str = '') -> CostEstimate:
    """Estimate five components for one operator-chosen common accounting period.

    Unknown component != zero. A budget can be declared exceeded when its
    already-known subtotal exceeds it; with unknown components, a seemingly
    safe subtotal is *not* evidence that the budget is safe.
    """
    if not isinstance(inputs, Mapping) or set(inputs) != REQUIRED_KEYS:
        raise CostInputError('비용 항목 키가 누락되거나 예상 외 항목이 있습니다.')
    parsed_budget = parse_number(budget, '예산')
    lines = []
    raw_sum = Decimal(0)
    for key, name, unit, divisor in COST_FIELDS:
        usage = parse_number(inputs[f'{key}_usage'], f'{name} 사용량')
        rate = parse_number(inputs[f'{key}_rate'], f'{name} 단가')
        # Explicit zero use has zero cost even if the corresponding unit rate
        # was not entered; blank use with a zero rate is still unknown.
        amount = (Decimal(0) if usage == 0 else
                  (usage * rate / divisor if usage is not None and rate is not None else None))
        if amount is not None:
            raw_sum += amount
        lines.append(CostLine(key, name, unit, usage, rate,
                              amount.quantize(MONEY, rounding=ROUND_HALF_UP)
                              if amount is not None else None))
    subtotal = raw_sum.quantize(MONEY, rounding=ROUND_HALF_UP)
    all_known = all(line.known for line in lines)
    if parsed_budget is None:
        status = '예산 미입력 — 초과 여부 판단 불가'
    elif raw_sum > parsed_budget:
        status = '경고: 알려진 비용만으로도 예산 초과'
    elif not all_known:
        status = '미확정: 일부 비용 미산정 — 예산 이내로 판정하지 않음'
    else:
        status = '수동 입력 추정상 예산 이내 (실제 청구 검증 아님)'
    return CostEstimate(tuple(lines), subtotal, parsed_budget, status, all_known)
