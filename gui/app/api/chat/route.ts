import { openai } from "@ai-sdk/openai";
import { AssistantModelMessage, streamText } from "ai";

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages }: { messages: AssistantModelMessage[] } = await req.json();

  const result = streamText({
    model: openai("gpt-4o-mini"),
    messages,
    abortSignal: req.signal,
  });

  return result.toUIMessageStreamResponse();
}
