import csv
import json
import os
from openai import OpenAI

# 环境变量建议
# API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# if(API_KEY == ""):
#      print("Error with API Key!")
API_KEY = "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"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

def makePrompt():
    # 1. 读取 CSV 数据
    csv_path = "/app/output/google_trends_raw.csv"
    csv_content = ""
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            csv_content = f.read()
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

    # 2. 构建 Prompt
    # 注意：为了兼容 TrendRadar，我们将评价(Evaluation)拼入 Title，或作为单独字段
    # 这里我们采用“Title拼入评价”的策略，这样在飞书卡片上最直观
    prompt = f"""This is the top trends in United States today (CSV format):
---
{csv_content}
---
Your job: Filter these trends based on my interest.
Interested: Funny events, entertainment, scandals, pop culture, light-hearted viral news.
UNINTERESTED: Serious politics, diplomacy, war, deaths/obituaries, sports (especially baseball).

Task:
1. Identify interest-matching trends.
2. For each, provide a short "AI Insight" (one short paragraph in chinese. Focus on it's impact or insight on mini games's ads idea or its user acquisition).
3. Format as a STICKY JSON for TrendRadar compatibility.
4. For each event, it's necessary to go into each url and read the content. (or the data cleansing is not sufficient) You're required to select the most insightfull event.
5. You should point out that some of the trend are not very good for game ads insight nor UA. 

The JSON structure MUST follow this exact template(you must give an json dictionary not a json array):
{{
  "google_trend_ai": {{
    "Trend Title [AI Insight in point 2]": {{
      "url": "primary_link_from_csv",
      "ranks": [rank_number],
      "mobileUrl": ""
    }}
  }}
}}
"""
    return prompt

def process_ai_response():
    prompt_content = makePrompt()
    if not prompt_content: return

    response = client.chat.completions.create(
        model="google/gemini-3-flash-preview", # 建议使用更稳定的版本名
        messages=[{"role": "user", "content": prompt_content}],
        # 强制 AI 输出 JSON 格式
        response_format={"type": "json_object"} 
    )

    # 提取内容
    ai_content = response.choices[0].message.content
    
    # 验证并保存
    try:
        data = json.loads(ai_content)
        output_path = "/app/output/ai_result.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ AI Analysis saved to {output_path}")
    except Exception as e:
        print(f"❌ Failed to parse AI JSON: {e}\nRaw content: {ai_content}")

if __name__ == "__main__":
    process_ai_response()