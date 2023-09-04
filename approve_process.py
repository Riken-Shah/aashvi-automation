from utils import send_messages
from automation import approved_non_posted_story, approved_non_posted_instagram_posts


if __name__ == '__main__':
    story = approved_non_posted_story()
    if story >= 2:
        send_messages(f"Hey! You have {story} non approved stories.")
    posts = approved_non_posted_instagram_posts()
    if posts >= 2:
        send_messages(f"Hey! You have {posts} non approved posts.")
