"use client";

import { useEffect, useRef } from "react";

export default function CursorProvider() {
  const cursorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cursor = cursorRef.current;
    if (!cursor) return;

    const onMouseMove = (e: MouseEvent) => {
      cursor.style.transform = `translate3d(${e.clientX - 10}px, ${e.clientY - 10}px, 0)`;
    };

    document.addEventListener('mousemove', onMouseMove);
    return () => document.removeEventListener('mousemove', onMouseMove);
  }, []);

  return (
    <div
      ref={cursorRef}
      className="cursor"
      style={{
        width: 20,
        height: 20,
        border: '2px solid hsl(25 80% 65%)',
        background: 'hsla(25 80% 65% / 0.3)',
        transform: 'translate3d(-10px, -10px, 0)',
      }}
    />
  );
}