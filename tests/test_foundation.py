"""
Tests for Phase 1: Project Foundation, Configuration, and Utilities.
"""
from src import config, utils


def test_config_paths_exist():
    assert config.BASE_DIR.exists()
    assert config.SRC_DIR.exists()
    assert config.ASSETS_DIR.exists()
    assert config.MEMES_DIR.exists()
    assert config.OUTPUTS_DIR.exists()
    assert config.TEMP_DIR.exists()


def test_config_models_and_options():
    assert config.DEFAULT_GEMINI_MODEL in config.AVAILABLE_GEMINI_MODELS
    assert len(config.AVAILABLE_GEMINI_MODELS) >= 3
    assert "gemini-2.5-flash" in config.AVAILABLE_GEMINI_MODELS
    assert "Comedy" in config.CONTENT_TYPES
    assert 5 in config.CLIP_COUNT_OPTIONS
    assert "Modern" in config.EDITING_STYLES


def test_legal_disclaimers():
    assert "Copyright and monetization decisions" in config.LEGAL_DISCLAIMER
    assert "YouTube's reused-content policy is separate from copyright" in config.REUSED_CONTENT_POLICY_NOTICE
    assert "No unverified assets detected" in config.SAFE_EXPORT_STATUS_NOTICE


def test_viral_weights_sum():
    total_weight = sum(config.VIRAL_WEIGHTS.values())
    assert round(total_weight, 4) == 1.0


def test_youtube_url_validation():
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    ]
    invalid_urls = [
        "https://vimeo.com/12345",
        "invalid_text",
        "",
        "http://notyoutube.com/video"
    ]
    for u in valid_urls:
        assert utils.is_valid_youtube_url(u) is True, f"Failed on valid URL: {u}"
    for u in invalid_urls:
        assert utils.is_valid_youtube_url(u) is False, f"Should be invalid: {u}"


def test_timestamp_formatting():
    assert utils.format_timestamp(0) == "00:00"
    assert utils.format_timestamp(65) == "01:05"
    assert utils.format_timestamp(3665) == "01:01:05"
    assert utils.parse_timestamp("01:05") == 65.0
    assert utils.parse_timestamp("01:01:05") == 3665.0


def test_api_key_persistence(tmp_path, monkeypatch):
    from src import config
    test_key_file = tmp_path / ".test_gemini_key"
    monkeypatch.setattr(config, "KEY_STORE_PATH", test_key_file)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Empty initially
    assert config.load_saved_api_key() == ""

    # Save key
    assert config.save_api_key_locally("AIzaSyFakeKey123") is True
    assert test_key_file.exists()
    assert config.load_saved_api_key() == "AIzaSyFakeKey123"

    # Clear key
    assert config.save_api_key_locally("") is True
    assert not test_key_file.exists()
    assert config.load_saved_api_key() == ""
