"""Website settings, social links and SEO schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.base import ImageAsset
from app.models.settings import (
    CareTeamSlide,
    CommitmentItem,
    ComprehensiveServiceCard,
    FounderCard,
    HomeAboutFeature,
    HomeAboutTile,
    HomeHero,
    LegalSection,
    ServicesHero,
    TeamTile,
    ValueItem,
    WhyChooseItem,
    WorkingHour,
    HeroStat,
)
from app.schemas.common import IdTimestampSchema

# ---- Website settings ----

class WebsiteSettingsUpdate(BaseModel):
    website_name: Optional[str] = None
    tagline: Optional[str] = None
    logo: Optional[ImageAsset] = None
    favicon: Optional[ImageAsset] = None
    theme_primary: Optional[str] = None
    theme_accent: Optional[str] = None
    font_family: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    google_map_embed: Optional[str] = None
    google_reviews_link: Optional[str] = None
    working_hours: Optional[List[WorkingHour]] = None
    services_hero: Optional[ServicesHero] = None
    home_hero: Optional[HomeHero] = None

    # Home page hero
    hero_headline: Optional[str] = None
    hero_subtitle: Optional[str] = None
    hero_description: Optional[str] = None
    hero_cta_primary_text: Optional[str] = None
    hero_cta_secondary_text: Optional[str] = None
    hero_image: Optional[ImageAsset] = None
    hero_stats: Optional[List[HeroStat]] = None

    # About page
    about_hero_badge: Optional[str] = None
    about_hero_title: Optional[str] = None
    about_hero_description: Optional[str] = None
    about_hero_image: Optional[ImageAsset] = None
    about_hero_stats: Optional[List[HeroStat]] = None
    about_story_title: Optional[str] = None
    about_story_text: Optional[str] = None
    about_stats: Optional[List[HeroStat]] = None
    about_values: Optional[List[ValueItem]] = None
    about_commitments: Optional[List[str]] = None
    commitment_items: Optional[List[CommitmentItem]] = None
    commitment_image: Optional[ImageAsset] = None
    about_founders: Optional[List[FounderCard]] = None
    about_address_name: Optional[str] = None
    about_address_line1: Optional[str] = None
    about_address_line2: Optional[str] = None
    about_map_embed_url: Optional[str] = None
    why_choose_eyebrow: Optional[str] = None
    why_choose_title: Optional[str] = None
    why_choose_description: Optional[str] = None
    commitment_subtitle: Optional[str] = None
    commitment_badge_value: Optional[str] = None
    commitment_badge_label: Optional[str] = None
    about_welcome_title: Optional[str] = None
    about_welcome_description: Optional[str] = None
    about_welcome_image: Optional[ImageAsset] = None

    # Home About section
    home_about_heading: Optional[str] = None
    home_about_description: Optional[str] = None
    home_about_features: Optional[List[HomeAboutFeature]] = None
    home_about_tiles: Optional[List[HomeAboutTile]] = None

    videos_wall_image: Optional[ImageAsset] = None

    # Content sections
    how_it_works_steps: Optional[List[ValueItem]] = None
    team_tiles: Optional[List[TeamTile]] = None
    care_team_slides: Optional[List[CareTeamSlide]] = None
    trust_bar_items: Optional[List[str]] = None
    why_choose_items: Optional[List[WhyChooseItem]] = None
    conditions_list: Optional[List[str]] = None

    # Comprehensive Services
    comprehensive_services_eyebrow: Optional[str] = None
    comprehensive_services_title: Optional[str] = None
    comprehensive_services_description: Optional[str] = None
    comprehensive_services: Optional[List[ComprehensiveServiceCard]] = None

    # Footer
    footer_tagline: Optional[str] = None
    footer_description: Optional[str] = None
    footer_image: Optional[str] = None

    # CTA
    cta_title: Optional[str] = None
    cta_description: Optional[str] = None

    # Legal pages
    privacy_sections: Optional[List[LegalSection]] = None
    terms_sections: Optional[List[LegalSection]] = None
    refund_sections: Optional[List[LegalSection]] = None

class WebsiteSettingsResponse(IdTimestampSchema):
    website_name: str
    tagline: Optional[str] = None
    logo: Optional[ImageAsset] = None
    favicon: Optional[ImageAsset] = None
    theme_primary: Optional[str] = None
    theme_accent: Optional[str] = None
    font_family: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None
    google_map_embed: Optional[str] = None
    google_reviews_link: Optional[str] = None
    working_hours: List[WorkingHour] = Field(default_factory=list)
    services_hero: Optional[ServicesHero] = None
    home_hero: Optional[HomeHero] = None

    # Home page hero
    hero_headline: Optional[str] = None
    hero_subtitle: Optional[str] = None
    hero_description: Optional[str] = None
    hero_cta_primary_text: Optional[str] = None
    hero_cta_secondary_text: Optional[str] = None
    hero_image: Optional[ImageAsset] = None
    hero_stats: List[HeroStat] = Field(default_factory=list)

    # About page
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
    commitment_items: List[CommitmentItem] = Field(default_factory=list)
    commitment_image: Optional[ImageAsset] = None
    about_founders: List[FounderCard] = Field(default_factory=list)
    about_address_name: Optional[str] = None
    about_address_line1: Optional[str] = None
    about_address_line2: Optional[str] = None
    about_map_embed_url: Optional[str] = None
    why_choose_eyebrow: Optional[str] = None
    why_choose_title: Optional[str] = None
    why_choose_description: Optional[str] = None
    commitment_subtitle: Optional[str] = None
    commitment_badge_value: Optional[str] = None
    commitment_badge_label: Optional[str] = None
    about_welcome_title: Optional[str] = None
    about_welcome_description: Optional[str] = None
    about_welcome_image: Optional[ImageAsset] = None

    # Home About section
    home_about_heading: Optional[str] = None
    home_about_description: Optional[str] = None
    home_about_features: List[HomeAboutFeature] = Field(default_factory=list)
    home_about_tiles: List[HomeAboutTile] = Field(default_factory=list)

    videos_wall_image: Optional[ImageAsset] = None

    # Content sections
    how_it_works_steps: List[ValueItem] = Field(default_factory=list)
    team_tiles: List[TeamTile] = Field(default_factory=list)
    care_team_slides: List[CareTeamSlide] = Field(default_factory=list)
    trust_bar_items: List[str] = Field(default_factory=list)
    why_choose_items: List[WhyChooseItem] = Field(default_factory=list)
    conditions_list: List[str] = Field(default_factory=list)

    # Comprehensive Services
    comprehensive_services_eyebrow: Optional[str] = None
    comprehensive_services_title: Optional[str] = None
    comprehensive_services_description: Optional[str] = None
    comprehensive_services: List[ComprehensiveServiceCard] = Field(default_factory=list)

    # Footer
    footer_tagline: Optional[str] = None
    footer_description: Optional[str] = None
    footer_image: Optional[str] = None

    # CTA
    cta_title: Optional[str] = None
    cta_description: Optional[str] = None

    # Legal pages
    privacy_sections: List[LegalSection] = Field(default_factory=list)
    terms_sections: List[LegalSection] = Field(default_factory=list)
    refund_sections: List[LegalSection] = Field(default_factory=list)

# ---- Social links ----

class SocialLinksUpdate(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    whatsapp: Optional[str] = None

class SocialLinksResponse(IdTimestampSchema):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None

# ---- SEO ----

class SEOSettingsUpsert(BaseModel):
    page_key: str = Field("global", min_length=1, max_length=80)
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None

class SEOSettingsResponse(IdTimestampSchema):
    page_key: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    schema_markup: Optional[str] = None
