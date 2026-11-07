"""penmimic - write any text in your own handwriting."""

from .template import make_both_templates, make_template
from .writer import Page, Writer

__version__ = "0.1.1"
__all__ = ["Writer", "Page", "make_template", "make_both_templates", "__version__"]


