import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Decision Report | MLB In-Game Decision Analytics",
  description:
    "Grading in-game baseball decisions with run expectancy. Built for front offices.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.className} bg-gray-50 text-slate-900 antialiased min-h-screen flex flex-col`}>
        <Nav />
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 mt-16 py-8 text-center text-xs text-slate-400 space-y-1">
          <p>Decision Report · Data: MLB Statcast, Baseball Reference, Baseball Savant · 2020–2024</p>
          <p>
            This tool grades decision-making, not player ability. All grades reflect expected value
            at the moment of the call, not the outcome of the individual play.
          </p>
        </footer>
      </body>
    </html>
  );
}
