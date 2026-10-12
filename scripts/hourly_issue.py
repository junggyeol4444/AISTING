"""GitHub 예약 작업: 아직 열린 개발 단계 Issue가 없으면 다음 단계 생성.

GitHub Actions GITHUB_TOKEN(issues:write)을 사용; 비밀 키를 코드에 저장하지 않음.
"""
import json
import os
import subprocess
from pathlib import Path

def main() -> int:
    root=Path(__file__).resolve().parents[1]
    with (root/"config/roadmap.json").open(encoding="utf-8") as f:
        steps=json.load(f)["steps"]
    current=next((x for x in steps if x["status"]!="completed"),None)
    if current is None:
        print("모든 단계 완료")
        return 0
    if not os.getenv("GH_TOKEN"):
        print("GH_TOKEN 미설정: GitHub Actions 환경에서만 Issue 자동 생성")
        return 0
    target=f"[AISTING 개발] {current['number']:03d} {current['title']}"
    result=subprocess.run(["gh","issue","list","--state","all","--limit","100","--json","title,state"],
                          capture_output=True,text=True,check=True)
    all_issues=json.loads(result.stdout)
    if any(i["title"]==target for i in all_issues):
        print("해당 단계 Issue가 이미 존재함")
        return 0
    body=(f"100단계 로드맵의 {current['number']}단계 작업 큐입니다.\n\n"
          f"**목표:** {current['title']}\n\n"
          "체크: 기획안에 맞는 개발/테스트 산출물, 운영자 승인 필요 항목 확인, "
          "config/roadmap.json의 상태 갱신.\n\n"
          "**주의:** 이 Issue를 만든 것만으로 코딩이 자동 수행되는 것은 아닙니다. "
          "AI 코드 자동작성은 별도 에이전트 연동이 필요합니다.")
    subprocess.run(["gh","issue","create","--title",target,"--body",body],check=True)
    print("개발 단계 Issue 생성:",target)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
