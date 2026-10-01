from __future__ import annotations

CONTENT_TYPES_MEMBER = "[Content_Types].xml"
ROOT_RELATIONSHIPS_MEMBER = "_rels/.rels"
MODEL_SUFFIX = ".model"
PROJECT_SETTINGS_BASENAME = "project_settings.config"

# Structured members larger than this are inventoried but not loaded into
# memory. Normal slicer configuration files are far smaller.
MAX_STRUCTURED_MEMBER_BYTES = 25 * 1024 * 1024

# Model XML can legitimately be much larger than slicer configuration. It is
# validated as a stream, so this is a work bound rather than an allocation.
MAX_XML_MEMBER_BYTES = 512 * 1024 * 1024

# A full CRC pass decompresses every archive member. Bound that diagnostic so
# an inspection cannot be forced to expand an enormous or malicious archive.
MAX_CRC_SCAN_BYTES = 512 * 1024 * 1024

JSON_SUFFIXES = (".json",)
XML_SUFFIXES = (".xml", ".model", ".rels")
CONFIG_SUFFIXES = (".config",)
