import { NextResponse } from 'next/server';
import { addNote } from '@/lib/jobhunt';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { about, type, content, name } = body;

    if (!about || !type || !content) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields: about, type, content' },
        { status: 400 }
      );
    }

    const data = await addNote(about, type, content, name);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to add note:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to add note' },
      { status: 500 }
    );
  }
}
