import { NextResponse } from 'next/server';
import { listAttention } from '@/lib/jobhunt';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type') || 'all';
    const data = await listAttention(type);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to list attention:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch attention data' },
      { status: 500 }
    );
  }
}
