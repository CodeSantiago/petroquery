import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import CursorProvider from "./components/Cursor";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Brain-API | RAG System",
  description: "AI-powered RAG system with Groq",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CursorProvider />
        {children}
      </body>
    </html>
  );
}