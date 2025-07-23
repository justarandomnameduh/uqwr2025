import React from 'react';
import { marked } from 'marked';

interface MarkdownTextProps {
  children: string;
  className?: string;
}

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true,
});

export const MarkdownText: React.FC<MarkdownTextProps> = ({ children, className = '' }) => {
  const htmlContent = marked(children);
  
  return (
    <div 
      className={`prose prose-sm max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}; 