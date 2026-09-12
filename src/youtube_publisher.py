"""
ViralClipper AI Studio - YouTube Channel Connection & 1-Click Shorts Scheduler
Supports:
- Official Google OAuth 2.0 (YouTube Data API v3) with client_secrets.json or Client ID/Secret.
- Built-in Sandbox / Test Channel Mode for immediate zero-config testing.
- Resumable video upload with automated metadata (titles, tags, descriptions, hashtags, thumbnails).
- Peak-time scheduling (sets privacyStatus="private" and publishAt="<UTC ISO timestamp>").
- Persistent scheduled queue tracking in outputs/scheduled_shorts.json.
"""
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

try:
    from src.config import (
        CREDENTIALS_DIR,
        YOUTUBE_TOKEN_FILE,
        YOUTUBE_CLIENT_SECRETS_FILE,
        SCHEDULED_SHORTS_FILE,
        OUTPUTS_DIR
    )
except ImportError:
    from src.config import BASE_DIR, OUTPUTS_DIR
    CREDENTIALS_DIR = BASE_DIR / "credentials"
    YOUTUBE_TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.json"
    YOUTUBE_CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "client_secrets.json"
    SCHEDULED_SHORTS_FILE = OUTPUTS_DIR / "scheduled_shorts.json"
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]


class ChannelInfo(BaseModel):
    channel_id: str = Field(..., description="YouTube Channel ID")
    title: str = Field(..., description="Channel Name")
    handle: str = Field(..., description="Channel Handle e.g. @CreatorName")
    avatar_url: str = Field(..., description="Channel profile image URL")
    subscriber_count: int = Field(0, description="Subscriber count")
    video_count: int = Field(0, description="Total video count")
    is_demo: bool = Field(False, description="True if simulated test channel")


class ScheduledShortRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    clip_id: str
    video_path: str
    title: str
    description: str
    tags: List[str]
    hashtags: List[str]
    scheduled_time_utc: Optional[str] = None
    scheduled_time_local: Optional[str] = None
    privacy_status: str = "private"
    channel_title: str
    channel_handle: str
    video_id: str
    youtube_url: str
    studio_url: str
    thumbnail_path: Optional[str] = None
    status: str = "SCHEDULED"  # SCHEDULED, PUBLISHED, DRAFT, FAILED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class YouTubeChannelManager:
    """
    Manages OAuth credentials, tokens, channel metadata, and connection states.
    Persists credentials to credentials/youtube_token.json.
    """
    def __init__(
        self,
        token_path: Optional[Path] = None,
        client_secrets_path: Optional[Path] = None
    ):
        self.token_path = token_path or YOUTUBE_TOKEN_FILE
        self.client_secrets_path = client_secrets_path or YOUTUBE_CLIENT_SECRETS_FILE
        self._demo_channel_file = CREDENTIALS_DIR / "demo_channel.json"

    def is_connected(self) -> bool:
        """Returns True if a live token or demo channel is active."""
        if self._demo_channel_file.exists():
            return True
        if self.token_path.exists():
            try:
                data = json.loads(self.token_path.read_text(encoding="utf-8"))
                return bool(data.get("token") or data.get("access_token") or data.get("refresh_token"))
            except Exception:
                return False
        return False

    def is_demo_mode(self) -> bool:
        """Returns True if the active connection is a sandbox demo channel."""
        return self._demo_channel_file.exists()

    def get_channel_info(self) -> Optional[ChannelInfo]:
        """Returns metadata for the currently connected YouTube channel."""
        if not self.is_connected():
            return None

        # Check Demo Mode First
        if self.is_demo_mode():
            try:
                data = json.loads(self._demo_channel_file.read_text(encoding="utf-8"))
                return ChannelInfo(**data)
            except Exception:
                pass

        # Live Google OAuth Channel Info
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = self._load_credentials()
            if not creds:
                return None

            youtube = build("youtube", "v3", credentials=creds)
            resp = youtube.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()

            items = resp.get("items", [])
            if not items:
                return None

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            return ChannelInfo(
                channel_id=item.get("id", "unknown_channel_id"),
                title=snippet.get("title", "My YouTube Channel"),
                handle=snippet.get("customUrl", f"@{snippet.get('title', 'channel').replace(' ', '').lower()}"),
                avatar_url=snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                subscriber_count=int(stats.get("subscriberCount", 0)),
                video_count=int(stats.get("videoCount", 0)),
                is_demo=False
            )
        except Exception as e:
            print(f"[YouTube Publisher] Error fetching live channel info: {e}")
            return None

    def connect_demo_mode(
        self,
        channel_name: str = "My Comedy Studio",
        handle: str = "@MyComedyStudio",
        subscriber_count: int = 48500
    ) -> ChannelInfo:
        """Activates zero-config sandbox demo mode for instant 1-click test scheduling."""
        info = ChannelInfo(
            channel_id="UC_DEMO_COMEDY_STUDIO_99",
            title=channel_name,
            handle=handle if handle.startswith("@") else f"@{handle}",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
            subscriber_count=subscriber_count,
            video_count=142,
            is_demo=True
        )
        self._demo_channel_file.parent.mkdir(parents=True, exist_ok=True)
        self._demo_channel_file.write_text(json.dumps(info.model_dump(), indent=2), encoding="utf-8")
        return info

    def connect_with_client_secrets_dict(self, secrets_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Saves client secrets and prepares Google OAuth 2.0 flow.
        Accepts standard Google Cloud client_secrets.json structure.
        """
        try:
            self.client_secrets_path.parent.mkdir(parents=True, exist_ok=True)
            self.client_secrets_path.write_text(json.dumps(secrets_dict, indent=2), encoding="utf-8")

            # Remove demo channel file if active
            if self._demo_channel_file.exists():
                self._demo_channel_file.unlink()

            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_config(
                secrets_dict,
                scopes=YOUTUBE_SCOPES
            )
            # Try running local server auth; if in headless cloud container, gracefully return prompt
            try:
                creds = flow.run_local_server(port=0, open_browser=False)
                self._save_credentials(creds)
                return True, "Successfully authorized with YouTube Channel!"
            except Exception as browser_err:
                return False, f"Cloud server cannot open browser. Please use 'Paste Saved Token' or generate token on your desktop: {browser_err}"
        except Exception as e:
            return False, f"Google OAuth failed: {str(e)}"

    def connect_with_token_dict(self, token_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """Directly authenticates by loading a pre-generated token.json (ideal for cloud deployments)."""
        try:
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(json.dumps(token_dict, indent=2), encoding="utf-8")
            if self._demo_channel_file.exists():
                self._demo_channel_file.unlink()

            info = self.get_channel_info()
            if info:
                return True, f"Successfully connected to YouTube channel: {info.title} ({info.handle})"
            return True, "Successfully saved YouTube credentials token!"
        except Exception as e:
            return False, f"Failed to save YouTube token: {e}"

    def connect_with_client_credentials(
        self,
        client_id: str,
        client_secret: str
    ) -> Tuple[bool, str]:
        """Generates standard client config from Client ID and Secret and authenticates."""
        config = {
            "installed": {
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"]
            }
        }
        return self.connect_with_client_secrets_dict(config)

    def disconnect(self) -> bool:
        """Disconnects active channel by removing tokens and demo flags."""
        disconnected = False
        if self._demo_channel_file.exists():
            self._demo_channel_file.unlink()
            disconnected = True
        if self.token_path.exists():
            self.token_path.unlink()
            disconnected = True
        return disconnected

    def _load_credentials(self):
        """Loads and refreshes OAuth credentials from token_path."""
        if not self.token_path.exists():
            return None
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        data = json.loads(self.token_path.read_text(encoding="utf-8"))
        creds = Credentials.from_authorized_user_info(data, YOUTUBE_SCOPES)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
            except Exception as e:
                print(f"[YouTube Publisher] Error refreshing token: {e}")
        return creds

    def _save_credentials(self, creds):
        """Serializes Google OAuth Credentials to token_path."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        creds_data = json.loads(creds.to_json())
        self.token_path.write_text(json.dumps(creds_data, indent=2), encoding="utf-8")


def format_youtube_tags(raw_tags: Union[str, List[str]]) -> List[str]:
    """Cleans and formats tags for YouTube Data API (no # prefix, unique, <= 400 chars total)."""
    if isinstance(raw_tags, str):
        if "," in raw_tags:
            parts = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            parts = [t.strip() for t in raw_tags.split() if t.strip()]
    else:
        parts = [str(t).strip() for t in raw_tags if str(t).strip()]

    clean_tags: List[str] = []
    seen = set()
    total_len = 0

    for p in parts:
        cleaned = p.lstrip("#").strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            if total_len + len(cleaned) + 1 <= 400:
                clean_tags.append(cleaned)
                total_len += len(cleaned) + 1

    return clean_tags


def format_youtube_title(title: str) -> str:
    """Enforces YouTube Shorts title requirements: under 100 chars, includes #Shorts."""
    t = title.strip()
    if "#Shorts" not in t and "#shorts" not in t:
        if len(t) + 9 <= 100:
            t = f"{t} #Shorts"
        else:
            t = f"{t[:90].rstrip()} #Shorts"
    return t[:100]


def schedule_youtube_short(
    video_path: Union[str, Path],
    title: str,
    description: str,
    tags: Union[str, List[str]],
    hashtags: Optional[List[str]] = None,
    publish_at: Optional[Union[datetime, str]] = None,
    privacy_status: str = "private",
    category_id: str = "23",  # 23 = Comedy, 24 = Entertainment
    made_for_kids: bool = False,
    thumbnail_path: Optional[Union[str, Path]] = None,
    channel_manager: Optional[YouTubeChannelManager] = None
) -> Dict[str, Any]:
    """
    1-Click YouTube Shorts Publisher & Scheduler:
    - Automatically structures title, tags, description, and hashtags.
    - If publish_at is provided, schedules release (status.privacyStatus='private' + status.publishAt='<UTC ISO>').
    - Uploads video via resumable chunked upload.
    - Sets custom video thumbnail if provided.
    - Saves entry to outputs/scheduled_shorts.json.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    mgr = channel_manager or YouTubeChannelManager()
    if not mgr.is_connected():
        raise RuntimeError("No YouTube Channel connected. Please connect your channel or enable Demo Mode first.")

    channel_info = mgr.get_channel_info()
    channel_title = channel_info.title if channel_info else "YouTube Channel"
    channel_handle = channel_info.handle if channel_info else "@channel"

    # 1. Prepare Metadata
    final_title = format_youtube_title(title)
    final_tags = format_youtube_tags(tags)

    # Format description with hashtags appended at the end
    desc_text = description.strip()
    if hashtags:
        clean_hashes = " ".join(f"#{h.lstrip('#')}" for h in hashtags if h.strip())
        if clean_hashes and clean_hashes not in desc_text:
            desc_text = f"{desc_text}\n\n{clean_hashes}"

    # 2. Prepare Scheduling Timestamps
    scheduled_utc_str = None
    scheduled_local_str = None
    is_scheduled = False

    if publish_at:
        if isinstance(publish_at, str):
            try:
                # Try ISO format parsing
                dt = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now(timezone.utc) + timedelta(hours=24)
        else:
            dt = publish_at

        # If naive datetime, assume local time and convert to UTC
        if dt.tzinfo is None:
            local_now = datetime.now()
            utc_now = datetime.now(timezone.utc)
            offset = local_now - utc_now.replace(tzinfo=None)
            dt_utc = (dt - offset).replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt.astimezone(timezone.utc)

        # YouTube Data API requires format: YYYY-MM-DDTHH:MM:SS.000Z
        scheduled_utc_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        scheduled_local_str = dt.strftime("%A, %b %d at %I:%M %p")
        is_scheduled = True
        # When scheduling, YouTube REQUIRES privacyStatus to be 'private'
        privacy_status = "private"

    # 3. Execute Upload / Scheduling
    if mgr.is_demo_mode():
        # === SANDBOX / DEMO CHANNEL MODE ===
        # Generate realistic 11-char YouTube Video ID
        video_id = str(uuid.uuid4()).replace("-", "")[:11]
        status_label = "SCHEDULED" if is_scheduled else ("PUBLIC" if privacy_status == "public" else "UNLISTED")
    else:
        # === LIVE YOUTUBE DATA API V3 UPLOAD ===
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = mgr._load_credentials()
        if not creds:
            raise RuntimeError("Live YouTube credentials could not be loaded or refreshed.")

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": final_title,
                "description": desc_text,
                "tags": final_tags,
                "categoryId": str(category_id)
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids
            }
        }

        if is_scheduled and scheduled_utc_str:
            body["status"]["publishAt"] = scheduled_utc_str

        media = MediaFileUpload(
            str(v_path),
            chunksize=1024 * 1024 * 5,  # 5MB chunks
            resumable=True,
            mimetype="video/mp4"
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube upload completed but no video ID was returned.")

        status_label = "SCHEDULED" if is_scheduled else ("PUBLIC" if privacy_status == "public" else "UNLISTED")

        # Set custom thumbnail if provided
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                ).execute()
            except Exception as e:
                print(f"[YouTube Publisher] Optional thumbnail upload warning: {e}")

    # 4. Construct Result URLs
    youtube_url = f"https://youtube.com/shorts/{video_id}"
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

    record = ScheduledShortRecord(
        clip_id=v_path.stem,
        video_path=str(v_path),
        title=final_title,
        description=desc_text,
        tags=final_tags,
        hashtags=hashtags or ["#Shorts", "#Comedy"],
        scheduled_time_utc=scheduled_utc_str,
        scheduled_time_local=scheduled_local_str,
        privacy_status=privacy_status,
        channel_title=channel_title,
        channel_handle=channel_handle,
        video_id=video_id,
        youtube_url=youtube_url,
        studio_url=studio_url,
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        status=status_label
    )

    # 5. Persist to outputs/scheduled_shorts.json
    save_scheduled_short_record(record)

    return record.model_dump()


def save_scheduled_short_record(record: ScheduledShortRecord) -> None:
    """Appends a new scheduled short record to outputs/scheduled_shorts.json."""
    SCHEDULED_SHORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = get_scheduled_shorts()
    # Filter out any with same ID if updating
    updated = [r for r in existing if r.get("id") != record.id]
    updated.insert(0, record.model_dump())
    SCHEDULED_SHORTS_FILE.write_text(json.dumps(updated, indent=2), encoding="utf-8")


def get_scheduled_shorts() -> List[Dict[str, Any]]:
    """Retrieves all scheduled / published shorts records."""
    if not SCHEDULED_SHORTS_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULED_SHORTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def delete_scheduled_short(record_id: str) -> bool:
    """Removes a scheduled short entry from the local queue."""
    existing = get_scheduled_shorts()
    filtered = [r for r in existing if r.get("id") != record_id and r.get("video_id") != record_id]
    if len(filtered) != len(existing):
        SCHEDULED_SHORTS_FILE.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
        return True
    return False
