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

    const { messages } = await req.json();

    // Call OpenAI with streaming enabled
    const openaiRes = await fetch(
      "https://api.openai.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4.1-mini", // or "gpt-4o-mini" if you prefer
          messages,
          stream: true,
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

    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    // Transform OpenAI's SSE into your {type:"text-delta", delta:"..."} format
    const stream = new ReadableStream({
      async start(controller) {
        const reader = openaiRes.body!.getReader();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process line-by-line
            let newlineIndex: number;
            while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
              const line = buffer.slice(0, newlineIndex).trim();
              buffer = buffer.slice(newlineIndex + 1);

              if (!line || !line.startsWith("data:")) continue;

              const payload = line.slice(5).trim(); // after "data:"

              if (payload === "[DONE]") {
                // Send final DONE marker in the same format your client expects
                controller.enqueue(encoder.encode("data: [DONE]\n\n"));
                controller.close();
                return;
              }

              try {
                const json = JSON.parse(payload);
                const delta =
                  json.choices?.[0]?.delta?.content ?? "";

                if (delta) {
                  const out = JSON.stringify({
                    type: "text-delta",
                    delta,
                  });
                  controller.enqueue(
                    encoder.encode(`data: ${out}\n\n`)
                  );
                }
              } catch {
                // ignore parse errors on weird control messages
              }
            }
          }

          // just in case, close if we exit loop without [DONE]
          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          controller.close();
        } catch (err) {
          controller.error(err);
        }
      },
    });

    return new Response(stream, {
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
