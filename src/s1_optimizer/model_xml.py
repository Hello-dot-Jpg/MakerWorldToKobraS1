"""Read-only support for Anycubic/Bambu's legacy model-settings XML dialect."""
import re
import xml.etree.ElementTree as ET


def parse_model_settings(raw: bytes) -> ET.Element:
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ET.ParseError("DTD/entity declarations are not supported in model settings")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as error:
        if "unbound prefix" not in str(error):
            raise
        # bbs_3mf.cpp uses XML_ParserCreate(nullptr), with literal slic3rpe tags.
        # Bind only this known prefix in memory; never rewrite archive bytes.
        match = re.search(rb"<config(?=[\s>])", raw)
        if match is None:
            raise
        insertion = b' xmlns:slic3rpe="urn:s1-optimizer:legacy-slic3rpe"'
        normalized = raw[:match.end()] + insertion + raw[match.end():]
        return ET.fromstring(normalized)
