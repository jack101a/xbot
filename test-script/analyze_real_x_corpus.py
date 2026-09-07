import json
import re
import statistics
import os

CORPUS_PATH = "data/real_x_timeline_deep_corpus.json"

with open(CORPUS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

posts = data.get("standalone_and_quote_posts", [])
comments = data.get("replies_and_comments", [])

total_items = len(posts) + len(comments)

EMOJI_PATTERN = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2705\u2728\u274c\u27a1\U0001f300-\U0001f9ff]")
TRAILING_EMOJI_PATTERN = re.compile(r"[\s\u200b]*[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2705\u2728\u274c\u27a1\U0001f300-\U0001f9ff]+[\s\u200b]*$")


def analyze_collection(items, name="Posts"):
    char_lens = [p["char_count"] for p in items if p.get("text")]
    word_lens = [p["word_count"] for p in items if p.get("text")]
    has_double_nl = [1 for p in items if "\n\n" in p.get("text", "")]
    has_single_nl = [1 for p in items if "\n" in p.get("text", "") and "\n\n" not in p.get("text", "")]
    zero_nl = [1 for p in items if "\n" not in p.get("text", "")]

    zero_emoji = 0
    trailing_emoji = 0
    inline_emoji = 0
    total_emojis = 0

    for p in items:
        txt = p.get("text", "")
        emojis = EMOJI_PATTERN.findall(txt)
        total_emojis += len(emojis)
        if len(emojis) == 0:
            zero_emoji += 1
        elif TRAILING_EMOJI_PATTERN.search(txt):
            trailing_emoji += 1
        else:
            inline_emoji += 1

    # Length buckets
    b_under_50 = sum(1 for c in char_lens if c < 50)
    b_50_120 = sum(1 for c in char_lens if 50 <= c < 120)
    b_120_200 = sum(1 for c in char_lens if 120 <= c < 200)
    b_200_280 = sum(1 for c in char_lens if 200 <= c <= 280)
    b_over_280 = sum(1 for c in char_lens if c > 280)

    n = len(char_lens) if char_lens else 1

    print(f"\n=================== {name.upper()} (N = {len(items)}) ===================")
    print(f"Character Length: Mean={statistics.mean(char_lens):.1f} | Median={statistics.median(char_lens)} | Min={min(char_lens)} | Max={max(char_lens)}")
    print(f"Word Count:       Mean={statistics.mean(word_lens):.1f} | Median={statistics.median(word_lens)}")
    print(f"Length Buckets:")
    print(f"  < 50 chars (Micro/Reaction):  {b_under_50} ({b_under_50/n*100:.1f}%)")
    print(f"  50-120 chars (Short Take):    {b_50_120} ({b_50_120/n*100:.1f}%)")
    print(f"  120-200 chars (Punchy Block): {b_120_200} ({b_120_200/n*100:.1f}%)")
    print(f"  200-280 chars (Standard):     {b_200_280} ({b_200_280/n*100:.1f}%)")
    print(f"  > 280 chars (Long/Premium):   {b_over_280} ({b_over_280/n*100:.1f}%)")
    print(f"Line Break Distribution:")
    print(f"  Zero Line Breaks (Single-line): {len(zero_nl)} ({len(zero_nl)/n*100:.1f}%)")
    print(f"  Double Breaks (\\n\\n Scannable): {len(has_double_nl)} ({len(has_double_nl)/n*100:.1f}%)")
    print(f"  Single Breaks (\\n only):        {len(has_single_nl)} ({len(has_single_nl)/n*100:.1f}%)")
    print(f"Emoji Distribution:")
    print(f"  Zero Emojis (Clean text):       {zero_emoji} ({zero_emoji/n*100:.1f}%)")
    print(f"  Inline Emojis (Natural flow):   {inline_emoji} ({inline_emoji/n*100:.1f}%)")
    print(f"  Trailing Emoji Dump:            {trailing_emoji} ({trailing_emoji/n*100:.1f}%)")


analyze_collection(posts, "All Scraped Standalone & Quote Posts")
analyze_collection(comments, "All Scraped Replies & Comment Threads")

# Breakdown by Source / Creator
feeds = {}
for p in posts:
    f = p.get("feed", "other")
    feeds.setdefault(f, []).append(p)

print("\n=================== BREAKDOWN BY CREATOR & FEED ===================")
for f_name, f_posts in feeds.items():
    c_lens = [p["char_count"] for p in f_posts]
    zero_em = sum(1 for p in f_posts if not EMOJI_PATTERN.findall(p.get("text", "")))
    double_nl = sum(1 for p in f_posts if "\n\n" in p.get("text", ""))
    print(f"\nFeed: {f_name} (N={len(f_posts)})")
    print(f"  Avg Chars: {statistics.mean(c_lens):.1f} | Avg Words: {statistics.mean([p['word_count'] for p in f_posts]):.1f}")
    print(f"  Zero Emojis: {zero_em}/{len(f_posts)} ({zero_em/len(f_posts)*100:.1f}%) | \\n\\n Double Breaks: {double_nl}/{len(f_posts)} ({double_nl/len(f_posts)*100:.1f}%)")
    print("  Sample Real Tweets:")
    for sample in f_posts[:3]:
        escaped = sample['text'].replace('\n', ' [\\n] ')
        print(f"    - @{sample['author']}: \"{escaped[:110]}...\" ({sample['char_count']}c)")

