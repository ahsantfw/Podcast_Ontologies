"""
Logging helper for core_engine and shared components.
Provides JSON logs to console and rotating files, with contextual fields.
"""

import logging
import logging.config
import json
from pathlib import Path
from typing import Optional, Dict, Any


# Get project root (ontology_production_v1 directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_CONFIG_PATH = PROJECT_ROOT / "configs" / "logging.yaml"


class ContextFilter(logging.Filter):
    """
    Ensures each record has a 'context' JSON string with correlation fields.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = getattr(record, "context", None) or {}
        # Safe JSON dump; fall back to "{}" on error
        try:
            record.context = json.dumps(ctx, ensure_ascii=False)
        except Exception:
            record.context = "{}"
        return True


def load_logging_config():
    """Load logging config from YAML if not already configured."""
    if logging.getLogger().handlers:
        return  # already configured
    
    # If YAML config exists, use it
    if LOG_CONFIG_PATH.exists():
        try:
            import yaml
            with open(LOG_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            # Ensure log directories exist for all file handlers
            if "handlers" in config:
                for handler_name, handler_config in config["handlers"].items():
                    if isinstance(handler_config, dict) and "filename" in handler_config:
                        log_file = Path(handler_config["filename"])
                        # Resolve relative paths from project root
                        if not log_file.is_absolute():
                            log_file = PROJECT_ROOT / log_file
                        log_file.parent.mkdir(parents=True, exist_ok=True)
                        # Update config with absolute path
                        config["handlers"][handler_name]["filename"] = str(log_file)
            
            logging.config.dictConfig(config)
            return
        except Exception as e:
            # Fall back to basic logging if YAML fails
            import warnings
            warnings.warn(f"Failed to load logging config from YAML: {e}. Using basic console logging.")
    
    # Fallback: Basic console logging for MVP
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def get_logger(
    name: str,
    run_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> logging.LoggerAdapter:
    """
    Return a logger adapter with default context fields attached.
    """
    load_logging_config()
    base_logger = logging.getLogger(name)
    context = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "request_id": request_id,
    }
    return logging.LoggerAdapter(base_logger, {"context": {k: v for k, v in context.items() if v}})


def with_context(logger: logging.LoggerAdapter, **kwargs: Any) -> logging.LoggerAdapter:
    """
    Return a new logger adapter with extended context.
    """
    ctx = {}
    ctx.update(logger.extra.get("context", {}))
    ctx.update({k: v for k, v in kwargs.items() if v is not None})
    return logging.LoggerAdapter(logger.logger, {"context": ctx})


def log_progress(
    logger: logging.LoggerAdapter,
    stage: str,
    message: str,
    *,
    index: Optional[int] = None,
    total: Optional[int] = None,
    **extras: Any,
):
    """
    Convenience for fine-grained progress logging (e.g., file-by-file).
    """
    ctx = {"stage": stage, "index": index, "total": total}
    ctx.update({k: v for k, v in extras.items() if v is not None})
    logger.info(message, extra={"context": ctx})

