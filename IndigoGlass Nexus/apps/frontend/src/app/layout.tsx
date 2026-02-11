import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'IndigoGlass Nexus | Supply Chain Intelligence',
  description: 'Production-grade Data & AI platform for forecasting demand, optimizing pharma distribution, and reporting sustainability KPIs',
  keywords: ['supply chain', 'AI', 'demand forecasting', 'route optimization', 'sustainability'],
  authors: [{ name: 'IndigoGlass Team' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
