import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const ArtifactRenderer = ({ content }) => {
  return (
    <div className="artifact-markdown-container">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <div className="code-block-wrapper">
                <div className="code-block-header">
                  <span>{match[1]}</span>
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  className="syntax-highlighter-block"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code className={`inline-code ${className || ''}`} {...props}>
                {children}
              </code>
            );
          },
          blockquote({ node, children, ...props }) {
            // Check for GitHub style alerts inside blockquotes
            // e.g. > [!NOTE], > [!IMPORTANT], > [!WARNING]
            const textContent = node.children
              .filter(child => child.type === 'element' && child.tagName === 'p')
              .map(p => p.children.filter(c => c.type === 'text').map(t => t.value).join(''))
              .join('\n');

            let alertType = null;
            if (textContent.includes('[!NOTE]')) alertType = 'note';
            else if (textContent.includes('[!TIP]')) alertType = 'tip';
            else if (textContent.includes('[!IMPORTANT]')) alertType = 'important';
            else if (textContent.includes('[!WARNING]')) alertType = 'warning';
            else if (textContent.includes('[!CAUTION]')) alertType = 'caution';

            if (alertType) {
              // We need to strip the [!TYPE] from the children rendering
              // This is a simplified approach: just add the class, we'll let CSS hide the tag
              // or we can clean the children. For simplicity, we just add the alert class
              return (
                <blockquote className={`github-alert github-alert-${alertType}`} {...props}>
                  <div className="alert-title">{alertType.toUpperCase()}</div>
                  <div className="alert-content">{children}</div>
                </blockquote>
              );
            }

            return <blockquote {...props}>{children}</blockquote>;
          },
          table({ node, children, ...props }) {
            return (
              <div className="markdown-table-wrapper">
                <table {...props}>{children}</table>
              </div>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default ArtifactRenderer;
