"""Singleton-style website configuration documents.

Each of these collections is expected to hold a single document (the active
configuration). The service layer enforces the singleton semantics.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import ImageAsset, TimestampedDocument


class WorkingHour(BaseModel):
    """Opening hours for a single day of the week."""

    day: str
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_closed: bool = False


class HeroStat(BaseModel):
    """A single stat displayed in the services hero band (e.g. ``24/7`` → ``Patient Support``)."""

    value: str
    label: str


class HeroSlide(BaseModel):
    """A single slide for the services hero carousel."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    background_image: Optional[ImageAsset] = None
    order: int = 0


class ServicesHero(BaseModel):
    """Editable content for the Services page hero section."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    background_image: Optional[ImageAsset] = None
    stats: List[HeroStat] = Field(default_factory=list)
    slides: List[HeroSlide] = Field(default_factory=list)


class HomeHeroStat(BaseModel):
    """A single stat displayed in the home hero section (e.g. 100 + Verified Caregivers)."""

    value: int = 0
    suffix: str = ""
    label: str = ""


class HomeHero(BaseModel):
    """Editable content for the Home page hero section."""

    trust_badge_text: Optional[str] = "Trusted by 5,000+"
    trust_badge_quote: Optional[str] = '"Their nursing staff is extremely professional and compassionate. Highly recommended!"'
    trust_badge_avatars: List[ImageAsset] = Field(default_factory=list)
    slider_images: List[ImageAsset] = Field(default_factory=list)
    stats: List[HomeHeroStat] = Field(default_factory=list)


class ValueItem(BaseModel):
    """A title/body pair used for about-page values and similar sections."""
    title: str
    body: str


class TeamTile(BaseModel):
    """A single tile in the professionals / team section."""
    image: Optional[str] = None
    count: str = ""
    title: str = ""
    desc: str = ""


class CareTeamSlide(BaseModel):
    """A single slide in the care-team stacked-card carousel."""
    image: Optional[str] = None
    eyebrow: str = ""
    title: str = ""
    description: str = ""
    button_text: str = ""
    button_link: str = "/booking"
    stats: List[HeroStat] = Field(default_factory=list)


class WhyChooseItem(BaseModel):
    """A single card in the 'Why Choose Nupun' section."""
    title: str = ""
    detail: str = ""


class HomeAboutFeature(BaseModel):
    """A single feature item in the Home About section (e.g. ICU at Home)."""
    title: str = ""
    description: str = ""
    icon: str = "heart-pulse"  # icon key: heart-pulse | shield-check | clock


class HomeAboutTile(BaseModel):
    """A single image card in the Home About section (e.g. 120+ Registered Nurses)."""
    image: Optional[str] = None
    count: str = ""
    title: str = ""
    description: str = ""
    cta_label: str = ""
    cta_link: str = "/booking"


class LegalSection(BaseModel):
    """A single section of a legal page (privacy, terms, refund)."""
    title: str = ""
    body: str = ""


class WebsiteSettings(TimestampedDocument):
    """Global website / brand settings."""

    website_name: str = "Nupun Home Health Care Services"
    tagline: Optional[str] = None
    logo: Optional[ImageAsset] = None
    favicon: Optional[ImageAsset] = None

    theme_primary: Optional[str] = None
    theme_accent: Optional[str] = None

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    google_map_embed: Optional[str] = None
    google_reviews_link: Optional[str] = None

    working_hours: List[WorkingHour] = Field(default_factory=list)

    services_hero: Optional[ServicesHero] = None
    home_hero: Optional[HomeHero] = None

    # ── Home page hero ──────────────────────────────────────
    hero_headline: Optional[str] = None
    hero_subtitle: Optional[str] = None
    hero_description: Optional[str] = None
    hero_image: Optional[ImageAsset] = None
    hero_stats: List[HeroStat] = Field(default_factory=list)

    # ── About page ──────────────────────────────────────────
    about_hero_badge: Optional[str] = None
    about_hero_title: Optional[str] = None
    about_hero_description: Optional[str] = None
    about_hero_image: Optional[ImageAsset] = None
    about_hero_stats: List[HeroStat] = Field(default_factory=list)
    about_story_title: Optional[str] = None
    about_story_text: Optional[str] = None
    about_stats: List[HeroStat] = Field(default_factory=list)
    about_values: List[ValueItem] = Field(default_factory=list)
    about_commitments: List[str] = Field(default_factory=list)
    about_welcome_title: Optional[str] = None
    about_welcome_description: Optional[str] = None
    about_welcome_image: Optional[ImageAsset] = None

    # ── Home About section ───────────────────────────────────
    home_about_heading: Optional[str] = None
    home_about_description: Optional[str] = None
    home_about_features: List[HomeAboutFeature] = Field(default_factory=list)
    home_about_tiles: List[HomeAboutTile] = Field(default_factory=list)

    # ── Reusable content sections ───────────────────────────
    how_it_works_steps: List[ValueItem] = Field(default_factory=list)
    team_tiles: List[TeamTile] = Field(default_factory=list)
    care_team_slides: List[CareTeamSlide] = Field(default_factory=list)
    trust_bar_items: List[str] = Field(default_factory=list)
    why_choose_items: List[WhyChooseItem] = Field(default_factory=list)
    conditions_list: List[str] = Field(default_factory=list)

    # ── Footer ──────────────────────────────────────────────
    footer_tagline: Optional[str] = None
    footer_description: Optional[str] = None
    footer_image: Optional[str] = None

    # ── Contact CTA ─────────────────────────────────────────
    cta_title: Optional[str] = None
    cta_description: Optional[str] = None

    # ── Legal pages ─────────────────────────────────────────
    privacy_sections: List[LegalSection] = Field(default_factory=list)
    terms_sections: List[LegalSection] = Field(default_factory=list)
    refund_sections: List[LegalSection] = Field(default_factory=list)

    is_active: bool = True

    class Settings:
        name = "website_settings"


class SocialLinks(TimestampedDocument):
    """Social media profile links."""

    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    twitter: Optional[str] = None
    whatsapp: Optional[str] = None

    class Settings:
        name = "social_links"


class SEOSettings(TimestampedDocument):
    """Per-page (or global) SEO configuration.

    ``page_key`` identifies the page the settings apply to (e.g. ``home``,
    ``services``, ``global``).
    """

    page_key: str = "global"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None

    class Settings:
        name = "seo_settings"
