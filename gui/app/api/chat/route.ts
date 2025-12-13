export const runtime = "edge";
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: "Missing OPENAI_API_KEY" }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    const { query, sessionId } = await req.json();
    
    const openaiRes = await fetch(
      "https://n8n.devlopment.net/webhook/query",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          sessionId,    
        }),
      }
    );

    if (!openaiRes.ok || !openaiRes.body) {
      const text = await openaiRes.text();
      return new Response(
        JSON.stringify({
          error: `OpenAI error ${openaiRes.status}: ${text}`,
        }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Proxy OpenAI's SSE stream directly to the client
    return new Response(openaiRes.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
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
