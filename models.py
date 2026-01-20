from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class ScientificReference(BaseModel):
    fact: str
    source_name: str
    source_url: str

class HotTopic(BaseModel):
    headline_th: str
    reason: str
    keywords: List[str]

class CompetitorArticle(BaseModel):
    title: str
    url: str
    summary: str
    gap: str

class ResearchResults(BaseModel):
    trending_topics: List[str]
    scientific_references: List[ScientificReference]
    image_urls: List[str]
    key_takeaways: str

class SEOArticleMetadata(BaseModel):
    title: str
    content_html: str
    excerpt: str
    seo_keyphrase: str
    seo_meta_description: str
    slug: str
    suggested_categories: List[str]
    in_article_image_prompts: List[str]
    faq_schema_html: Optional[str] = None
