import React from 'react';
import { FileText } from 'lucide-react';

export default function PdfViewerComponent({ pdfUrl, title = "Research Paper Viewer" }) {
  return (
    <div className="w-full bg-[#0a0a0a] border border-[#3d2b1f] rounded-lg overflow-hidden flex flex-col shadow-lg">
      <div className="px-4 py-3 bg-[#1f1610] border-b border-[#3d2b1f] flex items-center justify-between">
        <div className="flex items-center gap-2 text-[#d4af37]">
          <FileText size={18} />
          <span className="font-semibold text-sm font-serif">{title}</span>
        </div>
      </div>
      <div className="w-full relative bg-slate-950" style={{ height: '600px' }}>
        {pdfUrl ? (
          <iframe 
            src={pdfUrl}
            title="PDF Document"
            className="w-full h-full border-none"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
            <FileText size={48} className="mb-4 opacity-50" />
            <p className="text-sm">No document selected.</p>
            <p className="text-xs opacity-70 mt-2">Run a RAG query to load source PDFs.</p>
          </div>
        )}
      </div>
    </div>
  );
}
