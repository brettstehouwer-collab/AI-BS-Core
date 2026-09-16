import re
from typing import Dict, List, Any, Tuple

class SovereignDocumentEngine:
    """
    Sovereign Document Context Engine for AI-BS BS-Chat.
    Intelligently parses, indexes, and slices large attached files (.md, .txt, .json, .py, etc.)
    so that local models (like stehouwer_llm with 8,192 token limit) can ingest documents of ANY size
    without crashing, overflowing context, or dropping connections.
    """

    MAX_SAFE_DOC_CHARS = 22000  # ~5,500 tokens, safely leaves ~2,600 tokens for system prompt + response

    @classmethod
    def parse_attachments_and_query(cls, raw_prompt: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extracts attached files and the clean user query from the raw chat prompt.
        Format created by ChatTab.jsx:
        [ATTACHED FILE: <name> (<size> KB)]
        ```<ext>
        <content>
        ```
        [USER PROMPT]:
        <user query>
        """
        attachments = []
        user_query = raw_prompt.strip()

        # Regex to find attached file blocks
        pattern = r"\[ATTACHED FILE:\s*([^\(\]]+)(?:\s*\(([^\)]+)\))?\]\s*```([a-zA-Z0-9_\-\.]*)\r?\n([\s\S]*?)\r?\n```"
        matches = list(re.finditer(pattern, raw_prompt))

        if matches:
            for m in matches:
                filename = m.group(1).strip()
                size_str = m.group(2) or "0 KB"
                ext = m.group(3).strip()
                content = m.group(4)
                attachments.append({
                    "filename": filename,
                    "size_str": size_str,
                    "ext": ext,
                    "content": content,
                    "char_len": len(content)
                })

            # Look for [USER PROMPT]:
            user_prompt_marker = "[USER PROMPT]:"
            if user_prompt_marker in raw_prompt:
                user_query = raw_prompt.split(user_prompt_marker, 1)[1].strip()
            else:
                # Remove all attachment blocks from raw_prompt to isolate user query
                stripped = re.sub(pattern, "", raw_prompt).strip()
                user_query = stripped or "Please review and analyze the attached files in detail."

        return attachments, user_query

    @classmethod
    def index_markdown_sections(cls, content: str) -> List[Dict[str, Any]]:
        """
        Detects chapters, headers, and structural divisions in markdown text.
        """
        sections = []
        lines = content.splitlines()
        current_section = None
        current_lines = []
        start_line = 1

        # Patterns for chapters and headers
        header_regex = re.compile(r"^(#{1,4}\s+.*|CHAPTER\s+[0-9IVXLCDM]+.*|Chapter\s+[0-9IVXLCDM]+.*)", re.IGNORECASE)

        for idx, line in enumerate(lines, start=1):
            match = header_regex.match(line.strip())
            if match:
                if current_section is not None:
                    sections.append({
                        "title": current_section,
                        "start_line": start_line,
                        "end_line": idx - 1,
                        "content": "\n".join(current_lines),
                        "char_len": sum(len(l) + 1 for l in current_lines)
                    })
                current_section = match.group(1).strip()
                current_lines = [line]
                start_line = idx
            else:
                if current_section is None:
                    current_section = "Preamble / Introduction"
                    start_line = 1
                current_lines.append(line)

        if current_section is not None and current_lines:
            sections.append({
                "title": current_section,
                "start_line": start_line,
                "end_line": len(lines),
                "content": "\n".join(current_lines),
                "char_len": sum(len(l) + 1 for l in current_lines)
            })

        return sections

    @classmethod
    def optimize_document_for_context(cls, attachment: Dict[str, Any], user_query: str) -> str:
        """
        Takes an attachment and formats it into an optimized context payload that stays
        within the 8,192 token window while maximizing informative depth.
        """
        content = attachment["content"]
        filename = attachment["filename"]
        size_str = attachment["size_str"]
        total_chars = len(content)

        # Case 1: Fits comfortably within token limits
        if total_chars <= cls.MAX_SAFE_DOC_CHARS:
            return (
                f"[ATTACHED FILE: {filename} ({size_str}) — Complete Ingestion]\n"
                f"```{attachment.get('ext', 'md')}\n"
                f"{content}\n"
                f"```"
            )

        # Case 2: Large document (> 22,000 chars, e.g. Matthew.md at 133,000 chars)
        sections = cls.index_markdown_sections(content)
        user_q_lower = user_query.lower()

        # Check if user is asking about specific chapters or sections
        targeted_sections = []
        if sections:
            for s in sections:
                title_lower = s["title"].lower()
                # Check for chapter number match e.g. "chapter 1", "chapter 5", "ch 1"
                words = re.findall(r"\b(?:chapter\s+\d+|ch\s*\d+|\d+)\b", user_q_lower)
                for w in words:
                    num_match = re.search(r"\d+", w)
                    if num_match and re.search(rf"\b(?:chapter\s+{num_match.group(0)}|{num_match.group(0)})\b", title_lower):
                        targeted_sections.append(s)
                        break
                # Check for topic match in title
                if not targeted_sections:
                    clean_title = re.sub(r"[#*_]", "", title_lower).strip()
                    if clean_title in user_q_lower or any(part in clean_title for part in user_q_lower.split() if len(part) > 4):
                        targeted_sections.append(s)

        # If user asked for specific sections, deliver those in full detail
        if targeted_sections:
            targeted_text = "\n\n---\n\n".join(
                f"### {s['title']} (Lines {s['start_line']}–{s['end_line']}):\n{s['content']}"
                for s in targeted_sections
            )
            # If targeted text is still within bounds
            if len(targeted_text) <= cls.MAX_SAFE_DOC_CHARS:
                section_titles = ", ".join(s["title"] for s in targeted_sections)
                return (
                    f"[ATTACHED FILE: {filename} ({size_str}) — Target Sections Extracted: {section_titles}]\n"
                    f"```{attachment.get('ext', 'md')}\n"
                    f"{targeted_text}\n"
                    f"```\n"
                    f"*(Extracted from full {total_chars:,} character document across {len(sections)} indexed sections)*"
                )

        # Case 3: Comprehensive Structural Indexing & Multi-Window Synthesis
        # Construct a table of contents + opening chapters + key middle excerpts + conclusion
        total_lines = len(content.splitlines())
        word_count = len(content.split())
        
        toc_lines = []
        for i, s in enumerate(sections, start=1):
            toc_lines.append(f"  {i}. {s['title']} (Lines {s['start_line']}–{s['end_line']}, ~{s['char_len']} chars)")
        toc_summary = "\n".join(toc_lines[:35])  # Up to 35 sections listed
        if len(sections) > 35:
            toc_summary += f"\n  ... and {len(sections) - 35} additional chapters."

        # Budget allocation:
        # 1. Opening Section/Chapter (~8,000 chars)
        # 2. Key Middle Samples (~6,000 chars)
        # 3. Culminating Section/Chapter (~6,000 chars)
        open_chunk = ""
        mid_chunk = ""
        tail_chunk = ""

        if sections and len(sections) >= 3:
            # First 1-2 chapters
            open_sections = sections[:2]
            open_chunk = "\n\n".join(f"### {s['title']}:\n{s['content']}" for s in open_sections)
            if len(open_chunk) > 9000:
                open_chunk = open_chunk[:9000] + "\n... [Chapter continued]"

            # Middle chapter (e.g. Chapter 14 or midpoint)
            mid_idx = len(sections) // 2
            mid_section = sections[mid_idx]
            mid_chunk = f"### {mid_section['title']} (Midpoint Milestone):\n{mid_section['content'][:5000]}\n... [Midpoint continued]"

            # Final 1-2 chapters
            tail_sections = sections[-2:]
            tail_chunk = "\n\n".join(f"### {s['title']}:\n{s['content']}" for s in tail_sections)
            if len(tail_chunk) > 7000:
                tail_chunk = tail_chunk[:7000] + "\n... [Final Chapter concluded]"
        else:
            # Document has no clear section headers, use head + mid + tail slicing
            slice_size = 6500
            open_chunk = content[:slice_size] + "\n\n... [Continuing Document Segment] ..."
            mid_start = (total_chars // 2) - (slice_size // 2)
            mid_chunk = "... [Mid-Document Section] ...\n\n" + content[mid_start:mid_start + slice_size] + "\n\n... [Continuing to Conclusion] ..."
            tail_chunk = "... [Culminating Document Section] ...\n\n" + content[-slice_size:]

        optimized_block = (
            f"[ATTACHED FILE: {filename} ({size_str}) — High-Capacity Smart Index Ingestion]\n"
            f"**Document Telemetry:** {total_lines:,} lines | {word_count:,} words | {total_chars:,} bytes | {len(sections)} Structural Chapters Indexed\n\n"
            f"**Comprehensive Chapter Index:**\n{toc_summary}\n\n"
            f"**Detailed Content Windows (Ingested for Analysis):**\n\n"
            f"--- [PART 1: OPENING CHAPTERS & FOUNDATIONAL THESIS] ---\n{open_chunk}\n\n"
            f"--- [PART 2: MIDPOINT DEVELOPMENT & CORE MILESTONES] ---\n{mid_chunk}\n\n"
            f"--- [PART 3: CULMINATING CHAPTERS & RESOLUTION] ---\n{tail_chunk}\n\n"
            f"*(System Note: The full document has been cataloged. You can ask for granular details on ANY specific chapter or verse, and the Sovereign Engine will instantly retrieve it.)*"
        )
        return optimized_block

    @classmethod
    def prepare_chat_payload(cls, raw_prompt: str) -> Tuple[str, str]:
        """
        Processes raw_prompt:
        Returns:
          1. clean_user_query (for memory vault, tools, and telemetry)
          2. fully_assembled_prompt (with smart document contexts and options configured)
        """
        attachments, user_query = cls.parse_attachments_and_query(raw_prompt)

        if not attachments:
            return user_query, raw_prompt

        processed_doc_blocks = []
        for att in attachments:
            doc_block = cls.optimize_document_for_context(att, user_query)
            processed_doc_blocks.append(doc_block)

        assembled_prompt = "\n\n".join(processed_doc_blocks) + f"\n\n[USER PROMPT]:\n{user_query}"
        return user_query, assembled_prompt
