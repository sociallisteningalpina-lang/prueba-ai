import pandas as pd
import os
import json
import sys
from pathlib import Path
from pydantic import BaseModel
from google import genai
from google.genai import types

# Import campaign metadata from config
sys.path.insert(0, str(Path(__file__).parent / "config"))
from topic_classifier import get_campaign_metadata


# ============================================================================
# GEMINI BATCH ANALYSIS FUNCTION
# ============================================================================

class CommentResult(BaseModel):
    index: int
    sentiment: str  # Must be Positivo, Negativo, or Neutro
    topic: str      # Must match one of the campaign categories


def analyze_comments_with_gemini(df_comments: pd.DataFrame, categories: list) -> tuple:
    """
    Sends comments in batches to Gemini for sentiment and topic classification.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)
    
    categories_str = ", ".join(categories) if categories else "General, Atención al Cliente, Producto"
    batch_size = 40
    
    sentiments = {}
    topics = {}
    
    # Prepare list of items with their DataFrame index
    comments_list = [
        {"index": int(idx), "text": str(row['comment_text'])}
        for idx, row in df_comments.iterrows()
    ]
    
    total_comments = len(comments_list)
    print(f"🤖 Processing {total_comments} comments with Gemini in batches of {batch_size}...")

    for i in range(0, total_comments, batch_size):
        batch = comments_list[i:i + batch_size]
        print(f"  └─ Analyzing batch {i // batch_size + 1} / {(total_comments + batch_size - 1) // batch_size}...")

        prompt = f"""
You are an expert social media analyst specializing in Latin American slang, internet culture, emojis, and subtle sarcasm (e.g., 'qué buen servicio 🙄' is Negative).

Analyze these social media comments:
1. 'sentiment': Classify strictly as 'Positivo', 'Negativo', or 'Neutro'.
2. 'topic': Assign the best fitting category strictly from this list: [{categories_str}]. If none fit, use 'Otro'.

Comments batch:
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
            print(f"⚠️ Error analyzing batch starting at {i}: {e}")
            # Fallback for failed items in batch
            for item in batch:
                sentiments[item['index']] = 'Neutro'
                topics[item['index']] = 'Otro'

    # Map back to DataFrame order
    sentiment_series = df_comments.index.map(sentiments).fillna('Neutro')
    topic_series = df_comments.index.map(topics).fillna('Otro')

    return sentiment_series, topic_series


# ============================================================================
# MAIN REPORT GENERATION
# ============================================================================

def run_report_generation():
    print("--- INICIANDO GENERACIÓN DE INFORME HTML ---")
    
    try:
        df = pd.read_excel('Comentarios Campaña.xlsx')
        print("Archivo 'Comentarios Campaña.xlsx' cargado con éxito.")
    except FileNotFoundError:
        print("❌ ERROR: No se encontró el archivo 'Comentarios Campaña.xlsx'.")
        return

    # --- Limpieza y preparación de datos ---
    df['created_time_processed'] = pd.to_datetime(df['created_time_processed'])
    df['created_time_colombia'] = df['created_time_processed'] - pd.Timedelta(hours=5)

    if 'post_url_original' not in df.columns:
        df['post_url_original'] = df['post_url'].copy()

    all_unique_posts = df[['post_url', 'post_url_original', 'platform']].drop_duplicates(subset=['post_url']).copy()
    all_unique_posts.dropna(subset=['post_url'], inplace=True)

    df_comments = df.dropna(subset=['created_time_colombia', 'comment_text', 'post_url']).copy()
    df_comments.reset_index(drop=True, inplace=True)

    comment_counts = df_comments.groupby('post_url').size().reset_index(name='comment_count')
    unique_posts = pd.merge(all_unique_posts, comment_counts, on='post_url', how='left')
    unique_posts.loc[:, 'comment_count'] = unique_posts['comment_count'].fillna(0).astype(int)
    unique_posts.sort_values(by='comment_count', ascending=False, inplace=True)
    unique_posts.reset_index(drop=True, inplace=True)
    
    post_labels = {row['post_url']: f"Pauta {index + 1} ({row['platform']})" for index, row in unique_posts.iterrows()}
    unique_posts['post_label'] = unique_posts['post_url'].map(post_labels)
    df_comments['post_label'] = df_comments['post_url'].map(post_labels)
    
    all_posts_json = json.dumps(unique_posts.to_dict('records'))

    # ========================================================================
    # ANÁLISIS DE SENTIMIENTOS Y TEMAS CON GEMINI
    # ========================================================================
    
    campaign_info = get_campaign_metadata()
    categories = campaign_info.get('categories', [])
    print(f"Campaña: {campaign_info.get('campaign_name', 'General')}")
    print(f"Categorías configuradas: {categories}")

    # Run Gemini Batch Classification
    df_comments['sentimiento'], df_comments['tema'] = analyze_comments_with_gemini(df_comments, categories)
    
    print("Análisis con Gemini completado.")

    # Prepare JSON for dashboard
    if 'is_reply' not in df_comments.columns:
        df_comments['is_reply'] = False

    df_for_json = df_comments[[
        'created_time_colombia', 'comment_text', 'sentimiento', 
        'tema', 'platform', 'post_url', 'post_label', 'is_reply'
    ]].copy()
    
    df_for_json['is_reply'] = df_for_json['is_reply'].fillna(False).astype(bool)

    df_for_json.rename(columns={
        'created_time_colombia': 'date', 
        'comment_text': 'comment', 
        'sentimiento': 'sentiment', 
        'tema': 'topic'
    }, inplace=True)
    
    df_for_json['date'] = df_for_json['date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    all_data_json = json.dumps(df_for_json.to_dict('records'))

    min_date = df_comments['created_time_colombia'].min().strftime('%Y-%m-%d') if not df_comments.empty else ''
    max_date = df_comments['created_time_colombia'].max().strftime('%Y-%m-%d') if not df_comments.empty else ''
    
    post_filter_options = '<option value="Todas">Ver Todas las Pautas</option>'
    for url, label in post_labels.items():
        post_filter_options += f'<option value="{url}">{label}</option>'

    # --- Standard HTML Dashboard generation remains unchanged ---
    # [Rest of your HTML string rendering code goes here...]
