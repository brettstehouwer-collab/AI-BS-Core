const fs = require("fs");

function readCognitiveMetadata(text) {
  if (typeof text !== 'string') return null;
  let merged = null;
  let runtimeReceiptFrame = false;
  for (const match of text.matchAll(/<!--AI-BS-METADATA:([\s\S]*?)-->/g)) {
    try {
      const value = JSON.parse(match[1]);
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        merged = { ...(merged || {}), ...value };
      }
    } catch (_) {}
  }
  return merged;
}

function parseCognitiveContent(rawContent) {
  if (typeof rawContent !== 'string') {
    return { meta: null, thought: null, body: rawContent, isThinking: false };
  }

  let text = rawContent;
  let meta = null;

  meta = readCognitiveMetadata(text);
  text = text.replace(/<!--AI-BS-METADATA:[\s\S]*?-->/g, '').trimStart();

  let thought = null;
  let body = text;
  let isThinking = false;

  const completeThinkMatch = /<think>([\s\S]*?)<\/think>/.exec(text);
  if (completeThinkMatch) {
    thought = completeThinkMatch[1].trim();
    body = text.replace(/<think>[\s\S]*?<\/think>/, '').trim();
    isThinking = false;
  } else {
    const inProgressThinkMatch = /<think>([\s\S]*)$/.exec(text);
    if (inProgressThinkMatch) {
      thought = inProgressThinkMatch[1].trim();
      body = text.split('<think>')[0].trim();
      isThinking = true;
    }
  }

  return { meta, thought, body, isThinking };
}

const raw = fs.readFileSync("C:/AI-BS/backend/scratch/m22_raw.txt", "utf8");
console.log("Raw length:", raw.length);
console.log("Raw matches of metadata:", [...raw.matchAll(/<!--AI-BS-METADATA:([\s\S]*?)-->/g)].length);
const res = parseCognitiveContent(raw);
console.log("Body length:", res.body.length);
console.log("Body includes AI-BS-METADATA:", res.body.includes("AI-BS-METADATA"));
console.log("--- Body Preview ---");
console.log(res.body.substring(0, 300));
console.log("--- Body End Preview ---");
console.log(res.body.substring(res.body.length - 300));

