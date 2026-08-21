from __future__ import annotations

import logging
import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
@app.get("/home", response_class=HTMLResponse)
async def home_feed() -> str:
    return """<!DOCTYPE html>
<html>
<head>
    <title>Mock X Feed</title>
    <style>
        body {
            font-family: sans-serif;
            background: #000;
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        .tweet {
            border-bottom: 1px solid #333;
            padding: 15px;
            margin-bottom: 10px;
        }
        .buttons {
            margin-top: 10px;
            display: flex;
            gap: 20px;
        }
        button {
            background: none;
            border: none;
            color: #888;
            cursor: pointer;
        }
        #compose-modal, #retweet-confirm-modal {
            display: none;
            position: fixed;
            top: 20%;
            left: 30%;
            background: #222;
            border: 1px solid #444;
            padding: 20px;
            z-index: 100;
            width: 40%;
        }
        #modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 50;
        }
    </style>
</head>
<body>
    <div style="display: flex;">
        <!-- Sidebar -->
        <div style="width: 200px;">
            <button
                data-testid="SideNav_NewTweet_Button"
                id="nav-post-btn"
                style="background: #1d9bf0; color: white; padding: 10px 20px;
                       border-radius: 20px; font-weight: bold;"
            >
                Post
            </button>
        </div>
        <!-- Feed -->
        <div id="feed" style="flex-grow: 1; max-width: 600px;
             border-left: 1px solid #333; border-right: 1px solid #333;
             padding-left: 20px;">
            <h2>Home Feed</h2>
            <div class="tweet" data-testid="tweet">
                <div data-testid="tweetText">
                    This is a mock tweet about async Python and testing.
                </div>
                <div class="buttons">
                    <button data-testid="reply" class="reply-btn">Reply</button>
                    <button data-testid="retweet" class="retweet-btn">Retweet</button>
                    <button data-testid="like" class="like-btn">Like</button>
                </div>
            </div>
            <div class="tweet" data-testid="tweet">
                <div data-testid="tweetText">
                    Playwright is very powerful for browser automation!
                </div>
                <div class="buttons">
                    <button data-testid="reply" class="reply-btn">Reply</button>
                    <button
                        data-testid="retweet"
                        class="retweet-btn"
                    >
                        Retweet
                    </button>
                    <button data-testid="like" class="like-btn">Like</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <div id="modal-overlay"></div>
    <div id="compose-modal">
        <h3>Compose Post</h3>
        <textarea
            data-testid="tweetTextarea_0"
            id="tweet-text"
            rows="4"
            style="width: 100%; background: #333; color: white;
                   border: 1px solid #444; padding: 10px;"
        ></textarea>
        <br/><br/>
        <button
            data-testid="tweetButton"
            id="submit-post-btn"
            style="background: #1d9bf0; color: white;
                   padding: 8px 16px; border-radius: 16px;"
        >
            Post
        </button>
        <button id="close-compose-btn">Cancel</button>
    </div>

    <div id="retweet-confirm-modal">
        <h3>Retweet this post?</h3>
        <button
            data-testid="retweetConfirm"
            id="confirm-rt-btn"
            style="background: #1d9bf0; color: white;
                   padding: 8px 16px; border-radius: 16px;"
        >
            Retweet
        </button>
        <button id="cancel-rt-btn">Cancel</button>
    </div>

    <script>
        const composeModal = document.getElementById('compose-modal');
        const retweetModal = document.getElementById('retweet-confirm-modal');
        const overlay = document.getElementById('modal-overlay');
        const feed = document.getElementById('feed');

        // Navigation Post Button
        document.getElementById('nav-post-btn').addEventListener('click', () => {
            composeModal.style.display = 'block';
            overlay.style.display = 'block';
        });

        // Close Compose Modal
        document.getElementById('close-compose-btn').addEventListener('click', () => {
            composeModal.style.display = 'none';
            overlay.style.display = 'none';
            document.getElementById('tweet-text').value = '';
        });

        // Submit Post Button
        document.getElementById('submit-post-btn').addEventListener('click', () => {
            const text = document.getElementById('tweet-text').value;
            if (text) {
                // Add to top of feed
                const newTweet = document.createElement('div');
                newTweet.className = 'tweet';
                newTweet.setAttribute('data-testid', 'tweet');
                newTweet.innerHTML = `
                    <div data-testid="tweetText">${text}</div>
                    <div class="buttons">
                        <button data-testid="reply" class="reply-btn">Reply</button>
                        <button
                            data-testid="retweet"
                            class="retweet-btn"
                        >
                            Retweet
                        </button>
                        <button data-testid="like" class="like-btn">Like</button>
                    </div>
                `;
                // Insert after the h2 header
                feed.insertBefore(newTweet, feed.children[1]);
            }
            composeModal.style.display = 'none';
            overlay.style.display = 'none';
            document.getElementById('tweet-text').value = '';
        });

        // Dynamic event delegation for Likes, Retweets, Replies
        document.addEventListener('click', (e) => {
            const isLike = e.target.classList.contains('like-btn') ||
                e.target.getAttribute('data-testid') === 'like';
            if (isLike) {
                e.target.setAttribute('data-testid', 'unlike');
                e.target.innerText = 'Liked';
                e.target.style.color = '#f91880';
            } else if (e.target.getAttribute('data-testid') === 'unlike') {
                e.target.setAttribute('data-testid', 'like');
                e.target.innerText = 'Like';
                e.target.style.color = '#888';
            }

            const isRt = e.target.classList.contains('retweet-btn') ||
                e.target.getAttribute('data-testid') === 'retweet';
            if (isRt) {
                retweetModal.style.display = 'block';
                overlay.style.display = 'block';
            }

            const isReply = e.target.classList.contains('reply-btn') ||
                e.target.getAttribute('data-testid') === 'reply';
            if (isReply) {
                composeModal.style.display = 'block';
                overlay.style.display = 'block';
            }
        });

        // Retweet confirmation buttons
        document.getElementById('confirm-rt-btn').addEventListener('click', () => {
            retweetModal.style.display = 'none';
            overlay.style.display = 'none';
        });
        document.getElementById('cancel-rt-btn').addEventListener('click', () => {
            retweetModal.style.display = 'none';
            overlay.style.display = 'none';
        });
    </script>
</body>
</html>"""


