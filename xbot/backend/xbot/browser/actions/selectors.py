# X (Twitter) DOM selectors repository
# Stored here to allow quick hot-swapping if X updates their DOM structure.

SELECTORS = {
    # Feed & Navigation (Handles both standard data-testid, semantic articles, and virtual scroll cells)
    "tweet": 'article[data-testid="tweet"], [data-testid="tweet"], article[role="article"], [data-testid="cellInnerDiv"]:has([data-testid="tweetText"])',
    "tweet_text": '[data-testid="tweetText"], [data-testid="tweet"] [dir="auto"]',
    "search_input": '[data-testid="SearchBox_Search_Input"], input[aria-label*="Search" i]',
    
    # Engagement Buttons (Handles dynamic testids and localized aria-labels)
    "like_button": '[data-testid="like"], button[aria-label*="Like" i]',
    "unlike_button": '[data-testid="unlike"], button[aria-label*="Liked" i], button[aria-label*="Unlike" i]',
    "retweet_button": '[data-testid="retweet"], button[aria-label*="Repost" i], button[aria-label*="Retweet" i]',
    "retweet_confirm": '[data-testid="retweetConfirm"], [data-testid="Dropdown"] [role="menuitem"]',
    "reply_button": '[data-testid="reply"], button[aria-label*="Reply" i]',
    
    # Compose & Posting
    "nav_post_button": '[data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"], a[href="/compose/tweet"]',
    "tweet_textarea": '[data-testid="tweetTextarea_0"], div[role="textbox"][data-testid*="tweetTextarea"], div[contenteditable="true"][role="textbox"]',
    # Main post submit button
    "tweet_submit_button": '[data-testid="tweetButton"], [data-testid="tweetButtonInline"], button[data-testid*="tweetButton"]',
    # Inline reply submit button
    "inline_tweet_submit_button": '[data-testid="tweetButtonInline"], [data-testid="tweetButton"], button[data-testid*="tweetButton"]',
    
    # Profile & Following
    "profile_follow_button": 'button[aria-label*="Follow @" i], button[data-testid*="-follow"], button[data-testid$="-follow"]',
    "profile_avatar": '[data-testid="UserName"], [data-testid*="UserAvatar"], h2',

    # Poll Selectors
    "poll_button": '[data-testid="pollButton"], [aria-label*="poll" i], [aria-label*="Poll"]',
    "poll_choice_1": '[name="Choice1"], input[name="Choice1"], [data-testid="Choice1"] input',
    "poll_choice_2": '[name="Choice2"], input[name="Choice2"], [data-testid="Choice2"] input',
    "poll_choice_3": '[name="Choice3"], input[name="Choice3"], [data-testid="Choice3"] input',
    "poll_choice_4": '[name="Choice4"], input[name="Choice4"], [data-testid="Choice4"] input',
    "add_choice_button": '[aria-label*="Add choice" i], [data-testid="addChoice"], [aria-label*="choice" i]',

    # GIF Selectors
    "gif_button": 'button[aria-label="Add a GIF"], button[data-testid="gifSearchButton"], [data-testid="gifSearchButton"], button[aria-label*="GIF"], button[aria-label*="gif" i], [data-testid="fileInput"] + div button',
    "gif_search_input": 'input[data-testid="searchBox"], input[data-testid="SearchBox_Search_Input"], input[placeholder*="Search GIFs"], input[placeholder*="Search for GIFs"], input[aria-label*="Search for GIFs"], input[aria-label*="Search GIFs"]',
    "gif_item": '[data-testid="gifItem"], [data-testid="gifSearchResults"] img, [data-testid="gifSearchResults"] [role="button"], [data-testid="gifCategory"], div[role="button"][data-testid*="gif"]',
}

