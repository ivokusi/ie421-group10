"use client"

import type React from "react"
import { Send, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { createClient } from "@/lib/supabase/client"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

interface ChatWindowProps {
  chatId: string
  onUpdateTitle: (id: string, title: string) => void
}

export default function ChatWindow({ chatId, onUpdateTitle }: ChatWindowProps) {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(true)
  const [hasSetTitle, setHasSetTitle] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadMessages()
  }, [chatId])

  const loadMessages = async () => {
    const supabase = createClient()
    setIsLoadingMessages(true)

    try {
      const { data, error } = await supabase
        .from("messages")
        .select("*")
        .eq("conversation_id", chatId)
        .order("created_at", { ascending: true })

      if (error) throw error

      const loadedMessages: Message[] =
        data?.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
        })) || []

      setMessages(loadedMessages)
      setHasSetTitle(loadedMessages.length > 0)
    } catch (error) {
      console.error("Error loading messages:", error)
    } finally {
      setIsLoadingMessages(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!hasSetTitle && messages.length > 0 && messages[0].role === "user") {
      const title = messages[0].content.slice(0, 50)
      onUpdateTitle(chatId, title)
      setHasSetTitle(true)
    }
  }, [messages, chatId, onUpdateTitle, hasSetTitle])

  const saveMessageToDb = async (role: "user" | "assistant", content: string) => {
    const supabase = createClient()

    try {
      const { data, error } = await supabase
        .from("messages")
        .insert({
          conversation_id: chatId,
          role,
          content,
        })
        .select()
        .single()

      if (error) throw error
      return data.id
    } catch (error) {
      console.error("Error saving message:", error)
      return `temp-${Date.now()}`
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userContent = input
    setInput("")
    setIsLoading(true)

    const userMessageId = await saveMessageToDb("user", userContent)

    const userMessage: Message = {
      id: userMessageId,
      role: "user",
      content: userContent,
    }

    setMessages((prev) => [...prev, userMessage])

    try {
      console.log("Sending messages to API")

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMessage],
        }),
      })

      console.log("Response status:", response.status)
      console.log("Response headers:", Object.fromEntries(response.headers.entries()))

      if (!response.ok) {
        throw new Error("Failed to get response")
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantMessage = ""
      const assistantId = `assistant-${Date.now()}`
      const chunkCount = 0
      let buffer = ""

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          buffer += chunk

          const lines = buffer.split("\n")
          buffer = lines.pop() || ""

          for (const line of lines) {
            if (!line.trim()) continue

            if (!line.startsWith("data: ")) {
              continue
            }

            const jsonStr = line.slice(6).trim()

            if (jsonStr === "[DONE]") {
              continue
            }

            try {
              const parsed = JSON.parse(jsonStr)

              let deltaText = ""

              if (parsed.type === "text-delta" && parsed.delta) {
                deltaText = parsed.delta
              } else if (parsed.object === "chat.completion.chunk" && parsed.choices?.[0]?.delta?.content) {
                deltaText = parsed.choices[0].delta.content
              }

              if (deltaText) {
                assistantMessage += deltaText

                setMessages((prev) => {
                  const filtered = prev.filter((m) => m.id !== assistantId)
                  return [...filtered, { id: assistantId, role: "assistant", content: assistantMessage }]
                })
              }
            } catch (e) {
              continue
            }
          }
        }
      }

      console.log("Final assistant message length:", assistantMessage.length)
      console.log("Final assistant message:", assistantMessage)

      if (assistantMessage) {
        const savedAssistantId = await saveMessageToDb("assistant", assistantMessage)

        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, id: savedAssistantId } : m)))
      }
    } catch (error) {
      console.error("Chat error:", error)
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  if (isLoadingMessages) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">Loading messages...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-8">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <Bot className="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
                <h2 className="mb-2 font-semibold text-2xl text-foreground">Start a conversation</h2>
                <p className="text-muted-foreground">Ask me anything and I'll do my best to help!</p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn("flex gap-4", message.role === "user" ? "justify-end" : "justify-start")}
                >
                  {message.role === "assistant" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary">
                      <Bot className="h-5 w-5 text-primary-foreground" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[80%] rounded-2xl px-4 py-3",
                      message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                    )}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                  </div>
                  {message.role === "user" && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent">
                      <User className="h-5 w-5 text-accent-foreground" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary">
                    <Bot className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <div className="flex items-center gap-1 rounded-2xl bg-muted px-4 py-3">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground [animation-delay:-0.3s]"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground [animation-delay:-0.15s]"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-foreground"></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card">
        <div className="mx-auto max-w-3xl px-4 py-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              className="min-h-[60px] max-h-32 resize-none bg-background"
              disabled={isLoading}
            />
            <Button
              type="submit"
              size="icon"
              className="h-[60px] w-[60px] shrink-0"
              disabled={!input.trim() || isLoading}
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
          <p className="mt-2 text-center text-muted-foreground text-xs">
            Press Enter to send, Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
