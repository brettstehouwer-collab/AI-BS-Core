// Stateful parser for legacy `<!--AI-BS-METADATA:{json}-->` server frames.
//
// Server frames are protocol, never conversation content. They can arrive split
// across arbitrary network chunks, so detection is stateful instead of regex
// over each chunk. The backend escapes model-authored occurrences of the prefix
// as `&lt;!--AI-BS-METADATA:`, which this parser deliberately treats as literal
// prose; any other user/model comment text is passed through untouched.

export const META_PREFIX = '<!--AI-BS-METADATA:';
export const META_SUFFIX = '-->';
export const MAX_FRAME_CHARS = 262144;

export class ChatStreamParser {
  constructor() {
    this.buf = '';
    this.inFrame = false;
    this.overflowed = false;
    this.malformed = 0;
  }

  /** @param {string} chunk @returns {{text: string, frames: string[]}} */
  feed(chunk) {
    this.buf += typeof chunk === 'string' ? chunk : '';
    let text = '';
    const frames = [];
    for (;;) {
      if (this.inFrame) {
        const end = this.buf.indexOf(META_SUFFIX);
        if (end >= 0) {
          const body = this.buf.slice(0, end);
          this.buf = this.buf.slice(end + META_SUFFIX.length);
          this.inFrame = false;
          if (this.overflowed) { this.malformed += 1; this.overflowed = false; }
          else frames.push(body);
          continue;
        }
        if (this.buf.length > MAX_FRAME_CHARS) {
          // Unbounded frame: discard its body, keep scanning for the terminator.
          this.overflowed = true;
          this.buf = this.buf.slice(-(META_SUFFIX.length - 1));
        }
        break;
      }
      const start = this.buf.indexOf(META_PREFIX);
      if (start >= 0) {
        text += this.buf.slice(0, start);
        this.buf = this.buf.slice(start + META_PREFIX.length);
        this.inFrame = true;
        continue;
      }
      // Hold back a trailing partial prefix; it may complete in the next chunk.
      let keep = 0;
      const max = Math.min(this.buf.length, META_PREFIX.length - 1);
      for (let n = 1; n <= max; n += 1) {
        if (META_PREFIX.startsWith(this.buf.slice(-n))) keep = n;
      }
      text += this.buf.slice(0, this.buf.length - keep);
      this.buf = keep ? this.buf.slice(-keep) : '';
      break;
    }
    return { text, frames };
  }

  /** End of stream. An unterminated frame is discarded, never shown as prose. */
  finish() {
    let text = '';
    if (this.inFrame) {
      this.malformed += 1;
    } else {
      text = this.buf; // held partial prefix was ordinary text after all
    }
    this.buf = '';
    this.inFrame = false;
    this.overflowed = false;
    return { text, frames: [], malformed: this.malformed };
  }
}

/** Re-wrap parsed frame bodies so existing frame readers keep working. */
export function frameTextFor(frames) {
  return frames.map(body => META_PREFIX + body + META_SUFFIX).join('\n');
}

/** Remove server frames from already-complete text (legacy stored messages). */
export function stripMetadataFrames(text) {
  if (typeof text !== 'string' || !text.includes(META_PREFIX)) return text;
  const parser = new ChatStreamParser();
  const body = parser.feed(text).text;
  return body + parser.finish().text;
}

/** Parse frame bodies to objects; malformed JSON is ignored, never displayed. */
export function parseFrames(frames) {
  const out = [];
  for (const body of frames) {
    try {
      const value = JSON.parse(body);
      if (value && typeof value === 'object' && !Array.isArray(value)) out.push(value);
    } catch (_) { /* malformed frame is not a receipt */ }
  }
  return out;
}

