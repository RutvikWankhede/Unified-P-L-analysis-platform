"""
core/dataset_context.py - Authoritative In-Memory Runtime Dataset Context
========================================================================
Maintains the active dataset state for the CURRENT RUNTIME SESSION ONLY.
- Every fresh application startup initializes active_dataset to the Canonical Seed Dataset.
- Uploads or explicit activations update the runtime state in-memory for the current session.
- Application restart recreates this object and resets active_dataset to the Canonical Seed Dataset.
- Active dataset is NEVER persisted to disk/DB as a permanent startup pointer.
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CANONICAL_SEED_ID = "899540e5-fa49-49e8-b87a-6965b44fd71f"
CANONICAL_SEED_FILENAME = "unified_pnl_enterprise_demo.xlsx"


class RuntimeDatasetContext:
    def __init__(self):
        self._active_dataset_id: str = CANONICAL_SEED_ID
        self._active_dataset_filename: str = CANONICAL_SEED_FILENAME
        self._source: str = "seed"

    def get_active_id(self) -> str:
        return self._active_dataset_id or CANONICAL_SEED_ID

    def get_active_filename(self) -> str:
        return self._active_dataset_filename or CANONICAL_SEED_FILENAME

    def get_source(self) -> str:
        return self._source

    def is_seed_active(self) -> bool:
        return self.get_active_id() in [CANONICAL_SEED_ID, "DEMO-DATASET"]

    def set_active(
        self,
        dataset_id: str,
        filename: str,
        source: str = "upload",
        reason: str = "USER UPLOAD"
    ):
        prev_id = self.get_active_id()
        prev_name = self.get_active_filename()

        self._active_dataset_id = dataset_id
        self._active_dataset_filename = filename
        self._source = source

        from services.cache_service import invalidate_global_cache
        invalidate_global_cache()

        diag_block = (
            f"\n==================================================\n"
            f"DATASET ACTIVATED\n"
            f"==================================================\n\n"
            f"Previous:\n"
            f"ID: {prev_id}\n"
            f"Name: {prev_name}\n\n"
            f"New:\n"
            f"ID: {dataset_id}\n"
            f"Name: {filename}\n\n"
            f"Reason:\n"
            f"{reason}\n\n"
            f"Scope:\n"
            f"CURRENT RUNTIME SESSION\n\n"
            f"==================================================\n"
        )
        print(diag_block, flush=True)
        logger.info(diag_block)

    def reset_to_seed(self):
        self._active_dataset_id = CANONICAL_SEED_ID
        self._active_dataset_filename = CANONICAL_SEED_FILENAME
        self._source = "seed"
        from services.cache_service import invalidate_global_cache
        invalidate_global_cache()


# Singleton runtime context instance for the running backend process
runtime_dataset_context = RuntimeDatasetContext()
