from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = "You are a football YouTube Shorts scriptwriter. Write short, punchy, natural scripts with good flow."

USER_PROMPT_TEMPLATE = """
Write a YouTube Short script about this football story.

TITLE:
{title}

DETAILS:
{summary}

Rules:
- Keep it under 130 words
- No emojis
- Do not sound robotic
- Do not be overly corny
- Sound like a sharp football fan talking fast on TikTok or YouTube Shorts
- If the details are short, use recent form, rivalry, stakes, or fan reaction to make it more interesting
- Be specific and vivid, but do not make up fake facts

Structure:
1. Strong opening hook
2. Explain the story clearly
3. Give one opinionated takeaway
4. End with a question for comments

Do not label sections as HOOK, THE TEA, HOT TAKE, or QUESTION.
""".strip()


def generate_ai_script(article_title: str, summary: str) -> str:
    prompt = USER_PROMPT_TEMPLATE.format(title=article_title, summary=summary)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    return response.choices[0].message.content.strip()
