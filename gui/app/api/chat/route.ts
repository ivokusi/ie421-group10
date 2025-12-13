export const runtime = 'edge';
export const maxDuration = 30;

export async function POST(req: Request) {
  try {

    const body = await req.json()
    
    const upstream = await fetch(process.env.N8N_WEBHOOK_URL!, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: { 'content-type': 'application/json' },
    });

  } catch (err: any) {
    const message =
      err instanceof Error ? err.message : JSON.stringify(err);

    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

}
