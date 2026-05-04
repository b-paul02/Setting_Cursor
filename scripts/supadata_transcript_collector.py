import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("SUPADATA_API_KEY")
API_URL = "https://api.supadata.ai/v1/transcript"


def safe_filename(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def fetch_transcript(video_url: str, lang: str = "en", mode: str = "native") -> dict:
    """
    Fetch transcript from Supadata.

    mode options:
    - native: faster, uses existing YouTube captions
    - auto: tries native first, then may use fallback processing
    - generate: may take longer
    """

    if not API_KEY:
        raise ValueError(
            "SUPADATA_API_KEY is missing. Add it to your .env file like this:\n"
            "SUPADATA_API_KEY=your_api_key_here"
        )

    params = {
        "url": video_url,
        "lang": lang,
        "text": "true",
        "mode": mode,
    }

    headers = {
        "x-api-key": API_KEY,
    }

    try:
        print("Calling Supadata API...")
        print(f"Mode: {mode}")
        print("Please wait...")

        response = requests.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=180,
        )

        if response.status_code == 200:
            return response.json()

        raise RuntimeError(
            f"Supadata API error: {response.status_code}\n{response.text}"
        )

    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            "Supadata timed out. Try again later, use a shorter video, "
            "or change mode from 'native' to 'auto'."
        )

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Network connection failed. Check your internet, VPN, firewall, "
            "or try again later."
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Request failed: {error}")


def extract_transcript_text(transcript_data: dict) -> str:
    """
    Handles different possible Supadata response shapes.
    """

    if "content" in transcript_data and isinstance(transcript_data["content"], str):
        return transcript_data["content"]

    if "transcript" in transcript_data:
        transcript = transcript_data["transcript"]

        if isinstance(transcript, str):
            return transcript

        if isinstance(transcript, list):
            lines = []
            for item in transcript:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    start = item.get("start")
                    if start is not None:
                        lines.append(f"[{start}s] {text}")
                    else:
                        lines.append(text)
                else:
                    lines.append(str(item))
            return "\n".join(lines)

    if "data" in transcript_data:
        data = transcript_data["data"]

        if isinstance(data, str):
            return data

        if isinstance(data, dict):
            if "content" in data:
                return str(data["content"])
            if "transcript" in data:
                return str(data["transcript"])

    return str(transcript_data)


def save_transcript(
    video_url: str,
    creator: str,
    video_title: str,
    transcript_data: dict,
) -> None:
    folder = Path("research/youtube-transcripts")
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(creator)}-{safe_filename(video_title)}.md"
    file_path = folder / filename

    transcript_text = extract_transcript_text(transcript_data)
    lang = transcript_data.get("lang", "unknown")

    markdown = f"""# YouTube Transcript: {video_title}

## Video Details
- **Creator:** {creator}
- **Video title:** {video_title}
- **Video link:** {video_url}
- **Language:** {lang}
- **Date collected:** 3 May 2026
- **Topic relevance:** AI-powered SEO content production

## Why this video was selected
This video was selected because it discusses AI SEO, GEO, AEO, content optimization, SEO workflows, content briefs, content refresh, or AI-assisted SEO content production.

## Transcript
{transcript_text}
"""

    file_path.write_text(markdown, encoding="utf-8")
    print(f"Saved transcript to: {file_path}")


def main() -> None:
    print("Supadata YouTube Transcript Collector")
    print("------------------------------------")

    video_url = input("Paste YouTube video URL: ").strip()
    creator = input("Creator/channel name: ").strip()
    video_title = input("Video title: ").strip()

    mode = input("Mode native/auto/generate [native]: ").strip().lower()
    if not mode:
        mode = "native"

    if mode not in {"native", "auto", "generate"}:
        print("Invalid mode. Using native.")
        mode = "native"

    data = fetch_transcript(video_url=video_url, mode=mode)
    save_transcript(
        video_url=video_url,
        creator=creator,
        video_title=video_title,
        transcript_data=data,
    )


if __name__ == "__main__":
    main()