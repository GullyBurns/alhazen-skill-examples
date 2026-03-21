import { NextResponse } from 'next/server';
import { getFigure, listContradictions } from '@/lib/they-said-whaaa';

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  try {
    const [figureData, contraData] = await Promise.all([
      getFigure(params.id),
      listContradictions(params.id),
    ]);

    const figure = figureData as Record<string, unknown>;
    const contra = contraData as Record<string, unknown>;

    return NextResponse.json({
      ...figure,
      contradictions: (contra.contradictions as unknown[]) ?? [],
    });
  } catch (error) {
    console.error('they-said-whaaa /figure/[id] error:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
