# mock_ai.py
# ------------------------------------------------------------
# ⭐ 이 파일은 "AI 연동을 흉내 내는 더미(mock) 함수" 모음입니다.
# 사용자가 이번 단계에서 "일단 더미 응답으로 UI 흐름만 구현"을 선택했기 때문에,
# 실제 OpenAI/Claude API를 호출하는 대신 그럴듯한 고정/랜덤 응답을 돌려줍니다.
#
# 🔧 나중에 실제 AI를 연동할 때는:
#   - 이 파일 안의 함수 "내부 구현"만 실제 API 호출 코드로 바꿔치기 하면 됩니다.
#   - 함수의 이름과 반환값 구조(딕셔너리 형태)는 그대로 유지하면
#     views/ 폴더의 화면 코드는 전혀 수정할 필요가 없습니다. (관심사 분리)
# ------------------------------------------------------------

import random
import time


def generate_retest_questions(assignment, question_bank, count=10):
    """
    [AI 연동 지점 ①] 학생의 서술형 제출 답안을 근거로 재검사 문항을 선정하는 기능의 더미 버전.

    실제 구현 시에는:
      - 학생이 제출한 PDF를 텍스트로 추출(OCR/파싱)
      - 해당 텍스트 + 과제의 평가요소를 프롬프트에 넣어 AI 모델(API) 호출
      - AI가 "어떤 개념이 부족해 보이는지"를 판단해 문항은행에서 N개를 선정하거나 새로 생성

    지금은 문항은행(question_bank)에서 무작위로 count개를 뽑아 반환하고,
    문항 선정 "근거"도 고정 템플릿 문장으로 대체합니다.
    """
    time.sleep(0.3)  # 실제 API 호출처럼 약간의 지연이 있는 것을 흉내 (UX 확인용)
    selected = random.sample(question_bank, min(count, len(question_bank)))
    reason = (
        "학생의 서술형 답안 중 판 경계 관련 서술을 근거로, "
        "세 가지 경계 유형의 개념과 사례를 확인하는 문항을 생성했습니다."
    )
    return selected, reason


def generate_ai_feedback(student_name, score, total, reliability):
    """
    [AI 연동 지점 ②] 재검사 결과를 바탕으로 AI 피드백(문항생성근거/이해도판단/보충제안)을
    생성하는 기능의 더미 버전. 기획안 15번/21번 슬라이드 문구 톤을 참고해 구성했습니다.

    반환값은 항상 아래 3개 key를 가진 dict 입니다. (실제 연동 시에도 이 구조를 유지할 것)
    """
    time.sleep(0.3)
    basis = (
        f"{student_name} 학생의 서술형 답안 중 판 경계 관련 서술을 근거로, "
        f"세 가지 경계 유형의 개념과 사례를 확인하는 문항 {total}개를 생성했습니다."
    )
    judgement = (
        f"생성형 AI 작성 점검기 표절률 30% 미만, 재검사 {total}문항 중 {score}문항 정답으로 "
        f"과제 신뢰도 {reliability}%로 추정됩니다. 발산형·수렴형 경계는 이해했으나, "
        f"변환형 경계 관련 문항에서 오답 경향이 확인됩니다."
    )
    suggestion = (
        "변환형 경계 보충 자료(산안드레아스 단층 사례)를 우선 제공하고, "
        "이해 후 판 경계 유형별 지형 비교 심화 과제를 제안합니다."
    )
    return {
        "basis": basis,
        "judgement": judgement,
        "suggestion": suggestion,
    }


def check_plagiarism(pdf_text: str) -> int:
    """
    [AI 연동 지점 ③] 생성형 AI 작성 여부(표절률) 점검 기능의 더미 버전.
    실제로는 표절검사 API 또는 별도 판별 모델을 호출해 0~100 사이 표절 의심 비율을 반환합니다.
    지금은 임의의 값을 반환합니다.
    """
    time.sleep(0.2)
    return random.randint(0, 35)


def grade_short_answer(student_answer: str, correct_answer: str) -> bool:
    """
    [AI 연동 지점 ④] 단답형 문항 채점 더미 버전.
    실제로는 AI에게 "의미가 같은지" 판단시키는 것이 이상적이나,
    지금은 공백/대소문자를 무시한 단순 문자열 일치로 채점합니다.
    """
    if student_answer is None:
        return False
    return student_answer.strip().replace(" ", "") == correct_answer.strip().replace(" ", "")
