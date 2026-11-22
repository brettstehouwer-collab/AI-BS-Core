// Shared editor layout estimate. Export/PDF pagination remains renderer-specific.
/** @typedef {import("/types/domain").ScreenplayBlock} ScreenplayBlock */
/** @param {ScreenplayBlock} block */
export function estimateScreenplayBlockLines(block) {
  const length = Math.max(1, (block.text || '').length);
  switch (block.type) {
    case 'Scene Heading':
    case 'Action': return 1 + Math.ceil(length / 60);
    case 'Character': return 1 + Math.ceil(length / 38);
    case 'Parenthetical': return Math.ceil(length / 20);
    case 'Dialogue': return Math.ceil(length / 35);
    case 'Transition': return 1 + Math.ceil(length / 20);
    default: return 1;
  }
}

/**
 * @param {ScreenplayBlock[]} ast
 * @returns {{blocks: ScreenplayBlock[], startIndex: number, endIndex: number, estimatedLines: number}[]}
 * Consumers add dynamic display-only block fields (for example dual dialogue).
 */
export function paginateScreenplayBlocks(ast = []) {
  /** @type {{blocks: ScreenplayBlock[], startIndex: number, endIndex: number, estimatedLines: number}[]} */
  const pages = [];
  /** @type {ScreenplayBlock[]} */
  let blocks = [];
  let lines = 0;
  let startIndex = 0;
  // Source pages/manual breaks are explicit boundaries, independent of the
  // approximate editor line budget. This is not a claim about an external FDX app.
  const explicitPages = ast.some(block => block.startsNewPage || Number.isSafeInteger(block.sourcePage));
  ast.forEach((block, index) => {
    const count = estimateScreenplayBlockLines(block);
    if ((block.startsNewPage || (!explicitPages && lines + count > 54)) && blocks.length) {
      pages.push({ blocks, startIndex, endIndex: index, estimatedLines: lines });
      blocks = [];
      lines = 0;
      startIndex = index;
    }
    blocks.push(block);
    lines += count;
  });
  if (blocks.length) pages.push({ blocks, startIndex, endIndex: ast.length, estimatedLines: lines });
  return pages;
}
