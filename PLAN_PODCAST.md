# BSB Bible Audiobook - Podcast Distribution Plan

## Goal

Generate a full Bible audiobook (BSB translation) using ElevenLabs TTS (Bill voice)
and distribute as a single podcast with seasons-per-book via RSS to
YouTube Music, Spotify, Apple Podcasts, and more.

## Architecture

```
BSB JSONL
  |
  v
[1. TTS Generation] -- per-verse MP3 --> ffmpeg concat --> per-chapter MP3
  |
  v
output/elevenlabs_audio/
  <book_slug>/
    chapter_01/
      <book>_chapter_01.mp3       (final chapter audio)
      <book>_chapter_01.mp4       (YouTube video with cover art)
      verse_0000.mp3              (individual verse fragments)
      .checkpoint.json            (resume state)
    chapter_02/
      ...
  |
  v
[2. Static Hosting] -- upload MP3s --> Arweave / S3 / R2
  |
  v
[3. RSS Feed Generation] -- single feed, seasons = books --> podcast.xml
  |
  v
[4. Submit RSS once] --> YouTube Music, Spotify, Apple Podcasts
```

## Podcast Structure: Single Show, Seasons Per Book

One podcast ("The BSB Bible Audiobook") with 66 seasons.
Each season is a book; each episode is a chapter.

```
The BSB Bible Audiobook
  Season 1: Genesis        (50 episodes)
  Season 2: Exodus         (40 episodes)
  ...
  Season 20: Proverbs      (31 episodes)
  ...
  Season 66: Revelation    (22 episodes)
```

- One RSS feed, one submission per platform
- Apple Podcasts and Spotify display seasons natively
- YouTube Music shows it as one show with seasonal grouping
- Episodes are sequential within each season (chapter order)
- Uses `<itunes:season>` and `<itunes:episode>` tags

## Phase 1: TTS Generation (scripts/generate_elevenlabs_audio.py)

**Status:** Script written, needs ffmpeg + test run

- API: ElevenLabs TTS (`xi-api-key` auth)
- Voice: Bill (`pqHfZKP75CvOlQylNhV4`)
- Model: `eleven_v3`
- Output: per-chapter MP3, per-book folders
- Features:
  - Per-verse generation (resumable via checkpoint)
  - ffmpeg concat with 400ms silence between verses
  - Optional MP4 creation with cover art for YouTube
  - ID3 metadata embedding
  - Dry-run mode for cost estimation

**Commands:**
```bash
# Single book
python scripts/generate_elevenlabs_audio.py \
  --api-key sk_... --book Jonah --cover assets/cover.png

# Dry run (cost estimate)
python scripts/generate_elevenlabs_audio.py \
  --api-key sk_... --book Proverbs --dry-run

# Entire Bible
python scripts/generate_elevenlabs_audio.py \
  --api-key sk_... --all --cover assets/cover.png
```

**Output structure:**
```
output/elevenlabs_audio/
  jonah/
    chapter_01/
      jonah_chapter_01.mp3
      jonah_chapter_01.mp4
      verse_0000.mp3
      .checkpoint.json
    chapter_02/ ...
  proverbs/
    chapter_01/ ...
```

**Credit budget:**
- Full Bible: ~3.1M characters
- Current balance: ~113K credits
- Estimated cost: ~3.1M credits (need to top up or use Creator monthly allotment)

## Phase 2: Static Hosting

**Options (in priority order):**

1. **Arweave** (permanent, already used in repo)
   - Upload via `arweave upload <file>` or SDK
   - URLs: `https://arweave.net/<tx-id>`
   - Cost: ~$2-5 for ~2GB total
   - Pro: permanent, no recurring fees

2. **Cloudflare R2** (cheap, fast CDN)
   - `rclone copy output/ r2:bsb-audio/`
   - URLs: `https://pub-xxx.r2.dev/<book>/<chapter>.mp3`

3. **GitHub Releases** (free, up to 2GB per file)
   - Attach MP3s as release assets

**Decision needed:** Which host? Arweave is simplest given existing tooling.

## Phase 3: RSS Feed Generation (scripts/generate_podcast_rss.py)

**Status:** Not yet built

Generates a single podcast RSS 2.0 feed with iTunes season/episode tags:

```xml
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>The BSB Bible Audiobook</title>
    <description>The complete Berean Standard Bible, narrated by AI.
    Organized by book as seasons, chapters as episodes.</description>
    <itunes:author>Crafted BSB Bible</itunes:author>
    <itunes:image href="https://host/cover.png" />
    <itunes:category text="Religion &amp; Spirituality" />
    <item>
      <title>Genesis - Chapter 1</title>
      <itunes:season>1</itunes:season>
      <itunes:episode>1</itunes:episode>
      <enclosure url="https://host/genesis/chapter_01.mp3" length="1234567" type="audio/mpeg" />
      <itunes:duration>180</itunes:duration>
      <guid>bsb-genesis-001</guid>
      <pubDate>Wed, 25 Jun 2025 00:00:00 GMT</pubDate>
    </item>
    ...
    <item>
      <title>Proverbs - Chapter 1</title>
      <itunes:season>20</itunes:season>
      <itunes:episode>1</itunes:episode>
      ...
    </item>
  </channel>
</rss>
```

**Season mapping (canonical Bible book order):**
```
Season  1: Genesis         Season 24: Obadiah
Season  2: Exodus          Season 25: Jonah
Season  3: Leviticus       Season 26: Micah
...
Season 20: Proverbs        Season 40: Matthew
Season 21: Ecclesiastes    Season 41: Mark
...
```

**Commands:**
```bash
# Generate the single podcast feed
python scripts/generate_podcast_rss.py \
  --audio-dir output/elevenlabs_audio \
  --base-url https://arweave.net/bsb-audio \
  --output output/rss/podcast.xml
```

## Phase 4: Distribution Submission

**One-time setup, one RSS URL:**

| Platform | Method | Requirement |
|----------|--------|-------------|
| YouTube Music | YT Studio > Podcasts > New > RSS URL | Google account |
| Spotify | podcasters.spotify.com > Submit RSS | Spotify account |
| Apple Podcasts | podcastsconnect.apple.com > Add Show | Apple ID |

All platforms auto-ingest new episodes when the RSS feed updates.

## Phase 5: Automation (optional, later)

- GitHub Action to auto-generate new books as credits allow
- Auto-upload to Arweave on generation
- Auto-update RSS feed
- Scheduled releases (drip chapters weekly)

## Cover Art

- Need 3000x3000px PNG (one main cover, optionally per-season variants)
- Could use `scripts/imagegen` skill or source externally
- Must include: "The BSB Bible Audiobook", narrator credit

## TODO

- [ ] Install ffmpeg (`brew install ffmpeg`)
- [ ] Test TTS pipeline on Jonah (4 chapters)
- [ ] Verify audio quality and pacing
- [ ] Decide on hosting (Arweave vs R2)
- [ ] Build `scripts/generate_podcast_rss.py` (single feed, seasons)
- [ ] Generate cover art
- [ ] Test RSS feed validity (castfeedvalidator.com)
- [ ] Submit RSS to YouTube, Spotify, Apple
- [ ] Estimate full Bible credit cost and top up balance
