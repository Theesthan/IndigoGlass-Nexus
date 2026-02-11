// =============================================================================
// IndigoGlass Nexus - Root Page (Redirect to Dashboard or Login)
// =============================================================================

import { redirect } from 'next/navigation';

export default function RootPage() {
  // In production, this would check auth state
  redirect('/dashboard');
}
