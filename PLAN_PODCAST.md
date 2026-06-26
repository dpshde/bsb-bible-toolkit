# BSB Bible Audio - Distribution Plan

## Goal

Generate a full Bible audiobook (BSB translation) using ElevenLabs TTS and
distribute freely. No paywalls, no licensing fees. "Freely you received,
freely give." (Matthew 10:8)

## Why

The Berean Standard Bible is a modern, public-domain (CC0) translation that
proves world-class Bible translation doesn't need to be commercialized.
This project makes it available as audio, chapter by chapter, at no cost.

Learn more about the case for freely-given ministry: sellingjesus.org

## Pipeline

```
BSB JSONL
  |
  v
[1. TTS Generation] -- per-chapter MP3 via ElevenLabs Flash v2.5
  |                    scripts/generate_elevenlabs_audio.py
  v
output/elevenlabs_audio/<book>/<book>_chapter_01.mp3
  |
  v
[2. YouTube Upload] -- static image + audio = MP4, uploaded via Data API
  |                     scripts/upload_youtube.py
  v
YouTube channel: per-book playlists, each marked as a podcast in YT Studio
  |
  v
[3. RSS Feed] (optional, for Spotify/Apple) -- scripts/generate_podcast_rss.py
                MP3s hosted on GitHub Releases, RSS XML uploaded as release asset
```

## Distribution Channels

| Platform  | Method                          | Status       |
|-----------|---------------------------------|--------------|
| YouTube   | Direct MP4 upload + playlist    | Working      |
| YT Music  | Mark playlist as podcast in Studio | Working   |
| Spotify   | RSS feed submission             | Ready (RSS)  |
| Apple     | RSS feed submission             | Ready (RSS)  |

### YouTube (primary)

- Each book = one playlist, titled "<Book> - BSB Bible Audio"
- Each chapter = one video, titled "<Book> <N> - BSB Bible Audio"
- Static image (brand emblem) + audio, encoded as 1080p MP4 via ffmpeg
- Mark each playlist as a podcast in YouTube Studio for YT Music playback
- Playlists serve as podcast seasons; videos as episodes

### RSS Feed (for Spotify/Apple)

- Single feed: "The BSB Bible Audio"
- 66 seasons (canonical Bible order), chapters as episodes
- MP3s hosted as GitHub Release assets (per-book releases)
- RSS XML uploaded as a release asset for a public URL
- Submit once to Spotify and Apple; they auto-ingest new episodes

## Scripts

### scripts/generate_elevenlabs_audio.py
Per-chapter TTS via ElevenLabs Flash v2.5. Checkpointed, resumable.

```bash
python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Philippians
python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Philippians --dry-run
```

### scripts/upload_youtube.py
Builds MP4 (static image + audio) and uploads to YouTube. Creates per-book
playlists. Descriptions emphasize the BSB's public-domain, freely-given nature.

```bash
python scripts/upload_youtube.py --book Philippians --chapter 1
python scripts/upload_youtube.py --book Philippians --all
python scripts/upload_youtube.py --book Philippians --all --dry-run
```

### scripts/generate_podcast_rss.py
Generates a podcast RSS feed with iTunes season/episode tags. Supports
GitHub Releases hosting via `--github-releases` or custom hosting via
`--base-url`.

```bash
# GitHub Releases hosting (per-book releases)
python scripts/generate_podcast_rss.py \
    --github-releases dpshde/bsb-bible-toolkit \
    --books Philippians \
    --output output/rss/podcast.xml

# Custom hosting
python scripts/generate_podcast_rss.py \
    --base-url https://arweave.net/bsb-audio \
    --output output/rss/podcast.xml

# Dry run
python scripts/generate_podcast_rss.py --github-releases dpshde/bsb-bible-toolkit --dry-run
```

## Current Progress

- Philippians (4 chapters): audio generated, uploaded to YouTube, RSS feed live
- Hebrews (13 chapters): audio generated, 6/13 uploaded (hit daily limit)
- Mark (16 chapters): audio generated
- Remaining 63 books: not yet generated

## YouTube Daily Upload Limit

YouTube enforces a daily video upload quota. For unverified/unlisted OAuth apps
in testing mode, the limit is approximately **10 videos per 24 hours** (we hit
this after uploading 4 Philippians + 6 Hebrews chapters in one session).

Verifying the YouTube account (phone verification in YouTube Studio) raises the
limit, but the exact threshold depends on account age, history, and channel
standing.

**Impact on the full Bible:** 1,189 chapters at 10/day = ~119 days of uploads.
Even at a verified 50/day, that's ~24 days. This is the primary bottleneck.

## Tradeoffs: Current Approach (One Video Per Chapter)

**Current architecture:** Each chapter becomes its own YouTube video with a
static image + audio, organized into per-book playlists.

### Pros
- Each chapter individually searchable on YouTube
- Per-book playlists work as podcast seasons; markable as podcasts in YT Studio
- Clean per-chapter analytics (views, watch time per chapter)
- Simple pipeline: TTS -> ffmpeg MP4 -> API upload
- Existing RSS feed maps 1:1 to videos

### Cons
- **Daily upload limit** makes full Bible take months (see above)
- 1,189 videos is heavy channel clutter; viewers may find it overwhelming
- Each video is a static image with audio, minimal visual value per upload
- No multi-language support without uploading separate videos per language
  (would multiply upload count by N languages)
- Upload quota consumed per video regardless of content simplicity

## Alternatives Considered

### 1. Multi-Audio-Track Per Video (YouTube MLA Feature)

YouTube supports adding multiple audio tracks to a single video (Multi-Language
Audio). Viewers switch between tracks in the player settings.

