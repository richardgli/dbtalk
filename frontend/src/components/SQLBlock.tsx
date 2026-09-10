import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface SQLBlockProps {
  sql?: string;
}

export default function SQLBlock({ sql }: SQLBlockProps) {
  const [open, setOpen] = useState(false);

  if (!sql) return null;

  return (
    <div className="sql-block">
      <button
        className="sql-block__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="sql-block__chevron" data-open={open}>›</span>
        generated sql
      </button>
      {open && (
        <SyntaxHighlighter
          language="sql"
          style={oneDark}
          customStyle={{
            margin: 0,
            fontSize: '12.5px',
            borderRadius: '6px',
            padding: '10px 12px',
            scrollbarWidth: 'thin',
            scrollbarColor: '#8da9c4ff transparent',
          }}
        >
          {sql}
        </SyntaxHighlighter>
      )}
    </div>
  );
}