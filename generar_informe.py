import pandas as pd
import os
import json
from pathlib import Path
from pydantic import BaseModel
from google import genai
from google.genai import types

CONFIG_DIR = Path(__file__).parent / "config"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_context_notes() -> str:
    """Loads optional context.txt file from config directory."""
    context_path = CONFIG_DIR / "context.txt"
    if context_path.exists():
        with open(context_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "No extra context provided."


# ============================================================================
# GEMINI DYNAMIC CLASSIFICATION
# ============================================================================

class DiscoveredTopics(BaseModel):
    topics: list[str]

class CommentResult(BaseModel):
    index: int
    sentiment: str  # Positivo, Negativo, Neutro
    topic: str


def discover_campaign_topics(client: genai.Client, df_comments: pd.DataFrame, campaign_info: dict, brand_context: str) -> list[str]:
    """
    Pass 1: Analyzes campaign context & comment samples to dynamically determine overall categories.
    """
    print("🔍 Pass 1: Dynamically discovering campaign topics with Gemini...")
    
    # Get a representative sample of up to 100 comments
    sample_text = "\n".join(df_comments['comment_text'].dropna().sample(min(100, len(df_comments))).tolist())

    prompt = f"""
You are a social media analyst. Based on the campaign details, brand context, and comment samples below, define between 5 to 7 concise, mutually exclusive topic categories to classify all social listening comments.

Campaign Info: {json.dumps(campaign_info, ensure_ascii=False)}
Brand Context: {brand_context}

Comment Samples:
{sample_text}

Rules:
- Keep topic names brief (e.g., 'Atención al Cliente', 'Precio y Promociones', 'Calidad de Producto').
- Always include 'Otros' as a fallback category.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DiscoveredTopics,
                temperature=0.2,
            ),
        )
        topics = json.loads(response.text).get('topics', ['General', 'Otros'])
        print(f"✅ Discovered Topics: {topics}")
        return topics
    except Exception as e:
        print(f"⚠️ Error discovering topics, falling back to default: {e}")
        return ['Atención al Cliente', 'Calidad de Producto', 'Precio y Ofertas', 'Empaque', 'Otros']


def analyze_comments_with_gemini(df_comments: pd.DataFrame, campaign_info: dict) -> tuple:
    """
    Pass 2: Classifies sentiment and assigns comments to the dynamically discovered topics.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY environment variable missing.")

    client = genai.Client(api_key=api_key)
    brand_context = load_context_notes()

    # Step 1: Pass 1 - Generate dynamic categories
    discovered_topics = discover_campaign_topics(client, df_comments, campaign_info, brand_context)
    topics_list_str = ", ".join(discovered_topics)

    # Step 2: Pass 2 - Batch Classification
    batch_size = 40
    sentiments, topics = {}, {}
    
    comments_list = [
        {"index": int(idx), "text": str(row['comment_text'])}
        for idx, row in df_comments.iterrows()
    ]
    
    total_comments = len(comments_list)
    print(f"🤖 Pass 2: Classifying {total_comments} comments in batches of {batch_size}...")

    for i in range(0, total_comments, batch_size):
        batch = comments_list[i:i + batch_size]

        prompt = f"""
You are a social listening expert analyzing comments for {campaign_info.get('campaign_marca', 'the brand')}.

BRAND CONTEXT & NOTES:
{brand_context}

INSTRUCTIONS:
1. 'sentiment': Classify strictly as 'Positivo', 'Negativo', or 'Neutro'. Account for sarcasm, emojis, and Colombian slang.
2. 'topic': Pick the best fitting category strictly from this list: [{topics_list_str}].

Batch to analyze:
{json.dumps(batch, ensure_ascii=False)}
"""

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[CommentResult],
                    temperature=0.1,
                ),
            )
            parsed_results = json.loads(response.text)
            for item in parsed_results:
                sentiments[item['index']] = item['sentiment']
                topics[item['index']] = item['topic']

        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            for item in batch:
                sentiments[item['index']] = 'Neutro'
                topics[item['index']] = 'Otros'

    return df_comments.index.map(sentiments).fillna('Neutro'), df_comments.index.map(topics).fillna('Otros')
