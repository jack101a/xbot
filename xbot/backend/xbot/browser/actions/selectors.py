# X (Twitter) DOM selectors repository
# Stored here to allow quick hot-swapping if X updates their DOM structure.

SELECTORS = {
    # Feed & Navigation
    "tweet": '[data-testid="tweet"]',
    "tweet_text": '[data-testid="tweetText"]',
    "search_input": '[data-testid="SearchBox_Search_Input"]',
    
    # Engagement Buttons
    "like_button": '[data-testid="like"]',
    "unlike_button": '[data-testid="unlike"]',
    "retweet_button": '[data-testid="retweet"]',
    "retweet_confirm": '[data-testid="retweetConfirm"]',
    "reply_button": '[data-testid="reply"]',
    
    # Compose & Posting
    "nav_post_button": '[data-testid="SideNav_NewTweet_Button"]',
    "tweet_textarea": '[data-testid="tweetTextarea_0"]',
    # Main post submit button
    "tweet_submit_button": '[data-testid="tweetButton"]',
    # Inline reply submit button
    "inline_tweet_submit_button": '[data-testid="tweetButtonInline"]',
    
    # Profile & Following
    # Follow button on profile
    "profile_follow_button": '[data-testid="placementTracking"]',
    "profile_avatar": '[data-testid="UserAvatar-Container-profileUser"]',
}
