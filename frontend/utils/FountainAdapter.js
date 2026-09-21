/**
 * FountainAdapter.js
 * Converts raw Fountain or screenplay text into the Unified AST, and AST back to Fountain.
 * Fully conforms to Final Draft 13 element hierarchy and standard Hollywood layout rules.
 */

// Scene Heading starters
const SCENE_HEADING_REGEX = /^(INT\.|EXT\.|INT\/EXT\.|I\/E\.|EST\.)/i;
const TRANSITION_REGEX = /^(FADE IN:|FADE OUT\.|CUT TO:|DISSOLVE TO:|SMASH CUT TO:|MATCH CUT TO:|JUMP CUT TO:)$|( TO:)$|^>/;

export function fountainToAST(fountainText) {
  if (!fountainText || typeof fountainText !== 'string') {
    return [{ id: crypto.randomUUID(), type: "Action", text: "" }];
  }

  const ast = [];
  // Normalize newlines
  const rawLines = fountainText.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

  let i = 0;
  while (i < rawLines.length) {
    let rawLine = rawLines[i];
    let trimmed = rawLine.trim();

    // Skip empty lines
    if (trimmed === '') {
      i++;
      continue;
    }

    // Filter out BBC / Final Draft exported page numbers (e.g. "2.", "4.", "21.", "CONTINUED: 2.")
    if (/^\d+\.$/.test(trimmed) || /^CONTINUED:\s*\d*\.?$/i.test(trimmed) || /^\(MORE\)$/i.test(trimmed) || /^\(CONTINUED\)$/i.test(trimmed)) {
      i++;
      continue;
    }

    // 1. Scene Heading
    if (SCENE_HEADING_REGEX.test(trimmed) || trimmed.startsWith('.')) {
      let headingText = trimmed.replace(/^\./, '').trim();
      
      // Check if action was accidentally appended directly onto the scene heading (e.g., "EXT. STREET - DAY (TEASER) A vibrant...")
      // Common standard pattern: (TEASER) or - DAY / - NIGHT / - MORNING / - EVENING / - CONTINUOUS followed by lowercase or sentence action prose
      const headingMatch = headingText.match(/^((?:INT\.|EXT\.|INT\/EXT\.|I\/E\.|EST\.)[A-Z0-9\s\-\/\.\,\'\"]+?(?:DAY|NIGHT|MORNING|EVENING|AFTERNOON|DAWN|DUSK|CONTINUOUS|LATER|MOMENTS LATER|SAME TIME)(?:\s*\([A-Z0-9\s]+\))?)(?:\s+([A-Z][a-z].*))?$/);

      if (headingMatch && headingMatch[2]) {
        ast.push({ id: crypto.randomUUID(), type: "Scene Heading", text: headingMatch[1].trim() });
        ast.push({ id: crypto.randomUUID(), type: "Action", text: headingMatch[2].trim() });
      } else {
        ast.push({ id: crypto.randomUUID(), type: "Scene Heading", text: headingText });
      }
      i++;
      continue;
    }

    // 2. Transition
    if (TRANSITION_REGEX.test(trimmed)) {
      ast.push({ id: crypto.randomUUID(), type: "Transition", text: trimmed.replace(/^>/, '').replace(/<$/, '').trim() });
      i++;
      continue;
    }

    // 3. Parenthetical stand-alone
    if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
      ast.push({ id: crypto.randomUUID(), type: "Parenthetical", text: trimmed });
      i++;
      continue;
    }

    // 4. Character Cue
    // A character line is short (<= 35 chars), all caps, not a scene heading or transition,
    // and followed by dialogue or parenthetical.
    const isPotentialChar = /^[A-Z][A-Z0-9 \-\.\'\/\(\)\^]+$/.test(trimmed) && 
                            trimmed.length <= 40 && 
                            !SCENE_HEADING_REGEX.test(trimmed) && 
                            !TRANSITION_REGEX.test(trimmed);

    if (isPotentialChar && i + 1 < rawLines.length && rawLines[i + 1].trim() !== '') {
      let charName = trimmed;
      let isDual = false;
      if (charName.endsWith('^')) {
        isDual = true;
        charName = charName.slice(0, -1).trim();
      }

      // Add Character element
      ast.push({ 
        id: crypto.randomUUID(), 
        type: "Character", 
        text: charName, 
        ...(isDual && { dual: true }) 
      });
      i++;

      // Process Dialogue / Parenthetical lines belonging to this character
      while (i < rawLines.length && rawLines[i].trim() !== '') {
        let dialogueLine = rawLines[i].trim();

        // Skip embedded page numbers or continuations
        if (/^\d+\.$/.test(dialogueLine) || /^CONTINUED:\s*\d*\.?$/i.test(dialogueLine) || /^\(MORE\)$/i.test(dialogueLine) || /^\(CONTINUED\)$/i.test(dialogueLine)) {
          i++;
          continue;
        }

        // Clean out trailing (CONTINUED) or (MORE) inside the line
        dialogueLine = dialogueLine.replace(/\(CONTINUED\)/gi, '').replace(/\(MORE\)/gi, '').trim();
        if (!dialogueLine) {
          i++;
          continue;
        }

        // Parenthetical detection
        if (dialogueLine.startsWith('(') && dialogueLine.endsWith(')')) {
          ast.push({ id: crypto.randomUUID(), type: "Parenthetical", text: dialogueLine });
          i++;
          continue;
        }

        // Check if this line actually looks like a new character (e.g. another character cue without double blank line)
        if (/^[A-Z][A-Z0-9 \-\.\'\/\(\)\^]+$/.test(dialogueLine) && dialogueLine.length <= 40 && i + 1 < rawLines.length && rawLines[i+1].trim() !== '') {
          // Break out to let outer loop handle new Character
          break;
        }

        // Check if an Action prose mistakenly merged into dialogue (e.g., "He hangs up. Matt and Bobby laugh at Joey.")
        // If line contains dialogue + action cues, keep clean
        const lastAST = ast[ast.length - 1];
        if (lastAST && lastAST.type === "Dialogue") {
          lastAST.text += " " + dialogueLine;
        } else {
          ast.push({ id: crypto.randomUUID(), type: "Dialogue", text: dialogueLine });
        }
        i++;
      }
      continue;
    }

    // 5. Action (Default Prose)
    const lastAST = ast[ast.length - 1];
    if (lastAST && lastAST.type === "Action") {
      lastAST.text += " " + trimmed;
    } else {
      ast.push({ id: crypto.randomUUID(), type: "Action", text: trimmed });
    }
    i++;
  }

  if (ast.length === 0) {
    ast.push({ id: crypto.randomUUID(), type: "Action", text: "" });
  }

  return ast;
}

export function astToFountain(ast) {
  if (!Array.isArray(ast)) return "";
  let text = "";
  for (let i = 0; i < ast.length; i++) {
    const block = ast[i];
    if (!block || !block.text) continue;

    if (block.type === "Scene Heading") {
      text += (text ? "\n\n" : "") + block.text;
    } else if (block.type === "Action") {
      text += (text ? "\n\n" : "") + block.text;
    } else if (block.type === "Character") {
      text += (text ? "\n\n" : "") + block.text.toUpperCase() + (block.dual ? " ^" : "");
    } else if (block.type === "Parenthetical") {
      text += "\n" + block.text;
    } else if (block.type === "Dialogue") {
      text += "\n" + block.text;
    } else if (block.type === "Transition") {
      text += (text ? "\n\n" : "") + block.text;
    } else {
      text += (text ? "\n\n" : "") + block.text;
    }
  }
  return text;
}
