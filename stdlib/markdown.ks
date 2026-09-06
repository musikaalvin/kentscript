:: markdown - Markdown to HTML conversion
::
:: Usage:
::   import markdown;
::   print(markdown.to_html("# Hello\\n\\nThis is **bold** text."));

func to_html(text) {
    return system_markdown_to_html(text);
}

func to_html_file(path) {
    let content = system_fs_read_text(path);
    return system_markdown_to_html(content);
}

export { to_html, to_html_file };
