#!/usr/bin/env python3
"""
Convert raw Slack capture JSON into Slack Admin Export ZIP format.

Usage:
    python convert_to_export.py <input_json> [--output <output_zip>] [--channel <channel_name>]

Input:  JSON file downloaded from the browser capture (03_collect_and_download.js)
Output: ZIP file matching Slack Admin Export format, compatible with ChiefOps ingestion

The output ZIP contains:
  users.json          - User directory
  channels.json       - Channel metadata
  <channel>/          - Folder per channel
    YYYY-MM-DD.json   - Messages grouped by date
"""

import json
import zipfile
import sys
import os
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
import argparse


def convert_to_export(input_path: str, output_path: str, channel_name: str = None):
    """Convert captured Slack data to Admin Export ZIP format."""

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("_meta", {})
    messages = data.get("messages", [])
    users = data.get("users", [])

    if not messages:
        print("Error: No messages found in input file.")
        sys.exit(1)

    # ---- Determine channel name ----
    if not channel_name:
        channel_name = meta.get("channel_name", "unknown-channel")

    channel_name = channel_name.lstrip("#").replace(" ", "-").lower()
    channel_id = meta.get("channel_id")

    print(f"Channel:  #{channel_name}")
    print(f"Messages: {len(messages)}")
    print(f"Users:    {len(users)}")
    print()

    # ---- Sort messages by timestamp ----
    messages.sort(key=lambda m: float(m.get("ts", "0")))

    # ---- Group messages by date ----
    messages_by_date: dict[str, list] = defaultdict(list)
    for msg in messages:
        try:
            ts = float(msg.get("ts", "0"))
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")
            messages_by_date[date_str].append(msg)
        except (ValueError, TypeError, OSError):
            messages_by_date["unknown-date"].append(msg)

    # ---- Build users.json ----
    users_export = []
    seen_user_ids: set[str] = set()

    for user in users:
        uid = user.get("id", "")
        if uid and uid not in seen_user_ids:
            seen_user_ids.add(uid)
            users_export.append(
                {
                    "id": uid,
                    "team_id": user.get("team_id", ""),
                    "name": user.get("name", ""),
                    "deleted": user.get("deleted", False),
                    "real_name": user.get(
                        "real_name", user.get("profile", {}).get("real_name", "")
                    ),
                    "profile": user.get("profile", {}),
                    "is_bot": user.get("is_bot", False),
                    "is_admin": user.get("is_admin", False),
                    "updated": user.get("updated", 0),
                }
            )

    # Extract user info from messages for users not in the users list
    for msg in messages:
        uid = msg.get("user", "")
        if uid and uid not in seen_user_ids:
            seen_user_ids.add(uid)
            profile = msg.get("user_profile", {})
            users_export.append(
                {
                    "id": uid,
                    "name": profile.get("name", uid),
                    "real_name": profile.get("real_name", profile.get("display_name", "")),
                    "profile": profile,
                    "deleted": False,
                    "is_bot": msg.get("bot_id") is not None,
                }
            )

    # ---- Build channels.json ----
    channels_export = [
        {
            "id": channel_id or f"C_{channel_name.upper()[:8]}",
            "name": channel_name,
            "created": int(float(messages[0].get("ts", "0"))) if messages else 0,
            "creator": messages[0].get("user", "") if messages else "",
            "is_archived": False,
            "is_general": channel_name == "general",
            "members": list(seen_user_ids),
            "topic": {"value": ""},
            "purpose": {"value": f"Exported channel: {channel_name}"},
        }
    ]

    # ---- Write ZIP ----
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # users.json at root
        zf.writestr("users.json", json.dumps(users_export, indent=2, ensure_ascii=False))

        # channels.json at root
        zf.writestr(
            "channels.json", json.dumps(channels_export, indent=2, ensure_ascii=False)
        )

        # Messages grouped by date in channel folder
        for date_str, day_messages in sorted(messages_by_date.items()):
            file_path = f"{channel_name}/{date_str}.json"
            zf.writestr(
                file_path, json.dumps(day_messages, indent=2, ensure_ascii=False)
            )

    # ---- Summary ----
    date_range = sorted(messages_by_date.keys())
    print(f"Export written: {output_path}")
    print(f"  Date range:          {date_range[0]} to {date_range[-1]}")
    print(f"  Days with messages:  {len(messages_by_date)}")
    print(f"  Total messages:      {len(messages)}")
    print(f"  Total users:         {len(users_export)}")
    print()
    print("This ZIP is compatible with ChiefOps Slack Admin Export ingestion (slack_admin.py).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert captured Slack data to Admin Export ZIP format"
    )
    parser.add_argument("input", help="Path to captured JSON file")
    parser.add_argument(
        "--output",
        "-o",
        help="Output ZIP path (default: slack-export.zip)",
        default="slack-export.zip",
    )
    parser.add_argument(
        "--channel",
        "-c",
        help="Channel name override (auto-detected from capture data if not provided)",
    )

    args = parser.parse_args()
    convert_to_export(args.input, args.output, args.channel)
