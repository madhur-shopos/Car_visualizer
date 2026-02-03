import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  try {
    const { jobId } = await params;
    
    const response = await fetch(`${BACKEND_URL}/api/download/${jobId}/contact-sheet`, {
      method: 'GET',
    });

    if (!response.ok) {
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    }

    // Stream the image file
    const blob = await response.blob();
    
    return new NextResponse(blob, {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        'Content-Disposition': `attachment; filename="contact_sheet_${jobId}.png"`,
      },
    });
  } catch (error) {
    console.error('Contact sheet download proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to download contact sheet' },
      { status: 500 }
    );
  }
}
