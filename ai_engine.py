# ai_engine.py
# ------------------------------------------------------------
# 실제 생성형 AI(OpenAI ChatGPT) 연동 모듈.
# mock_ai.py는 뼈대 단계의 "가짜" 응답이었지만, 이 파일은 학생이 실제로 제출한
# PDF 답안 내용을 근거로 진짜 AI에게 객관식(5지선다) 문항을 생성하도록 요청합니다.
#
# 필요 환경변수: OPENAI_API_KEY (config.py 참고)
# ------------------------------------------------------------

import json
import config


class AIEngineError(Exception):
    """AI 문항 생성 과정에서 발생한 오류를 화면에 안내하기 위한 예외."""
    pass


def extract_pdf_pages(pdf_path):
    """
    PDF 파일에서 페이지별 텍스트를 추출합니다.
    반환값: [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}, ...]
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise AIEngineError(
            "PDF 텍스트 추출에 필요한 'pypdf' 패키지가 설치되어 있지 않습니다. "
            "`pip install pypdf`로 설치해주세요."
        )

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        raise AIEngineError(f"PDF 파일을 여는 중 오류가 발생했습니다: {e}")

    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        pages.append({"page": i, "text": text})

    if not any(p["text"] for p in pages):
        raise AIEngineError(
            "이 PDF에서 텍스트를 추출할 수 없었습니다. 스캔 이미지로만 이루어진 PDF는 "
            "현재 지원되지 않습니다(텍스트가 포함된 PDF만 가능합니다)."
        )
    return pages


def _build_pdf_context(pages):
    """AI 프롬프트에 넣을, 페이지 번호가 표시된 학생 답안 텍스트를 만듭니다."""
    parts = []
    for p in pages:
        if p["text"]:
            parts.append(f"[페이지 {p['page']}]\n{p['text']}")
    return "\n\n".join(parts)


def generate_ai_feedback(student_name, assignment_title, achievement_standard, score, total, reliability_label, wrong_answers):
    """
    학생의 실제 재검사 결과(점수/신뢰도)와 오답 내용을 근거로 AI 피드백 3가지
    (문항 생성 근거 / 이해도 판단 / 보충·심화 제안)를 실제로 생성합니다.

    wrong_answers: [{"question_text":..., "student_answer":..., "correct_answer":...}, ...]
    반환값: {"basis": "...", "judgement": "...", "suggestion": "..."}
    """
    if not config.OPENAI_API_KEY:
        raise AIEngineError(
            "AI 피드백 생성을 위해서는 OPENAI_API_KEY 환경변수 설정이 필요합니다. "
            "터미널에서 API 키를 설정한 뒤 앱을 다시 실행해주세요."
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise AIEngineError(
            "AI 연동에 필요한 'openai' 패키지가 설치되어 있지 않습니다. "
            "`pip install openai`로 설치해주세요."
        )

    wrong_text = "\n".join(
        f"- 문항: {w['question_text']} / 학생 답: {w['student_answer'] or '(미응답)'} / 정답: {w['correct_answer']}"
        for w in wrong_answers
    ) or "(오답 없음 - 전 문항 정답)"

    system_prompt = (
        "너는 고등학교 지구과학 교사를 돕는 평가 도우미다. 학생의 재검사(이해도 확인) 결과를 바탕으로 "
        "교사에게 보여줄 피드백을 작성한다. 반드시 실제로 제공된 점수·오답 정보만 근거로 삼고, "
        "존재하지 않는 내용을 지어내면 안 된다. 출력은 오직 JSON 객체여야 하며, 다른 설명 없이 JSON만 응답한다."
    )
    user_prompt = f"""[과제명] {assignment_title}
[성취기준] {achievement_standard}
[학생] {student_name}
[재검사 점수] {score} / {total}
[과제 신뢰도] {reliability_label}
[오답 문항 목록]
{wrong_text}

