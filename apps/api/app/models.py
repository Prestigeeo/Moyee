"""Import every model module so `Base.metadata` knows all tables."""

from app.modules.assistant.models import Conversation, Message, MessageCitation  # noqa: F401
from app.modules.billing.models import Plan, Subscription, UsageCounter  # noqa: F401
from app.modules.library.models import (  # noqa: F401
    AcademicSource,
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentSummary,
    ProjectSource,
)
from app.modules.literature.models import LiteratureEntry, LiteratureMatrix  # noqa: F401
from app.modules.projects.models import Project  # noqa: F401
from app.modules.users.models import Profile  # noqa: F401
from app.modules.writing.models import ResearchDocument  # noqa: F401
