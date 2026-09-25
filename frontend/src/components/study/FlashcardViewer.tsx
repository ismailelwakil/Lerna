import React, { useState } from 'react';
import { RotateCcw, ChevronLeft, ChevronRight } from 'lucide-react';

interface Flashcard {
  front: string;
  back: string;
}

interface FlashcardViewerProps {
  content: string;
  className?: string;
}

export const FlashcardViewer: React.FC<FlashcardViewerProps> = ({ content, className = '' }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  // Parse markdown flashcards
  const cards: Flashcard[] = [];
  const lines = content.split('\n');
  let currentFront = '';
  let currentBack = '';
  let inBack = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('**Card') || trimmed.startsWith('### Card') || trimmed.startsWith('---')) {
      if (currentFront && currentBack) {
        cards.push({ front: currentFront.trim(), back: currentBack.trim() });
        currentFront = '';
        currentBack = '';
        inBack = false;
      }
    } else if (trimmed.startsWith('Front:') || trimmed.startsWith('Q:') || trimmed.startsWith('**Question:**') || trimmed.startsWith('Question:')) {
      if (currentFront && currentBack) {
        cards.push({ front: currentFront.trim(), back: currentBack.trim() });
        currentFront = '';
        currentBack = '';
      }
      currentFront = trimmed.replace(/^(Front:|Q:|\*\*Question:\*\*|Question:)/, '').trim();
      inBack = false;
    } else if (trimmed.startsWith('Back:') || trimmed.startsWith('A:') || trimmed.startsWith('**Answer:**') || trimmed.startsWith('Answer:')) {
      currentBack = trimmed.replace(/^(Back:|A:|\*\*Answer:\*\*|Answer:)/, '').trim();
      inBack = true;
    } else if (trimmed) {
      if (inBack) {
        currentBack += ' ' + trimmed;
      } else if (currentFront) {
        currentFront += ' ' + trimmed;
      }
    }
  }
  if (currentFront && currentBack) {
    cards.push({ front: currentFront.trim(), back: currentBack.trim() });
  }

  // Fallback if parsing didn't find specific Q/A markers
  if (cards.length === 0) {
    return (
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm font-mono whitespace-pre-wrap">
        {content}
      </div>
    );
  }

  const card = cards[currentIndex % cards.length];

  const handleNext = () => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev + 1) % cards.length);
  };

  const handlePrev = () => {
    setFlipped(false);
    setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length);
  };

  return (
    <div className={`flex flex-col items-center space-y-4 ${className}`}>
      <div className="flex items-center justify-between w-full max-w-lg text-xs font-medium text-slate-500">
        <span>
          Card {(currentIndex % cards.length) + 1} of {cards.length}
        </span>
        <button
          onClick={() => setFlipped(!flipped)}
          className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Click to flip
        </button>
      </div>

      <div
        onClick={() => setFlipped(!flipped)}
        className="w-full max-w-lg min-h-[220px] p-6 bg-white border border-slate-200 rounded-2xl shadow-sm cursor-pointer flex flex-col justify-center items-center text-center transition-all hover:shadow-md relative select-none"
      >
        <span className="absolute top-4 left-4 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-500">
          {flipped ? 'Answer' : 'Question'}
        </span>

        <div className="text-base font-medium text-slate-800 max-w-md leading-relaxed">
          {flipped ? card.back : card.front}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handlePrev}
          className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button
          onClick={() => setFlipped(!flipped)}
          className="px-4 py-2 bg-indigo-50 text-indigo-700 font-medium text-xs rounded-lg hover:bg-indigo-100"
        >
          {flipped ? 'Show Question' : 'Reveal Answer'}
        </button>
        <button
          onClick={handleNext}
          className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