@app.get("/search", response_class=HTMLResponse)
async def search_results(q: str = "") -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock Search Results</title>
    <style>
        body {{
            font-family: sans-serif;
            background: #000;
            color: #fff;
            padding: 20px;
        }}
        .tweet {{
            border-bottom: 1px solid #333;
            padding: 15px;
            margin-bottom: 10px;
        }}
        .buttons {{
            margin-top: 10px;
            display: flex;
            gap: 20px;
        }}
        button {{
            background: none;
            border: none;
            color: #888;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <h2>Search Results for: {q}</h2>
    <div id="feed">
        <div class="tweet" data-testid="tweet">
            <div data-testid="tweetText">
                SearchResult: Here is a cool tweet matching {q}!
            </div>
            <div class="buttons">
                <button data-testid="reply" class="reply-btn">Reply</button>
                <button
                    data-testid="retweet"
                    class="retweet-btn"
                >
                    Retweet
                </button>
                <button data-testid="like" class="like-btn">Like</button>
            </div>
        </div>
        <div class="tweet" data-testid="tweet">
            <div data-testid="tweetText">SearchResult: Another match for {q}.</div>
            <div class="buttons">
                <button data-testid="reply" class="reply-btn">Reply</button>
                <button
                    data-testid="retweet"
                    class="retweet-btn"
                >
                    Retweet
                </button>
                <button data-testid="like" class="like-btn">Like</button>
            </div>
        </div>
    </div>
</body>
</html>"""


@app.get("/{username}", response_class=HTMLResponse)
async def profile_page(username: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Mock Profile - {username}</title>
    <style>
        body {{
            font-family: sans-serif;
            background: #000;
            color: #fff;
            padding: 20px;
        }}
        .avatar {{
            width: 100px;
            height: 100px;
            background: #555;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .follow-btn {{
            background: #fff;
            color: #000;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            cursor: pointer;
            border: none;
        }}
    </style>
</head>
<body>
    <div data-testid="UserAvatar-Container-profileUser" class="avatar">
        Avatar
    </div>
    <h2>@{username}</h2>
    <button
        data-testid="placementTracking"
        class="follow-btn"
        id="follow-btn"
    >
        Follow
    </button>

    <script>
        document.getElementById('follow-btn').addEventListener('click', (e) => {{
            if (e.target.innerText === 'Follow') {{
                e.target.innerText = 'Following';
                e.target.style.background = '#000';
                e.target.style.color = '#fff';
                e.target.style.border = '1px solid #555';
            }} else {{
                e.target.innerText = 'Follow';
                e.target.style.background = '#fff';
                e.target.style.color = '#000';
                e.target.style.border = 'none';
            }}
        }});
    </script>
</body>
</html>"""


class ThreadedUvicorn:
    """Runs the mock FastAPI application inside a background thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9999) -> None:
        config = uvicorn.Config(
            app, host=host, port=port, log_level="warning", loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        self.thread.start()
        # Sleep briefly to allow server to start listening
        time.sleep(1.0)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5.0)
