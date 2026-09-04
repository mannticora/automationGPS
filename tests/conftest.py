"""Hace que los módulos de scripts/ sean importables desde tests/ sin instalar el proyecto."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
