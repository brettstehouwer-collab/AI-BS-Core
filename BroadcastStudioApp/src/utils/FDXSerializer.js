/**
 * FDXSerializer.js
 * Comprehensive Final Draft XML (.fdx) serializer for Hollywood & Television Industry parity.
 * Encodes complete ElementSettings, PageLayout, US Letter 8.5"x11" geometry, Courier Final Draft 12pt,
 * and exact Paragraph types & alignments matching Final Draft 12/13, Fade In, and Movie Magic.
 */

function escapeXml(unsafe) {
  if (!unsafe) return "";
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export function serializeFDX(ast = [], metadata = {}) {
  const title = escapeXml(metadata.title || "UNTITLED SCREENPLAY");
  const author = escapeXml(metadata.author || "AI-BS Suite");

  let xml = `<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FinalDraft DocumentType="Script" Template="No" Version="3">
  <ElementSettings Type="General">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="1.25" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Scene Heading">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="Bold+AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="24" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Action">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Character">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="2.20" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Parenthetical">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="-0.10" Leading="Regular" LeftIndent="1.60" RightIndent="2.00" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Dialogue">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="1.00" RightIndent="1.50" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Transition">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Right" FirstIndent="0.00" Leading="Regular" LeftIndent="4.00" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Shot">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="Bold+AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Cast List">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <HeaderAndFooter>
    <Header>
      <Paragraph Alignment="Right" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="0" Spacing="1" StartsNewPage="No">
        <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="">[PageNumber].</Text>
      </Paragraph>
    </Header>
  </HeaderAndFooter>
  <PageLayout BackgroundColor="#FFFFFFFFFFFF" BottomMargin="720" BreakDialogueAndActionAtSentences="Yes" DocumentType="Script" HeaderMargin="360" FooterMargin="360" LeftMargin="1080" RightMargin="720" TopMargin="720">
    <PageSize Height="11.00" Width="8.50"/>
  </PageLayout>
  <Content>
`;

  for (let i = 0; i < ast.length; i++) {
    const block = ast[i];
    const text = block.text || "";
    const escapedText = escapeXml(text);
    const type = block.type || "Action";

    let styleAttr = "";
    if (type === "Scene Heading" || type === "Shot") {
      styleAttr = ' Style="Bold+AllCaps"';
    } else if (type === "Character" || type === "Transition") {
      styleAttr = ' Style="AllCaps"';
    }

    let alignmentAttr = "";
    if (type === "Transition") {
      alignmentAttr = ' Alignment="Right"';
    } else if (block.dual) {
      alignmentAttr = ' Alignment="Left" Number="Dual"';
    }

    xml += `    <Paragraph Type="${type}"${alignmentAttr}>
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12"${styleAttr}>${escapedText}</Text>
    </Paragraph>
`;
  }

  xml += `  </Content>
</FinalDraft>`;

  return xml;
}
