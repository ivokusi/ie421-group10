import { createOpenAI } from "@ai-sdk/openai";
import { AssistantModelMessage, streamText } from "ai";

export const runtime = "edge";
export const maxDuration = 30;

const openai = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY!, 
});

export async function POST(req: Request) {
  
  try {
    const { messages }: { messages: AssistantModelMessage[] } = await req.json();

    const result = streamText({
      model: openai("gpt-4o-mini"),
      messages,
      abortSignal: req.signal,
    });

    return result.toUIMessageStreamResponse();
  } catch (err: any) {
    console.error("Error in /api/chat:", err);

    const message =
      err instanceof Error ? err.message : JSON.stringify(err);

    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

}