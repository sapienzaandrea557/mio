import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Syne } from "next/font/google";
import "./globals.css";

const sans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-sans" });
const display = Syne({ subsets: ["latin"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "Web Creator Freelance",
  description: "Sito personale di Andrea.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it" className="bg-[#f0f2f5] selection:bg-indigo-500 selection:text-white scroll-smooth" dir="ltr">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
      </head>
      <body className={`${sans.variable} ${display.variable} font-sans text-dark overflow-x-hidden bg-[#f0f2f5] grain-overlay antialiased`}>
        {children}
      </body>
    </html>
  );
}
