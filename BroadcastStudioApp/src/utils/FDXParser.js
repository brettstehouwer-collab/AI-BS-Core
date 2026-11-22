/**
 * FDXParser.js
 * Parses Final Draft XML (.fdx) into a unified JSON AST for the AI-BS Screenplay Editor.
 */

export function parseFDX(xmlString) {
  const ast = [];
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlString, "text/xml");

  // Basic error checking
  const parseError = xmlDoc.getElementsByTagName("parsererror");
  if (parseError.length > 0) {
    console.error("Error parsing XML:", parseError[0].textContent);
    throw new Error("Failed to parse FDX file. Invalid XML.");
  }

  const paragraphs = xmlDoc.getElementsByTagName("Paragraph");

  for (let i = 0; i < paragraphs.length; i++) {
    const para = paragraphs[i];
    const type = para.getAttribute("Type") || "General";
    
    // Combine all Text nodes within the Paragraph
    const textNodes = para.getElementsByTagName("Text");
    let combinedText = "";
    for (let j = 0; j < textNodes.length; j++) {
      combinedText += textNodes[j].textContent;
    }

    ast.push({
      id: crypto.randomUUID(),
      type: type,
      text: combinedText
    });
  }

  // If file was empty or not FDX
  if (ast.length === 0) {
    ast.push({ id: crypto.randomUUID(), type: "Action", text: "" });
  }

  return ast;
}
