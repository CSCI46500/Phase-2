from html.parser import HTMLParser
import re

# HTML stripper for README Parsing
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_data(self):
        return "".join(self.text)

def strip_html(text: str) -> str:
    s = MLStripper()
    s.feed(text)
    return s.get_data()

def strip_markdown(text: str) -> str:
    # Remove links: [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove emphasis: **bold**, *italic*, __bold__, _italic_
    text = re.sub(r'(\*\*|\*|__|_)(.*?)\1', r'\2', text)
    # Remove headings: # Heading
    text = re.sub(r'^\s*#+\s+', '', text, flags=re.MULTILINE)
    # Remove inline code: `code`
    text = re.sub(r'`([^`]*)`', r'\1', text)
    return text