import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: Request) {
  try {
    const forwarded = request.headers.get("x-forwarded-for");
    const ip = forwarded ? forwarded.split(/, /)[0] : "127.0.0.1";
    const userAgent = request.headers.get("user-agent") || "Unknown";

    // Registra la visita se non è già stata registrata di recente per questo IP (opzionale, qui registriamo tutto)
    await prisma.visitor.create({
      data: {
        ip: ip,
        userAgent: userAgent,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Visitor API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
