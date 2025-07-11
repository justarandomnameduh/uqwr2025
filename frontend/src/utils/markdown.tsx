import React from 'react';

export const parseMarkdown = (text: string): string => {
  let result = text;
  
  const lines = result.split('\n');
  const processedLines: string[] = [];
  let inList = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    if (trimmedLine.startsWith('* ')) {
      const listContent = trimmedLine.substring(2);
      
      let processedContent = listContent;
      processedContent = processedContent.replace(/`([^`]+?)`/g, '<code class="markdown-code">$1</code>');
      processedContent = processedContent.replace(/\*\*(.*?)\*\*/g, '<strong class="markdown-bold">$1</strong>');
      processedContent = processedContent.replace(/\*([^*]+?)\*/g, (match, p1) => {
        return `<em class="markdown-italic">${p1}</em>`;
      });
      
      if (!inList) {
        processedLines.push('<ul class="markdown-list">');
        inList = true;
      }
      processedLines.push(`<li class="markdown-list-item">${processedContent}</li>`);
    } else {
      if (inList) {
        processedLines.push('</ul>');
        inList = false;
      }
      
      let processedLine = line;
      processedLine = processedLine.replace(/`([^`]+?)`/g, '<code class="markdown-code">$1</code>');
      processedLine = processedLine.replace(/\*\*(.*?)\*\*/g, '<strong class="markdown-bold">$1</strong>');
      processedLine = processedLine.replace(/([^*]|^)\*([^*]+?)\*([^*]|$)/g, '$1<em class="markdown-italic">$2</em>$3');
      
      processedLines.push(processedLine);
    }
  }
  
  // Close list if we end while in one
  if (inList) {
    processedLines.push('</ul>');
  }

  result = '';
  for (let i = 0; i < processedLines.length; i++) {
    const currentLine = processedLines[i];
    const nextLine = processedLines[i + 1];
    
    result += currentLine;
    
    // Add line break only if:
    // 1. Not the last line
    // 2. Current line is not a list item (<li>)
    // 3. Next line is not a list item (<li>)
    // 4. Current line is not <ul> or </ul>
    // 5. Next line is not <ul> or </ul>
    if (i < processedLines.length - 1) {
      const isCurrentListItem = currentLine.includes('<li class="markdown-list-item">');
      const isNextListItem = nextLine.includes('<li class="markdown-list-item">');
      const isCurrentListTag = currentLine.includes('<ul class="markdown-list">') || currentLine.includes('</ul>');
      const isNextListTag = nextLine.includes('<ul class="markdown-list">') || nextLine.includes('</ul>');
      
      if (!isCurrentListItem && !isNextListItem && !isCurrentListTag && !isNextListTag) {
        result += '<br>';
      }
    }
  }
  
  return result;
};

export const MarkdownText: React.FC<{ content: string }> = ({ content }) => {
  const htmlContent = parseMarkdown(content);
  
  return (
    <div 
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}; 