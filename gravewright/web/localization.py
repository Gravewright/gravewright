"""Translate application-owned dictionaries and static Jinja text, never user data."""
import ast
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from jinja2 import pass_context
from jinja2.ext import Extension


@lru_cache(maxsize=1)
def native_messages():
    root = Path(__file__).resolve().parents[1]
    return {name: json.loads((root / path).read_text()) for name, path in {
        'accounts': 'accounts/messages.json', 'inside': 'web/inside_messages.json',
        'table': 'table/messages.json', 'tools': 'table/tool_messages.json',
    }.items()}


def translate_tree(value, messages):
    if isinstance(value, str):
        return messages.get(value, value)
    if isinstance(value, dict):
        return {key: translate_tree(item, messages) for key, item in value.items()}
    if isinstance(value, list):
        return [translate_tree(item, messages) for item in value]
    return value


def template_context(request):
    from gravewright.modules.localization import for_request
    language = for_request(request)
    context = {'default_locale': language['id'], 'language': language,
               'language_enabled': len(language['options']) > 1}
    if language['messages']:
        original = native_messages()
        translated = translate_tree(original, language['messages'])
        context.update(translated['inside'])
        context.update(translated['table'])
        context.update(text=translated['accounts'], auth=translated['accounts'],
                       t=lambda key: translated['tools'].get(key, key))
    return context


@pass_context
def tr(context, value):
    messages = context.get('language', {}).get('messages', {})
    return messages.get(value, value) if isinstance(value, str) else value


class StaticText(HTMLParser):
    """Annotate literal text at compilation; leave variables and scripts intact."""
    attributes = re.compile(r'(\b(?:title|placeholder|aria-label|alt)\s*=\s*)([\"\'])(.*?)\2', re.S)

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts, self.strings, self.protected = [], set(), 0

    def literal(self, value):
        text = unescape(value.strip())
        if not re.search(r'[A-Za-zÀ-ÿ]', text) or '{' in text or '}' in text:
            return value
        self.strings.add(text)
        leading = value[:len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()):]
        return leading + '{{ tr(' + json.dumps(text, ensure_ascii=False) + ') }}' + trailing

    reactive_attributes = re.compile(r"(\b(?:data-text|data-attr:(?:title|placeholder|aria-label|alt))\s*=\s*)([\"\'])(.*?)\2", re.S)
    javascript_strings = re.compile(r"'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"")

    def reactive(self, match):
        expression = match[3]
        if '{{' in expression or '{%' in expression:
            return match[0]
        def translate_literal(literal):
            try:
                value = ast.literal_eval(literal[0])
            except (ValueError, SyntaxError):
                return literal[0]
            if not isinstance(value, str) or not value.strip():
                return literal[0]
            self.strings.add(value)
            return '{{ tr(' + json.dumps(value, ensure_ascii=False) + ')|tojson|forceescape }}'
        return match[1] + match[2] + self.javascript_strings.sub(translate_literal, expression) + match[2]

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        if not self.protected:
            raw = self.reactive_attributes.sub(self.reactive, raw)
            raw = self.attributes.sub(lambda m: m[1] + m[2] + self.literal(m[3]) + m[2], raw)
        self.parts.append(raw)
        if tag in ('script', 'style', 'code', 'pre'):
            self.protected += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in ('script', 'style', 'code', 'pre'):
            self.protected -= 1

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')
        if tag in ('script', 'style', 'code', 'pre'):
            self.protected = max(0, self.protected - 1)

    def handle_data(self, data):
        self.parts.append(data if self.protected else self.literal(data))

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, value):
        self.parts.append(f'<!--{value}-->')

    def handle_decl(self, value):
        self.parts.append(f'<!{value}>')


class LocalizationExtension(Extension):
    def preprocess(self, source, name, filename=None):
        if name and name.endswith('.html'):
            parser = StaticText()
            parser.feed(source)
            parser.close()
            return ''.join(parser.parts)
        return source
