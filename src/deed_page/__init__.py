"""Official client for the public deed.page API (https://deed.page/docs)."""
from .client import DeedPage, DeedPageError, collect_files, load_token, save_token, token_path, redact

__version__ = "0.1.0"
__all__ = ["DeedPage", "DeedPageError", "collect_files", "load_token", "save_token", "token_path", "redact", "__version__"]
