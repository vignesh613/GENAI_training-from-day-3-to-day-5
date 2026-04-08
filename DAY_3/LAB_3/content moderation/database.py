from typing import Dict, List
from models import ContentItem, ModerationStatus

# Simple in-memory mock storage
content_store: Dict[str, ContentItem] = {}

def save_content(item: ContentItem):
    content_store[item.id] = item

def get_content(content_id: str) -> ContentItem:
    return content_store.get(content_id)

def get_all_content() -> List[ContentItem]:
    return list(content_store.values())

def get_review_queue() -> List[ContentItem]:
    return [item for item in content_store.values() if item.status == ModerationStatus.HUMAN_REVIEW]
