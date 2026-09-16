import os
import sys
import time
import uuid
import tempfile
import subprocess
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("TypstPandocEngine")

OUTPUT_DIR = r"C:\AI-BS\saved_data\publications"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TYPST_EXE_PATHS = [
    r"C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\typst.exe",
    r"C:\Program Files\Typst\typst.exe",
    "typst.exe",
    "typst"
]

PANDOC_EXE_PATHS = [
    r"C:\Users\footb\AppData\Local\Microsoft\WinGet\Links\pandoc.exe",
    r"C:\Program Files\Pandoc\pandoc.exe",
    "pandoc.exe",
    "pandoc"
]


def _find_binary(candidates: List[str]) -> Optional[str]:
    for path in candidates:
        if os.path.isabs(path) and os.path.exists(path):
            return path
        try:
            res = subprocess.run(["where", path], capture_output=True, text=True, shell=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().splitlines()[0]
        except Exception:
            pass
    return None


class TypstPandocEngine:
    """
    Sovereign Typst & Pandoc Publishing Engine for Stehouwer Publishing LLC.
    Delivers sub-50ms PDF compilation, KDP-compliant print templates, and multi-format conversion.
    """

    @staticmethod
    def compile_typst(
        markup_text: str,
        output_pdf_path: Optional[str] = None,
        title: str = "Stehouwer Publishing Document",
        author: str = "Brett Stehouwer",
        trim_size: str = "6x9",
        line_numbers: bool = False
    ) -> Dict[str, Any]:
        """
        Compiles Typst markup text directly into a print-ready PDF using fast C-bindings or CLI fallback.
        """
        start_time = time.time()
        session_id = f"pub_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        if not output_pdf_path:
            output_pdf_path = os.path.join(OUTPUT_DIR, f"{session_id}.pdf")

        # Normalize trim size
        dim_map = {
            "6x9": ("6in", "9in", "(inside: 0.75in, outside: 0.5in, top: 0.6in, bottom: 0.6in)"),
            "8.5x11": ("8.5in", "11in", "(inside: 0.8in, outside: 0.6in, top: 0.75in, bottom: 0.75in)"),
            "5.5x8.5": ("5.5in", "8.5in", "(inside: 0.7in, outside: 0.5in, top: 0.5in, bottom: 0.5in)"),
            "a4": ("a4", "a4", "(inside: 2cm, outside: 1.5cm, top: 2cm, bottom: 2cm)"),
        }
        width, height, margins = dim_map.get(trim_size.lower(), dim_map["6x9"])

        # Check if full Typst document or raw snippet
        if not markup_text.strip().startswith("#set") and not markup_text.strip().startswith("#show"):
            # Wrap in standard Stehouwer Publishing KDP template
            full_doc = f"""
#set page(
  paper: "{trim_size.lower() if trim_size.lower() in ['a4', 'us-letter'] else 'us-trade'}",
  width: {width},
  height: {height},
  margin: {margins},
  header: align(right)[
    #text(size: 8pt, fill: rgb("64748b"))[{title}]
  ],
  footer: [
    #align(center)[
      #text(size: 8pt, fill: rgb("64748b"))[#context counter(page).display()]
    ]
  ]
)

#set text(
  font: ("Linux Libertine", "Times New Roman", "Georgia"),
  size: 10.5pt,
  lang: "en"
)

#set par(
  justify: true,
  leading: 0.65em,
  first-line-indent: 1.5em
)

#align(center)[
  #v(2cm)
  #text(size: 20pt, weight: "bold")[{title}] \
  #v(0.5cm)
  #text(size: 12pt, fill: rgb("475569"))[{author}] \
  #v(0.3cm)
  #text(size: 9pt, fill: rgb("94a3b8"))[Stehouwer Publishing LLC • Sovereign Print Edition]
  #v(1.5cm)
]

{markup_text}
"""
        else:
            full_doc = markup_text

        # Try fast Python C-binding first
        pdf_bytes = None
        method_used = "typst-c-binding"
        try:
            import typst
            with tempfile.NamedTemporaryFile(suffix=".typ", mode="w", encoding="utf-8", delete=False) as tf:
                tf.write(full_doc)
                temp_typ = tf.name

            try:
                pdf_bytes = typst.compile(temp_typ)
            finally:
                if os.path.exists(temp_typ):
                    os.remove(temp_typ)
        except Exception as e:
            logger.warning(f"Typst Python binding fallback: {e}")
            # Fallback to typst.exe CLI
            binary = _find_binary(TYPST_EXE_PATHS)
            if binary:
                method_used = "typst-cli-binary"
                with tempfile.NamedTemporaryFile(suffix=".typ", mode="w", encoding="utf-8", delete=False) as tf:
                    tf.write(full_doc)
                    temp_typ = tf.name
                try:
                    cmd = [binary, "compile", temp_typ, output_pdf_path]
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    with open(output_pdf_path, "rb") as pf:
                        pdf_bytes = pf.read()
                finally:
                    if os.path.exists(temp_typ):
                        os.remove(temp_typ)
            else:
                raise RuntimeError(f"Typst compilation failed: {e}")

        if pdf_bytes:
            with open(output_pdf_path, "wb") as pf:
                pf.write(pdf_bytes)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        pdf_size = os.path.getsize(output_pdf_path) if os.path.exists(output_pdf_path) else len(pdf_bytes or b"")

        return {
            "status": "success",
            "session_id": session_id,
            "title": title,
            "trim_size": trim_size,
            "method": method_used,
            "elapsed_ms": elapsed_ms,
            "pdf_path": output_pdf_path,
            "pdf_filename": os.path.basename(output_pdf_path),
            "file_size_bytes": pdf_size,
            "download_url": f"/api/v1/publishing/download/{os.path.basename(output_pdf_path)}"
        }

    @staticmethod
    def generate_kdp_manuscript(
        title: str,
        author: str,
        chapters: List[Dict[str, str]],
        subtitle: Optional[str] = None,
        trim_size: str = "6x9",
        isbn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formats structured manuscript chapters into a publication-ready KDP interior PDF.
        """
        body_content = []
        for i, ch in enumerate(chapters, 1):
            ch_title = ch.get("title", f"Chapter {i}")
            ch_text = ch.get("content", "")
            body_content.append(f"""
#pagebreak()
#v(1cm)
#align(center)[
  #text(size: 16pt, weight: "bold")[{ch_title}]
]
#v(0.8cm)

{ch_text}
""")

        full_body = "\n".join(body_content)
        header_title = f"{title}" + (f" — {subtitle}" if subtitle else "")
        return TypstPandocEngine.compile_typst(
            markup_text=full_body,
            title=header_title,
            author=author,
            trim_size=trim_size
        )

    @staticmethod
    def convert_pandoc(
        input_text: str,
        from_format: str = "markdown",
        to_format: str = "typst",
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Converts text across document formats (Markdown, Typst, LaTeX, DOCX, HTML, EPUB) via Pandoc.
        """
        start_time = time.time()
        binary = _find_binary(PANDOC_EXE_PATHS)
        if not binary:
            return {"status": "error", "message": "Pandoc executable not found in PATH."}

        with tempfile.NamedTemporaryFile(suffix=f".{from_format}", mode="w", encoding="utf-8", delete=False) as tf:
            tf.write(input_text)
            temp_input = tf.name

        out_ext = "typ" if to_format == "typst" else to_format
        temp_output = temp_input + f".{out_ext}"

        try:
            cmd = [binary, "-f", from_format, "-t", to_format, temp_input, "-o", temp_output]
            if extra_args:
                cmd.extend(extra_args)

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5400)
            if res.returncode != 0:
                return {
                    "status": "error",
                    "stderr": res.stderr,
                    "returncode": res.returncode
                }

            with open(temp_output, "r", encoding="utf-8", errors="ignore") as of:
                converted_content = of.read()

            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "success",
                "from_format": from_format,
                "to_format": to_format,
                "elapsed_ms": elapsed_ms,
                "output": converted_content
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
