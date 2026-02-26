import { NextRequest, NextResponse } from 'next/server';
import { searchTag } from '@/lib/techrecon';

export async function GET(request: NextRequest) {
  const tag = request.nextUrl.searchParams.get('tag');

  if (!tag) {
    return NextResponse.json(
      { error: 'tag parameter is required' },
      { status: 400 }
    );
  }

  try {
    const data = await searchTag(tag);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Tags error:', error);
    return NextResponse.json(
      { error: 'Failed to search tags' },
      { status: 500 }
    );
  }
}
