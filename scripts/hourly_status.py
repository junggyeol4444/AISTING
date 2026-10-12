"""GitHub Actions step summary: 현재 단계 및 안전한 작업 경계."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with (root/"config/roadmap.json").open(encoding="utf-8") as f:
    roadmap=json.load(f)
steps=roadmap["steps"]
n=sum(x["status"]=="completed" for x in steps)
next_step=next((x for x in steps if x["status"]!="completed"),None)
print("## AISTING 정기 점검")
print(f"- 개발 진행률: {n}/{len(steps)}")
if next_step:
    print(f"- 다음 단계: {next_step['number']:03d} {next_step['title']}")
print("- 이 작업은 자동 테스트와 개발 작업 큐를 확인합니다.")
print("- 코드 자동작성은 별도 AI 에이전트 설정 전까지 수행하지 않습니다.")
