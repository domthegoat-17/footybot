FootyBot
FootyBot is an automated football news bot that scans major RSS feeds, detects trending soccer stories, generates short-form scripts using AI, and posts them to Discord — built for YouTube Shorts and TikTok content creation.

Features

Aggregates football news from multiple RSS feeds
Filters out non-soccer content
Detects trending stories across multiple sources
Scores stories using a custom heat score algorithm
Generates single-story scripts with OpenAI
Generates rapid-fire roundup scripts covering transfers, injuries, and drama
Builds a persistent knowledge store of football intel across hourly runs
Knowledge store resets daily at midnight EST for fresh daily content
Prevents duplicate posts using link and topic fingerprint tracking
Posts everything directly to Discord via webhook


Project Structure
footybot/
├── config.py
├── feed_reader.py
├── filters.py
├── script_generator.py
├── script_formatter.py
├── tracker.py
├── discord_post.py
├── knowledge_store.py
├── knowledge_extractor.py
├── main.py
├── roundup.py
├── sources.txt
├── seen_links.txt
└── README.md
File Overview
config.py
Scoring weights, keyword lists, heat score terms, competition bonuses, trend bonuses, and similarity thresholds.
feed_reader.py
Loads RSS feeds and extracts article titles, summaries, and publish times. Falls back to full article scraping when summaries are too short.
filters.py
Handles soccer filtering, heat score calculation, entity extraction, topic similarity detection, and trend grouping.
script_generator.py
Generates a single-story YouTube Shorts script for one article using OpenAI. Opinionated, fast-talking tone with hooks and a closing question.
script_formatter.py
Reformats paragraph-style scripts into YouTube Shorts pacing — one sentence per line with natural pauses.
tracker.py
Prevents duplicate posts using URL tracking and topic fingerprint hashing. Entries expire after 3 days.
knowledge_store.py
Manages knowledge.json — a persistent store of structured intel extracted from every qualifying article. Stores transfers, injuries, and drama only. Resets daily at midnight EST.
knowledge_extractor.py
Makes a lightweight GPT call per article to extract structured intel: category, player, clubs, fee, rumour status, and a one-sentence key fact. Skips anything that isn't a transfer, injury, or on-pitch drama.
discord_post.py
Posts scripts to Discord via webhook. Handles Discord's 2000 character limit by splitting long messages automatically.
main.py
The main bot pipeline. Runs on a loop every hour. Press Ctrl+C to stop.
roundup.py
Generates a rapid-fire roundup script from stored knowledge intel. Run manually whenever you want a new roundup posted.

How It Works
Main Pipeline (runs every hour)
RSS Feeds
   ↓
Article Parsing
   ↓
Soccer Filtering
   ↓
Heat Score Ranking
   ↓
Trend Detection
   ↓
Knowledge Store Population (transfers, injuries, drama)
   ↓
Script Generation — top 3 stories (OpenAI)
   ↓
Discord Posting
   ↓
Duplicate Tracking
Roundup Pipeline (run manually)
knowledge.json
   ↓
Filter by category (transfers / injuries / drama)
   ↓
Build intel block
   ↓
Roundup Script Generation (OpenAI)
   ↓
Discord Posting

Requirements
Python 3.10+
pip install feedparser newspaper3k openai requests

Environment Variables
DISCORD_WEBHOOK_URL=your_webhook_url_here
OPENAI_API_KEY=your_openai_key_here
Store these in a .env file. Make sure .env is in your .gitignore.

Running the Bot
Start the hourly loop:
python main.py
Press Ctrl+C at any time to stop cleanly.
The bot will run immediately on start, then wait 60 minutes between each run. The knowledge store is wiped automatically at midnight EST each day.

Generating a Roundup
Run this manually whenever you want a roundup script posted to Discord:
python roundup.py transfers
python roundup.py injuries
python roundup.py drama
Running without an argument shows what is currently in the knowledge store:
python roundup.py
The roundup script style is rapid-fire and factual — player, situation, clubs interested, fee if known. No opinions, no takes, no sign-off. Built to be read straight to camera.

Knowledge Store
Every article that passes soccer filtering gets classified by GPT into one of three categories:

transfer — signings, bids, loans, rumours, fees
injury — player injuries, doubts, returns
drama — red cards, bans, suspensions, last-minute goals, comebacks

Anything else (previews, press conferences, manager sackings, opinion pieces) is skipped entirely and not stored.
Each entry captures: player name, from/to clubs, fee, rumour status (rumour / advanced / official), and a one-sentence key fact.
The store accumulates across all hourly runs throughout the day, giving the roundup a rich pool to draw from. It resets at midnight EST.

Scoring System
Articles are ranked using a heat score that considers:

breaking news signals
transfer and injury keywords
match drama terms
major competition bonuses
big club bonuses
recency (published within 2 or 6 hours)
trend bonus (same story covered by multiple sources)

Only articles above the heat threshold get a script generated. All qualifying articles still get their intel stored regardless of score.

Author
Dominic
