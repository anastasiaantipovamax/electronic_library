import bleach
import markdown2

ALLOWED_MARKDOWN_TAGS = [
    'p', 'br', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'pre', 'code', 'blockquote',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'hr'
]

ALLOWED_MARKDOWN_ATTRIBUTES = {
    'a': ['href', 'title', 'rel'],
    'th': ['align'],
    'td': ['align'],
}


def sanitize_markdown_source(text):
    """Очищает исходный Markdown перед сохранением в БД."""
    if not text:
        return ''
    return bleach.clean(
        text,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes=ALLOWED_MARKDOWN_ATTRIBUTES,
        protocols=['http', 'https', 'mailto'],
        strip=True,
    )


def markdown_filter(text):
    """Конвертирует Markdown в HTML и повторно очищает готовую HTML-разметку."""
    if not text:
        return ''
    html = markdown2.markdown(text, extras=['fenced-code-blocks', 'tables'])
    return bleach.clean(
        html,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes=ALLOWED_MARKDOWN_ATTRIBUTES,
        protocols=['http', 'https', 'mailto'],
        strip=True,
    )


def register_filters(app):
    app.jinja_env.filters['markdown'] = markdown_filter
