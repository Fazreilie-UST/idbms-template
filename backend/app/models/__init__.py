import importlib
import pkgutil
from pathlib import Path
import logging

from app.db.base import Base  # shared declarative base

logger = logging.getLogger(__name__)

# --- Auto-discovery for all models in subdirectories ---
AUTO_IMPORT_MODELS = True  # Set False in production for speed
if AUTO_IMPORT_MODELS:
    models_path = Path(__file__).parent
    
    # Iterate through all subdirectories (packages)
    for item in models_path.iterdir():
        if item.is_dir() and not item.name.startswith("_") and item.name != "__pycache__":
            package_name = item.name
            # Iterate through all .py files in the subdirectory
            for finder, module_name, ispkg in pkgutil.iter_modules([str(item)]):
                if not module_name.startswith("_"):
                    try:
                        importlib.import_module(f".{package_name}.{module_name}", package="app.models")
                        logger.info(f"Auto-imported model: {package_name}/{module_name}")
                    except Exception as e:
                        logger.error(f"Failed to import {package_name}/{module_name}: {e}")