"""AI support module public API."""

from .ai_support import AISupport, analyze_transcript, get_available_templates, summarize_by_hash

__all__ = [
	"AISupport",
	"analyze_transcript",
	"get_available_templates",
	"summarize_by_hash",
]