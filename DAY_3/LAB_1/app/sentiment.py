import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

# Using a Twitter RoBERTa model natively trained for 3-class sentiment (positive, negative, neutral)
try:
    sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")
except Exception as e:
    logger.error(f"Failed to load sentiment model: {e}")
    raise

def analyze_sentiment(text: str) -> str:
    """Returns standard labels: 'positive', 'negative', or 'neutral'"""
    try:
        result = sentiment_analyzer(text)[0]
        label = result['label'].lower()
        
        # Map to branches based on known outputs of the model
        if label in ['positive', 'label_2']: return 'positive'
        if label in ['negative', 'label_0']: return 'negative'
        return 'neutral'
    except Exception as e:
        logger.error(f"Error analyzing sentiment for text '{text}': {e}")
        return 'neutral' # Safe fallback
