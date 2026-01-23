"""YouTube Intelligence SaaS Application Module"""

from .main import YouTubeApp
from .auth import YouTubeAuthHandler

__version__ = "0.1.0"
__all__ = ["YouTubeApp", "YouTubeAuthHandler"]
