from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.ai.trend_radar import TrendItem, fetch_rss_trends


from datetime import datetime, timezone, timedelta

_now = datetime.now(timezone.utc)
_d1 = (_now - timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
_d2 = (_now - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
_d3 = (_now - timedelta(days=3)).strftime("%a, %d %b %Y %H:%M:%S GMT")
_iso1 = (_now - timedelta(days=1)).isoformat()
_iso2 = (_now - timedelta(days=2)).isoformat()

# Sample RSS 2.0 XML Feed
SAMPLE_RSS_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech Chronicle</title>
    <link>https://techchronicle.example.com</link>
    <description>The latest in technology and AI</description>
    <item>
      <title>Breakthrough in Autonomous AI Agents</title>
      <link>https://techchronicle.example.com/posts/ai-breakthrough</link>
      <description>Researchers demonstrate multi-agent coordination reaching new milestones.</description>
      <pubDate>{_d1}</pubDate>
      <guid>https://techchronicle.example.com/posts/ai-breakthrough</guid>
    </item>
    <item>
      <title>PostgreSQL 19 Query Optimization Features</title>
      <link>https://techchronicle.example.com/posts/pg-19-optimization</link>
      <description>Deep dive into modern indexing techniques and distributed storage.</description>
      <pubDate>{_d2}</pubDate>
    </item>
    <item>
      <title>Quantum Computing Advances in Cryptography</title>
      <link>https://techchronicle.example.com/posts/quantum-crypto</link>
      <description>Post-quantum algorithms standardized across major protocols.</description>
      <pubDate>{_d3}</pubDate>
    </item>
  </channel>
</rss>
"""

# Sample Atom 1.0 XML Feed with namespaces
SAMPLE_ATOM_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>DevOps &amp; Infrastructure Wire</title>
  <link href="https://devopswire.example.com" rel="alternate"/>
  <updated>{_iso1}</updated>
  <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
  <entry>
    <title>Kubernetes v1.35 Released with Native GPU Slicing</title>
    <link href="https://devopswire.example.com/k8s-1-35" rel="alternate" type="text/html"/>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <published>{_iso1}</published>
    <summary>Kubernetes 1.35 introduces out-of-the-box support for fractional GPU allocation in AI clusters.</summary>
  </entry>
  <entry>
    <title>Rust Web Framework Benchmark 2026</title>
    <link href="https://devopswire.example.com/rust-benchmarks-2026"/>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6b</id>
    <updated>{_iso2}</updated>
    <content type="html"><![CDATA[<p>Axum and Actix performance compared under heavy concurrent loads.</p>]]></content>
  </entry>
</feed>
"""


def test_trend_item_model_valid() -> None:
    item = TrendItem(
        id="hash123",
        title="OpenAI announces new reasoning model",
        summary="A new frontier model optimized for coding and math.",
        source_url="https://openai.example.com/news",
        source_name="OpenAI Blog",
        published_at="2026-08-18T12:00:00Z",
    )
    assert item.id == "hash123"
    assert item.title == "OpenAI announces new reasoning model"
    assert item.summary == "A new frontier model optimized for coding and math."
    assert item.source_url == "https://openai.example.com/news"
    assert item.source_name == "OpenAI Blog"
    assert item.published_at == "2026-08-18T12:00:00Z"


def test_trend_item_model_defaults() -> None:
    item = TrendItem(
        id="hash456",
        title="Minimal Trend Item",
        source_url="https://example.com/item",
    )
    assert item.summary == ""
    assert item.source_name == "RSS"
    assert item.published_at is None


def test_trend_item_validation_error() -> None:
    with pytest.raises(ValidationError):
        # Missing required source_url and id
        TrendItem.model_validate({"title": "Invalid Item"})


@pytest.mark.asyncio
async def test_fetch_rss_2_0_parsing() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_RSS_XML
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    items = await fetch_rss_trends(
        feed_urls=["https://techchronicle.example.com/feed.xml"],
        max_items_per_feed=5,
        client=mock_client,
    )

    assert len(items) == 3
    first = items[0]
    assert first.title == "Breakthrough in Autonomous AI Agents"
    assert first.source_url == "https://techchronicle.example.com/posts/ai-breakthrough"
    assert "multi-agent coordination" in first.summary
    assert first.source_name == "Tech Chronicle"
    assert first.published_at == _d1
    assert len(first.id) > 0


@pytest.mark.asyncio
async def test_fetch_atom_1_0_parsing() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_ATOM_XML
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    items = await fetch_rss_trends(
        feed_urls=["https://devopswire.example.com/atom.xml"],
        max_items_per_feed=5,
        client=mock_client,
    )

    assert len(items) == 2
    first = items[0]
    assert first.title == "Kubernetes v1.35 Released with Native GPU Slicing"
    assert first.source_url == "https://devopswire.example.com/k8s-1-35"
    assert "fractional GPU allocation" in first.summary
    assert first.source_name == "DevOps & Infrastructure Wire"
    assert first.published_at == _iso1

    second = items[1]
    assert second.title == "Rust Web Framework Benchmark 2026"
    assert second.source_url == "https://devopswire.example.com/rust-benchmarks-2026"
    assert "Axum and Actix" in second.summary
    assert second.published_at == _iso2


@pytest.mark.asyncio
async def test_keyword_filtering() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_RSS_XML
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    # Filter for AI keywords
    ai_items = await fetch_rss_trends(
        feed_urls=["https://techchronicle.example.com/feed.xml"],
        keywords=["AI", "autonomous"],
        client=mock_client,
    )
    assert len(ai_items) == 1
    assert ai_items[0].title == "Breakthrough in Autonomous AI Agents"

    # Filter for Database keywords
    db_items = await fetch_rss_trends(
        feed_urls=["https://techchronicle.example.com/feed.xml"],
        keywords=["postgresql", "indexing"],
        client=mock_client,
    )
    assert len(db_items) == 1
    assert db_items[0].title == "PostgreSQL 19 Query Optimization Features"

    # Filter with unmatched keyword
    none_items = await fetch_rss_trends(
        feed_urls=["https://techchronicle.example.com/feed.xml"],
        keywords=["blockchain", "solana"],
        client=mock_client,
    )
    assert len(none_items) == 0


@pytest.mark.asyncio
async def test_max_items_per_feed() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_RSS_XML
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    items = await fetch_rss_trends(
        feed_urls=["https://techchronicle.example.com/feed.xml"],
        max_items_per_feed=2,
        client=mock_client,
    )
    assert len(items) == 2


@pytest.mark.asyncio
async def test_network_error_resilience() -> None:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Failed to connect"))

    # Should not raise, should return empty list
    items = await fetch_rss_trends(
        feed_urls=["https://unreachable-feed.example.com/feed.xml"],
        client=mock_client,
    )
    assert items == []


@pytest.mark.asyncio
async def test_http_status_error_resilience() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("500 Server Error", request=MagicMock(), response=mock_response))
    mock_client.get = AsyncMock(return_value=mock_response)

    items = await fetch_rss_trends(
        feed_urls=["https://error-feed.example.com/feed.xml"],
        client=mock_client,
    )
    assert items == []


@pytest.mark.asyncio
async def test_malformed_xml_resilience() -> None:
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Not a valid RSS feed <unclosed tag"
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    items = await fetch_rss_trends(
        feed_urls=["https://malformed-feed.example.com/feed.xml"],
        client=mock_client,
    )
    assert items == []


@pytest.mark.asyncio
async def test_multiple_feeds_aggregation() -> None:
    mock_client = AsyncMock()

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "rss" in url:
            resp.text = SAMPLE_RSS_XML
        else:
            resp.text = SAMPLE_ATOM_XML
        return resp

    mock_client.get = AsyncMock(side_effect=mock_get)

    items = await fetch_rss_trends(
        feed_urls=[
            "https://techchronicle.example.com/rss.xml",
            "https://devopswire.example.com/atom.xml",
        ],
        max_items_per_feed=2,
        client=mock_client,
    )

    # 2 items from first feed + 2 items from second feed
    assert len(items) == 4
    sources = {item.source_name for item in items}
    assert "Tech Chronicle" in sources
    assert "DevOps & Infrastructure Wire" in sources


@pytest.mark.asyncio
async def test_fetch_rss_trends_default_client() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_RSS_XML
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockAsyncClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        MockAsyncClient.return_value.__aenter__.return_value = mock_instance

        items = await fetch_rss_trends(
            feed_urls=["https://example.com/feed.xml"],
        )
        assert len(items) == 3
