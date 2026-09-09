import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'Card Lab — Sports Card Research',description:'Read your graded sports-card label and research the card, market evidence, and player with your AI Agent workflow.'};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>;}

