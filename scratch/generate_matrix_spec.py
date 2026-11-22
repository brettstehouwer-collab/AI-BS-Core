import markdown
import weasyprint

# Paths
md_path = r"C:\Users\footb\.gemini\antigravity-ide\brain\1735480a-4db2-4a42-a53f-5e25870ba0b6\aibs_matrix_master_spec.md"
pdf_path = r"C:\Users\footb\AI-BS_Matrix\AI-BS_Matrix_Master_Specification.pdf"

# Read Markdown
with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

# Convert Markdown to HTML
html_body = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
)

# Define Beautiful Dark Mode CSS
css_styling = """
@page {
    size: letter portrait;
    margin: 1in;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 9pt;
        color: #8b949e;
    }
    @bottom-left {
        content: "AI-BS Matrix Documentation";
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 9pt;
        color: #8b949e;
    }
}

body {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
}

h1 {
    color: #39ff14;
    font-size: 28pt;
    border-bottom: 2px solid #39ff14;
    padding-bottom: 10px;
    margin-bottom: 20px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

h2 {
    color: #58a6ff;
    font-size: 18pt;
    border-bottom: 1px solid #30363d;
    padding-bottom: 5px;
    margin-top: 30px;
}

h3 {
    color: #c9d1d9;
    font-size: 14pt;
    margin-top: 25px;
}

p {
    margin-bottom: 15px;
}

ul, ol {
    margin-bottom: 15px;
    padding-left: 25px;
}

li {
    margin-bottom: 5px;
}

strong, b {
    color: #fff;
    font-weight: 600;
}

code {
    background-color: #161b22;
    color: #ff7b72;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 10pt;
    border: 1px solid #30363d;
}

blockquote {
    border-left: 4px solid #39ff14;
    padding-left: 15px;
    margin-left: 0;
    color: #8b949e;
    background-color: rgba(57, 255, 20, 0.05);
    padding: 10px 15px;
    border-radius: 0 4px 4px 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

th, td {
    border: 1px solid #30363d;
    padding: 10px;
    text-align: left;
}

th {
    background-color: #161b22;
    color: #58a6ff;
}

hr {
    border: 0;
    height: 1px;
    background: #30363d;
    margin: 30px 0;
}
"""

# Construct Final HTML Document
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AI-BS Matrix Specification</title>
    <style>
        {css_styling}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

# Render PDF using WeasyPrint
print("Rendering PDF...")
weasyprint.HTML(string=full_html).write_pdf(pdf_path)
print(f"Success! PDF generated at: {pdf_path}")
