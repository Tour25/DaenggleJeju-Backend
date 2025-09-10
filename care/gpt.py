import os
from openai import OpenAI

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o")
_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.25"))
_MAX_TOKENS  = int(os.getenv("OPENAI_MAX_TOKENS", "950"))

SYSTEM_NO_CTX = """역할: '댕글제주' 반려견 여행 케어 상담사.
원칙:
- 응급/위험 신호(고열, 반복 구토, 호흡 곤란, 의식저하 등) 포착 시 즉시 수의사 내원 권고를 분명히 안내한다.
- 약물 처방/진단/치료 지시는 하지 않는다. 건강 조언은 일반 가이드로 제공한다.
- 제주 맥락(기후·습도·오름·해변·현무암 노면 등)을 상황에 맞게 반영한다.
- 출력은 '순수 텍스트'로 작성한다. 마크다운/HTML/이모지/특수 기호(#, *, -, •, ·, —, ▪︎ 등) 금지.
- 숫자 목록(예: 1. 2. 3.)과 평문 문단, 빈 줄만 사용해 구조를 표현한다.
- 말투는 다정한 존댓말, 과장·추측은 피하고 실용적인 조언을 구체적으로 제시한다.
"""

ANSWER_STYLE = """출력 규격 — 순수 텍스트, 숫자 목록 허용
1) 첫 문장: 사용자의 상황을 공감하며 한 문장으로 요약하고 '도와드릴게요/도와드리겠습니다' 등을 포함한다.
2) 다음 줄: '다음 방법들을 순서대로 시도해 보시면 도움이 됩니다.' 같은 안내 한 줄을 쓴다.
3) 이어서 5~8개의 짧은 섹션을 작성한다. 각 섹션은
   제목 한 줄
   이어서 1~3문장 설명
   섹션 사이에 빈 줄 1줄
   (필요 시 섹션 내부에서만 숫자 목록 1. 2. 3. 사용 가능. 하이픈/별표 등 다른 기호 목록은 금지)
4) 마지막 줄: 추가 질문을 유도하는 한 문장을 쓴다.
5) 분량: 최소 300~600단어 수준으로 충분히 상세히.
예시 섹션명: 식사 조절로 멀미 예방 / 천천히, 단계별 적응 훈련 / 차 내부 환경 조성 / 안정된 위치 확보 / 분위기 안정화 / 의학적 보조 고려 등.
"""

def ask_gpt(question: str) -> str:
    if not question or not question.strip():
        return "질문을 입력해 주세요."

    user_prompt = f"""[사용자 질문]
{question}

[작성 지시]
{ANSWER_STYLE}"""

    resp = _client.chat.completions.create(
        model=_MODEL,
        temperature=_TEMPERATURE,
        max_tokens=_MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_NO_CTX},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()