**How it works:**
- Upload one base video per chapter (English audio + static image)
- Add additional audio tracks (other voices, other languages) via YouTube Studio
- Each track must match video duration within +/- 1 second
- Supported formats: MP3, M4A, WAV, FLAC (up to 2GB each)

**API limitation:** The YouTube Data API v3 does NOT expose an endpoint for
uploading additional audio tracks. Multi-audio-track upload is **YouTube Studio
UI only**. The API can upload the base video, but every additional track must be
added manually in Studio.

**Pros:**
- One video per chapter regardless of how many languages/voices
- Viewers pick their preferred audio track in-player
- Clean channel (1,189 videos max, not 1,189 x N languages)
- Localized metadata (title, description, tags) per language via Studio

**Cons:**
- Does NOT solve the daily upload limit (still 1,189 base videos needed)
- Additional audio tracks require manual YouTube Studio work per video
- No API automation for track uploads; doesn't scale to 1,189 chapters x N tracks
- Duration must match exactly; our TTS audio lengths vary per voice/language

**Verdict:** Good for a handful of high-value languages on popular videos, but
not practical for automated full-Bible coverage due to the manual Studio step.

### 2. Per-Book Compilation Videos

Combine all chapters of a book into one long YouTube video with chapter
timestamps/markers.

**How it works:**
- ffmpeg concatenates all chapter MP3s into one audio track
- One MP4 per book (static image + full book audio)
- Chapter markers in the video description for navigation
- 66 videos total instead of 1,189

**Pros:**
- 66 videos = well within daily upload limits (upload the entire Bible in ~7 days)
- Clean channel layout (one video per book)
- Each video is substantial (30 min - several hours), which YouTube's algorithm
  favors for watch time
- Chapter markers provide navigation

**Cons:**
- Loses individual chapter searchability on YouTube
- No per-chapter analytics
- RSS feed no longer maps 1:1 to videos (podcast episodes are per-chapter)
- Large file sizes (some books like Psalms/Isaiah would be many hours long)
- Can't mark individual chapters as podcast episodes in YT Music

**Verdict:** Solves the upload limit problem entirely. Best for YouTube
discovery and watch-time optimization. Loses granularity.

### 3. Account Verification

Verify the YouTube account to increase the daily upload limit.

**How it works:**
- YouTube Studio > Settings > Feature eligibility > Verify phone number
- Raises limit (exact number varies, typically 50-100+/day for verified accounts)
- May require additional verification for very high volumes

**Pros:**
- No architecture change needed
- Keeps per-chapter searchability and analytics
- Simplest fix

**Cons:**
- Still 1,189 videos; even at 50/day that's ~24 days
- Channel still has 1,189 videos (clutter concern remains)
- Doesn't address multi-language scaling

**Verdict:** Easy win that extends the current approach's runway. Pair with
batching uploads across multiple days.

### 4. RSS-Only Distribution (No YouTube Videos)

Skip YouTube video uploads entirely. Distribute only via RSS podcast feed to
YouTube Podcasts, Spotify, and Apple.

**How it works:**
- Host all MP3s on GitHub Releases (or R2/Arweave)
- Generate one RSS feed with all 1,189 chapters
- Submit RSS to YouTube Podcasts, Spotify, Apple
- Platforms ingest episodes from the feed automatically

**Pros:**
- No daily upload limit (RSS is a catalog; MP3s are hosted externally)
- One submission per platform; new episodes auto-ingested
- Native podcast structure on all platforms (seasons, episodes)
- No ffmpeg/MP4 encoding needed
- No YouTube API quota consumed

**Cons:**
- YouTube Podcasts via RSS showed greyed-out/unplayable episodes in YT Music
  during testing (may be a transient issue or a limitation of RSS-ingested content)
- No YouTube search discovery (RSS podcast episodes don't appear in YouTube
  search the same way uploaded videos do)
- No visual component (no static image, no YouTube thumbnails)
- Dependent on external hosting (GitHub Releases URLs work but aren't a CDN)

**Verdict:** Best for Spotify/Apple. Uncertain for YouTube/YT Music due to the
greyed-out issue observed during testing.

### 5. Hybrid: Compilation Videos + RSS Podcast Feed

Combine approaches 2 and 4.

**YouTube:** One long-form video per book (66 total) with chapter markers.
Solves upload limit, maximizes watch time, clean channel.

**Podcast platforms:** RSS feed with individual chapter episodes (1,189 total).
Spotify and Apple get per-chapter episodes; YouTube gets per-book compilations.

**Pros:**
- Best of both: YouTube discovery via compilations, podcast granularity via RSS
- 66 YouTube uploads (done in a week)
- 1,189 RSS episodes (no upload limit)
- Per-chapter listening on Spotify/Apple, per-book listening on YouTube

**Cons:**
- Two separate distribution pipelines to maintain
- YouTube listeners can't navigate to individual chapters (only markers)
- More complex setup

**Verdict:** Most robust. Solves upload limit, serves all platforms well,
preserves per-chapter access where it matters (podcast apps).

## Recommendation

Short-term: **Verify the YouTube account** (option 3) to raise the daily limit
and continue the current per-chapter approach while the Bible is being generated.

Long-term: **Hybrid approach** (option 5) -- per-book compilation videos on
YouTube for discovery + RSS feed for per-chapter podcast distribution on
Spotify/Apple. This eliminates the upload bottleneck and serves each platform
according to its strengths.

Multi-audio-track (option 1) can be layered on top of either approach for
high-value languages on specific books, but the manual Studio requirement makes
it impractical for full-Bible automation.
