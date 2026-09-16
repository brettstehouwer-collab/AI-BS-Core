/**
 * FountainAdapter.js
 * Converts basic Fountain text into the Unified AST, and AST back to Fountain.
 */

export function fountainToAST(fountainText) {
  const ast = [];
  const lines = fountainText.split('\n');
  
  let i = 0;
  while (i < lines.length) {
    let line = lines[i];
    
    if (line.trim() === '') {
      i++;
      continue;
    }
    
    // Scene Heading
    if (line.match(/^(INT\.|EXT\.|INT\/EXT\.|EST\.|I\/E\.)/i) || line.startsWith('.')) {
      ast.push({ id: crypto.randomUUID(), type: "Scene Heading", text: line.replace(/^\./, '') });
      i++;
      continue;
    }
    
    // Transition
    if (line.match(/TO:$/) || line.startsWith('>')) {
      ast.push({ id: crypto.randomUUID(), type: "Transition", text: line.replace(/^>/, '').replace(/<$/, '').trim() });
      i++;
      continue;
    }
    
    // Character & Dialogue Block
    if (line.match(/^[A-Z][A-Z0-9 \-\.()\^]+$/) && !line.match(/^(INT\.|EXT\.)/i) && i + 1 < lines.length && lines[i+1].trim() !== '') {
      let charName = line.trim();
      let isDual = false;
      if (charName.endsWith('^')) {
          isDual = true;
          charName = charName.slice(0, -1).trim();
      }
      ast.push({ id: crypto.randomUUID(), type: "Character", text: charName, ...(isDual && { dual: true }) });
      i++;
      
      while (i < lines.length && lines[i].trim() !== '') {
        const dialogLine = lines[i].trim();
        if (dialogLine.startsWith('(') && dialogLine.endsWith(')')) {
          ast.push({ id: crypto.randomUUID(), type: "Parenthetical", text: dialogLine });
        } else {
          // Check if previous was dialogue, if so append, else create new
          const lastAST = ast[ast.length - 1];
          if (lastAST.type === "Dialogue") {
             lastAST.text += " " + dialogLine;
          } else {
             ast.push({ id: crypto.randomUUID(), type: "Dialogue", text: dialogLine });
          }
        }
        i++;
      }
      continue;
    }
    
    // Action (fallback)
    const lastAST = ast[ast.length - 1];
    if (lastAST && lastAST.type === "Action") {
       lastAST.text += " " + line.trim();
    } else {
       ast.push({ id: crypto.randomUUID(), type: "Action", text: line.trim() });
    }
    i++;
  }
  
  if (ast.length === 0) {
    ast.push({ id: crypto.randomUUID(), type: "Action", text: "" });
  }
  
  return ast;
}

export function astToFountain(ast) {
  let text = "";
  for (let i = 0; i < ast.length; i++) {
    const block = ast[i];
    
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