위 정보를 바탕으로 아래 3가지를 JSON으로 작성해줘:
{{
  "basis": "이 학생에게 어떤 근거로 재검사 문항을 생성했는지에 대한 1~2문장 요약",
  "judgement": "재검사 점수와 오답 경향을 근거로 한 이해도 판단 내용 (구체적인 오답 개념 언급)",
  "suggestion": "오답 경향을 보완할 수 있는 보충·심화 과제 제안 1~2문장"
}}
"""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise AIEngineError(f"AI 호출 중 오류가 발생했습니다: {e}")

    raw_text = (response.choices[0].message.content or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        feedback = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise AIEngineError(f"AI 응답을 해석할 수 없었습니다(JSON 파싱 오류): {e}")

    return {
        "basis": str(feedback.get("basis", "")).strip(),
        "judgement": str(feedback.get("judgement", "")).strip(),
        "suggestion": str(feedback.get("suggestion", "")).strip(),
    }

def generate_personalized_questions(pdf_path, count, unit_name, achievement_standard, question_text):
    """
    학생이 제출한 PDF 답안을 실제로 읽어, 그 내용을 근거로 5지선다 객관식 문항을 생성합니다.

    반환값: [
        {
            "question_text": "...",
            "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
            "answer": "보기 중 정답 문자열",
            "basis_page": 2,
            "basis_quote": "학생이 실제로 작성한 문장 원문 일부",
        },
        ...
    ]
    """
    if not config.OPENAI_API_KEY:
        raise AIEngineError(
            "AI 문항 생성을 위해서는 OPENAI_API_KEY 환경변수 설정이 필요합니다. "
            "터미널에서 API 키를 설정한 뒤 앱을 다시 실행해주세요."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise AIEngineError(
            "AI 연동에 필요한 'openai' 패키지가 설치되어 있지 않습니다. "
            "`pip install openai`로 설치해주세요."
        )

    pages = extract_pdf_pages(pdf_path)
    pdf_context = _build_pdf_context(pages)

    system_prompt = (
        "너는 고등학교 지구과학 교사를 돕는 평가 도우미다. "
        "학생이 제출한 서술형 과제 답안(페이지 번호 표시됨)을 읽고, 그 학생이 실제로 작성한 "
        "내용을 근거로 학생의 이해도를 확인할 수 있는 객관식(5지선다) 문항을 만든다. "
        "반드시 학생이 쓴 문장 중 실제로 존재하는 표현을 인용해서 근거로 제시해야 하며, "
        "존재하지 않는 내용을 지어내면 안 된다. "
        "출력은 오직 JSON 배열이어야 하며, 다른 설명이나 마크다운 코드블록 없이 JSON만 응답한다."
    )

    user_prompt = f"""[단원명]
{unit_name}

[성취기준]
{achievement_standard}

[평가문항(원래 서술형 과제 질문)]
{question_text}

[학생이 제출한 답안 (페이지별)]
{pdf_context}

위 학생 답안을 근거로, 이 학생의 이해도를 확인하는 5지선다 객관식 문항을 정확히 {count}개 만들어줘.
각 문항은 다음 JSON 형식의 객체로 만들고, 전체를 JSON 배열로 응답해:
{{
  "question_text": "문항 내용",
  "choices": ["보기1", "보기2", "보기3", "보기4", "보기5"],
  "answer": "choices 중 정답과 완전히 동일한 문자열",
  "basis_page": 학생 답안에서 근거가 된 페이지 번호(정수),
  "basis_quote": "학생이 실제로 작성한 문장 중 이 문항의 근거가 된 부분(원문 그대로 인용, 40자 내외)"
}}
"""

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        raise AIEngineError(f"AI 호출 중 오류가 발생했습니다: {e}")

    raw_text = (response.choices[0].message.content or "").strip()
    # 혹시 코드블록(```json ... ```)으로 감싸서 응답한 경우 제거
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        questions = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise AIEngineError(f"AI 응답을 해석할 수 없었습니다(JSON 파싱 오류): {e}")

    if not isinstance(questions, list) or not questions:
        raise AIEngineError("AI가 문항을 생성하지 못했습니다. 다시 시도해주세요.")

    # 최소한의 형식 검증 및 보정
    cleaned = []
    for q in questions[:count]:
        choices = q.get("choices") or []
        if len(choices) < 2:
            continue
        cleaned.append({
            "question_text": q.get("question_text", "").strip(),
            "choices": [str(c) for c in choices],
            "answer": str(q.get("answer", "")).strip(),
            "basis_page": int(q.get("basis_page") or 0) or None,
            "basis_quote": str(q.get("basis_quote", "")).strip(),
        })

    if not cleaned:
        raise AIEngineError("AI 응답에 유효한 문항이 없었습니다. 다시 시도해주세요.")

    return cleaned
