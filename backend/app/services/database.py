import logging
from typing import Optional, Any
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

logger = logging.getLogger("bollyswap.services.database")


class DatabaseService:
    """
    Manages asynchronous MongoDB Atlas client lifecycle, connection pooling,
    collection access, and collection index synchronization.
    """

    def __init__(self):
        self.client: Optional[AsyncMongoClient] = None
        self.db: Optional[Any] = None
        self._connected: bool = False
        self._status_message: str = "Uninitialized"

    @property
    def is_connected(self) -> bool:
        return self._connected and self.db is not None

    @property
    def status(self) -> str:
        if self._connected:
            return "connected"
        if self._status_message.startswith("Unconfigured"):
            return "unconfigured"
        return "disconnected"

    async def connect(self, uri: Optional[str], db_name: str = "bollyswap") -> None:
        """Connects to MongoDB Atlas cluster and sets up required indexes."""
        if not uri or uri.strip() == "" or uri.startswith("YOUR_"):
            self._connected = False
            self._status_message = "Unconfigured: MONGODB_URI is empty or placeholder."
            logger.info("MongoDB Atlas connection skipped: MONGODB_URI not set.")
            return

        try:
            logger.info("Connecting to MongoDB Atlas (database: %s)...", db_name)
            self.client = AsyncMongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=5,
            )
            # Verify connectivity
            await self.client.admin.command("ping")
            self.db = self.client[db_name]
            self._connected = True
            self._status_message = "Connected to MongoDB Atlas."
            logger.info("MongoDB Atlas connection verified successfully.")

            # Create indexes
            await self._create_indexes()

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self._connected = False
            self._status_message = f"Connection timeout: Could not connect to cluster ({type(e).__name__})."
            logger.warning("MongoDB Atlas connection timed out: %s", type(e).__name__)
        except PyMongoError as e:
            self._connected = False
            self._status_message = f"MongoDB error: {type(e).__name__}"
            logger.error("MongoDB Atlas initialization error: %s", type(e).__name__)
        except Exception as e:
            self._connected = False
            self._status_message = f"Unexpected error: {type(e).__name__}"
            logger.exception("Unexpected error connecting to MongoDB")

    async def _create_indexes(self) -> None:
        """Creates collection indexes for fast lookup and integrity."""
        if self.db is None:
            return
        try:
            # projects indexes
            projects = self.db.projects
            await projects.create_index("project_id", unique=True)
            await projects.create_index("status")
            await projects.create_index([("created_at", -1)])

            # processing_jobs indexes
            jobs = self.db.processing_jobs
            await jobs.create_index("job_id", unique=True)
            await jobs.create_index("project_id")
            await jobs.create_index("status")
            await jobs.create_index([("created_at", -1)])

            # consent_records indexes
            consent = self.db.consent_records
            await consent.create_index("project_id")
            await consent.create_index([("created_at", -1)])

            # uploads metadata indexes
            uploads = self.db.uploads
            await uploads.create_index("upload_id", unique=True)
            await uploads.create_index([("created_at", -1)])

            # detection_jobs indexes (Phase 4)
            detection_jobs = self.db.detection_jobs
            await detection_jobs.create_index("detection_job_id", unique=True)
            await detection_jobs.create_index("project_id")
            await detection_jobs.create_index("video_id")
            await detection_jobs.create_index([("created_at", -1)])

            logger.info("MongoDB Atlas indexes synchronized successfully.")
        except Exception as e:
            logger.warning("Index creation warning (may already exist or insufficient permissions): %s", e)

    async def disconnect(self) -> None:
        """Closes MongoDB connection pool gracefully."""
        if self.client is not None:
            logger.info("Closing MongoDB Atlas connection pool...")
            await self.client.close()
            self.client = None
            self.db = None
            self._connected = False
            self._status_message = "Disconnected."

    async def ping(self) -> bool:
        """Performs a quick heartbeat ping to verify active connection."""
        if not self.is_connected or self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            self._connected = False
            return False

    def get_collection(self, name: str) -> Any:
        """Returns collection handle if connected, raises runtime error otherwise."""
        if not self.is_connected or self.db is None:
            raise RuntimeError(
                f"Database is not connected. Operation on '{name}' cannot be fulfilled."
            )
        return self.db[name]


# Global singleton instance
database_service = DatabaseService()


def get_database_service() -> DatabaseService:
    """Dependency provider for database service."""
    return database_service


def get_db() -> Any:
    """Dependency provider returning active database handle if available."""
    if not database_service.is_connected:
        raise RuntimeError("MongoDB connection is offline or unavailable.")
    return database_service.db

