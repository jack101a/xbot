"""
xbot.search.matrix: Search Matrix Strategy for automated campaign research.

Implements structured 4-tier query families for discovering:
  Tier 1: High-Engagement Viral Anchors (for Quote Tweets and KOL Sniping)
  Tier 2: Real-Time Community Pulse & Live Buzz (for Replies and Banter via &f=live)
  Tier 3: Verified Creator Discovery (for Follow Reciprocity & Peer Networking)
  Tier 4: Visual & Media Harvesting (for Posters, Trailers, and Multimodal Vision)
"""

from __future__ import annotations

from xbot.search.query_builder import XSearchQueryBuilder
from xbot.search.types import SearchCategory, SearchTarget


class SearchMatrixStrategy:
    """Factory for standard high-signal search query configurations."""

    @staticmethod
    def create_viral_anchor_query(
        topic: str,
        min_faves: int = 50,
        max_age_days: int = 7,
        require_media: bool = True,
        target: SearchTarget = SearchTarget.WEB,
    ) -> XSearchQueryBuilder:
        """
        Builds a Tier 1 query to find authoritative, high-engagement anchor posts.
        Ideal for Quote Takes and High-Visibility Replies.
        """
        clean_topic = topic.strip().strip('"')
        builder = (
            XSearchQueryBuilder(target=target)
            .exact_phrase(clean_topic) if " " in clean_topic else XSearchQueryBuilder(target=target).keyword(clean_topic)
        )
        return (
            builder
            .min_faves(min_faves)
            .exclude_retweets(True)
            .require_media(require_media)
            .since_days_ago(max_age_days)
            .category(SearchCategory.TOP)
        )

    @staticmethod
    def create_realtime_buzz_query(
        topic: str,
        max_age_days: int = 2,
        target: SearchTarget = SearchTarget.WEB,
    ) -> XSearchQueryBuilder:
        """
        Builds a Tier 2 query to capture real-time community chatter, breaking jokes,
        and unranked live user takes (&f=live).
        """
        clean_topic = topic.strip().strip('"')
        return (
            XSearchQueryBuilder(target=target)
            .keyword(clean_topic)
            .exclude_retweets(True)
            .since_days_ago(max_age_days)
            .category(SearchCategory.LATEST)
        )

    @staticmethod
    def create_verified_creator_query(
        niche: str,
        min_faves: int = 50,
        max_age_days: int = 14,
        target: SearchTarget = SearchTarget.WEB,
    ) -> XSearchQueryBuilder:
        """
        Builds a Tier 3 query to discover blue-tick creators and influential voices
        within a specific niche for reciprocal follow and networking.
        """
        clean_niche = niche.strip().strip('"')
        return (
            XSearchQueryBuilder(target=target)
            .keyword(clean_niche)
            .require_verified(True)
            .min_faves(min_faves)
            .exclude_retweets(True)
            .since_days_ago(max_age_days)
            .category(SearchCategory.TOP)
        )

    @staticmethod
    def create_media_harvester_query(
        topic: str,
        max_age_days: int = 14,
        target: SearchTarget = SearchTarget.WEB,
    ) -> XSearchQueryBuilder:
        """
        Builds a Tier 4 query dedicated to harvesting screenshots, video clips,
        and trailers (&f=media).
        """
        clean_topic = topic.strip().strip('"')
        return (
            XSearchQueryBuilder(target=target)
            .keyword(clean_topic)
            .require_media(True)
            .exclude_retweets(True)
            .since_days_ago(max_age_days)
            .category(SearchCategory.MEDIA)
        )
