"""
Skills Package
==============

Available skills:
- social_manager: LinkedIn post drafting
- email_manager: Urgent email checking
"""

from . import social_manager
from . import email_manager

__all__ = ["social_manager", "email_manager"]
