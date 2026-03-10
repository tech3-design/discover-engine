from app.checkers.registry import registry

from .robots_txt import RobotsTxtChecker
from .xml_sitemap import XmlSitemapChecker
from .image_sitemap import ImageSitemapChecker
from .video_sitemap import VideoSitemapChecker
from .news_sitemap import NewsSitemapChecker
from .https_check import HttpsChecker
from .canonical_tags import CanonicalTagsChecker
from .crawl_traps import CrawlTrapsChecker
from .robots_meta import RobotsMetaChecker

for cls in [
    RobotsTxtChecker,
    XmlSitemapChecker,
    ImageSitemapChecker,
    VideoSitemapChecker,
    NewsSitemapChecker,
    HttpsChecker,
    CanonicalTagsChecker,
    CrawlTrapsChecker,
    RobotsMetaChecker,
]:
    registry.register(cls())
