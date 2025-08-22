#!/usr/bin/env bash
set -euo pipefail
urls=(
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/15-82.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/15-82.1"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/14-82.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/14-82.1"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/14-80.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/13-73.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/13-72.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/13-72.1"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/12-66.5"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/11-61.2"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/9-53.5"
  "https://mangapoisk.io/manga/wedding-ring-story-1/chapter/8-48"
)
for u in "${urls[@]}"; do
  echo "RUN: $u"
  python3 /home/sirius/Manga/MangaToolkitV4/cli.py --chapter-url "$u"
  sleep 1
done
