"""Keep the illustrated instructions usable without desktop or network access."""
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("picture_guide", REPO / "tools" / "build_picture_guide.py")
guide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guide)


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = []
        self.image_refs = []

    def handle_starttag(self, tag, attributes):
        self.tags.append(tag)
        for name, value in attributes:
            if name == "id":
                self.ids.append(value)
            if name == "src":
                self.image_refs.append(value)


class PictureGuideTests(unittest.TestCase):
    def test_every_guide_picture_exists_and_is_a_labelled_svg(self):
        for document in (REPO / "USING_THE_APP.md", REPO / "docs" / "EXTRA_OPTIONS.md"):
            references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8"))
            self.assertTrue(references)
            for reference in references:
                with self.subTest(document=document.name, reference=reference):
                    root = ET.parse(document.parent / reference).getroot()
                    self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))
                    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}desc"))
                    self.assertFalse(root.findall(".//{http://www.w3.org/2000/svg}script"))

    def test_offline_html_embeds_all_six_pictures_and_no_scripts(self):
        rendered = guide.render(REPO)
        elements = Elements()
        elements.feed(rendered)
        self.assertEqual(elements.tags.count("svg"), 6)
        self.assertEqual(elements.tags.count("h2"), 6)
        self.assertEqual(len(elements.ids), len(set(elements.ids)))
        self.assertFalse(elements.image_refs, "Offline pictures must not require network downloads")
        self.assertNotIn("script", elements.tags)
        self.assertNotIn("`S1Optimizer", rendered)
        self.assertIn("https://github.com/Hello-dot-Jpg/MakerWorldToKobraS1/blob/main/docs/EXTRA_OPTIONS.md", rendered)

    def test_text_is_escaped_before_formatting(self):
        result = guide.inline("<script>bad</script> **bold** `name.exe`")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("<strong>bold</strong>", result)
        self.assertIn("<code>name.exe</code>", result)
