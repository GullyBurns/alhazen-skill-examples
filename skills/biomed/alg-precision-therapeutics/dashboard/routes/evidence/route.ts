import { NextRequest, NextResponse } from 'next/server';
import { showEvidence } from '@/lib/alg-precision-therapeutics';

export async function GET(request: NextRequest) {
  const mechanismId = request.nextUrl.searchParams.get('mechanism_id');
  if (!mechanismId) {
    return NextResponse.json({ error: 'mechanism_id is required' }, { status: 400 });
  }
  try {
    const data = await showEvidence(mechanismId);
    return NextResponse.json(data);
  } catch (error) {
    console.error('APT evidence error:', error);
    return NextResponse.json({ error: 'Failed to fetch evidence' }, { status: 500 });
  }
}
