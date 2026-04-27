import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name, email, project } = body;
    
    // Ottieni l'indirizzo IP
    const forwarded = request.headers.get("x-forwarded-for");
    const ip = forwarded ? forwarded.split(/, /)[0] : "127.0.0.1";

    if (!name || !email || !project) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const newMessage = await prisma.message.create({
      data: {
        name,
        email,
        project,
        ip: ip,
      },
    });

    return NextResponse.json({ success: true, data: newMessage });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
