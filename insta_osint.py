#!/usr/bin/env python3
"""
Advanced Instagram OSINT Tool (Public Profiles Only)
Educational / Lab use
"""

import requests
import argparse
import json
import os
import time
from rich import print
from rich.table import Table

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "X-IG-App-ID": "936619743392459"
}

RATE_DELAY = 2  # seconds between requests


class InstagramOSINT:

    def __init__(self, username, download_photos=False):
        self.username = username
        self.download_photos = download_photos
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.user = None
        self.base_dir = username

    def fetch_profile(self):
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={self.username}"
        r = self.session.get(url, timeout=10)

        if r.status_code != 200:
            raise Exception("Profile not found or blocked")

        self.user = r.json()["data"]["user"]

    def save_profile(self):
        os.makedirs(self.base_dir, exist_ok=True)
        with open(f"{self.base_dir}/profile.json", "w") as f:
            json.dump(self.user, f, indent=2)

    def print_summary(self):
        table = Table(title=f"Instagram OSINT: {self.username}")
        table.add_column("Field")
        table.add_column("Value")

        table.add_row("Full Name", self.user["full_name"])
        table.add_row("Followers", str(self.user["edge_followed_by"]["count"]))
        table.add_row("Following", str(self.user["edge_follow"]["count"]))
        table.add_row("Posts", str(self.user["edge_owner_to_timeline_media"]["count"]))
        table.add_row("Private", str(self.user["is_private"]))
        table.add_row("Verified", str(self.user["is_verified"]))
        table.add_row("Bio", self.user["biography"])
        table.add_row("External URL", str(self.user["external_url"]))

        print(table)

    def download_profile_picture(self):
        r = self.session.get(self.user["profile_pic_url_hd"])
        with open(f"{self.base_dir}/profile_pic.jpg", "wb") as f:
            f.write(r.content)

    def download_posts(self):
        if self.user["is_private"]:
            print("[red]Private account — cannot download posts[/red]")
            return

        media = self.user["edge_owner_to_timeline_media"]
        posts_dir = f"{self.base_dir}/posts"
        os.makedirs(posts_dir, exist_ok=True)

        cursor = None
        has_next = True
        count = 0

        while has_next:
            edges = media["edges"]
            for post in edges:
                node = post["node"]
                count += 1

                img_url = node["display_url"]
                timestamp = node["taken_at_timestamp"]
                caption = node["edge_media_to_caption"]["edges"]

                meta = {
                    "id": node["id"],
                    "shortcode": node["shortcode"],
                    "likes": node["edge_liked_by"]["count"],
                    "comments": node["edge_media_to_comment"]["count"],
                    "timestamp": timestamp,
                    "caption": caption[0]["node"]["text"] if caption else ""
                }

                img_data = self.session.get(img_url).content
                img_path = f"{posts_dir}/{count}.jpg"

                with open(img_path, "wb") as f:
                    f.write(img_data)

                with open(f"{posts_dir}/{count}.json", "w") as f:
                    json.dump(meta, f, indent=2)

                print(f"[green]Downloaded post {count}[/green]")
                time.sleep(RATE_DELAY)

            has_next = media["page_info"]["has_next_page"]
            cursor = media["page_info"]["end_cursor"]

            if has_next:
                next_url = (
                    "https://www.instagram.com/graphql/query/"
                    "?query_hash=69cba40317214236af40e7efa697781d"
                    f"&variables={{\"id\":\"{self.user['id']}\",\"first\":12,\"after\":\"{cursor}\"}}"
                )
                r = self.session.get(next_url)
                media = r.json()["data"]["user"]["edge_owner_to_timeline_media"]
                time.sleep(RATE_DELAY)

        print(f"[bold green]Downloaded {count} posts[/bold green]")

    def run(self):
        self.fetch_profile()
        self.save_profile()
        self.download_profile_picture()
        self.print_summary()

        if self.download_photos:
            self.download_posts()


def main():
    parser = argparse.ArgumentParser(description="Advanced Instagram OSINT Tool")
    parser.add_argument("-u", "--username", required=True, help="Instagram username")
    parser.add_argument("-d", "--download-photos", action="store_true", help="Download public photos")
    args = parser.parse_args()

    try:
        osint = InstagramOSINT(args.username, args.download_photos)
        osint.run()
    except Exception as e:
        print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    main()
