import { NextRequest, NextResponse } from 'next/server';
import { searchEvidence } from '@/lib/alg-precision-therapeutics';

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get('query');
  const mondoId = request.nextUrl.searchParams.get('mondo_id');
  if (!query) {
    return NextResponse.json({ error: 'query is required' }, { status: 400 });
  }
  try {
    const data = await searchEvidence(query, mondoId ?? '');
    return NextResponse.json(data);
  } catch (error) {
    console.error('APT search error:', error);
    return NextResponse.json({ error: 'Failed to search evidence' }, { status: 500 });
  }
}
