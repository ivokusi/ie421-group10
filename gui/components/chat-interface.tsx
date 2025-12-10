"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { createClient } from "@/lib/supabase/client"
import ChatSidebar from "./chat-sidebar"
import ChatWindow from "./chat-window"

export interface Chat {
  id: string
  title: string
  timestamp: Date
}

interface ChatInterfaceProps {
  userId: string
}

export default function ChatInterface({ userId }: ChatInterfaceProps) {
  const [chats, setChats] = useState<Chat[]>([])
  const [currentChatId, setCurrentChatId] = useState<string>("")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const hasCreatedInitialChat = useRef(false)

  useEffect(() => {
    loadChats()
  }, [userId])

  const loadChats = async () => {
    const supabase = createClient()
    setIsLoading(true)
    setError(null)

    try {
      console.log("Loading chats for user:", userId)

      const { data, error } = await supabase
        .from("conversations")
        .select("*")
        .eq("user_id", userId)
        .order("updated_at", { ascending: false })

      if (error) {
        console.error("Database error details:", {
          message: error.message,
          details: error.details,
          hint: error.hint,
          code: error.code,
        })
        throw error
      }

      console.log("Loaded conversations:", data)

      const loadedChats: Chat[] =
        data?.map((conv) => ({
          id: conv.id,
          title: conv.title,
          timestamp: new Date(conv.created_at),
        })) || []

      setChats(loadedChats)

      if (loadedChats.length > 0) {
        setCurrentChatId(loadedChats[0].id)
        hasCreatedInitialChat.current = false
      } else {
        if (!hasCreatedInitialChat.current) {
          hasCreatedInitialChat.current = true
          handleNewChat()
        }
      }
    } catch (error: any) {
      console.error("Error loading chats:", error)
      setError(error?.message || "Failed to load chats. Please make sure the database tables are created.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = async () => {
    const supabase = createClient()

    try {
      const { data, error } = await supabase
        .from("conversations")
        .insert({
          user_id: userId,
          title: "New Chat",
        })
        .select()
        .single()

      if (error) throw error

      const newChat: Chat = {
        id: data.id,
        title: data.title,
        timestamp: new Date(data.created_at),
      }

      setChats((prev) => [newChat, ...prev])
      setCurrentChatId(newChat.id)
    } catch (error) {
      console.error("Error creating chat:", error)
    }
  }

  const handleDeleteChat = async (id: string) => {
    const supabase = createClient()

    try {
      const { error } = await supabase.from("conversations").delete().eq("id", id)

      if (error) throw error

      setChats((prevChats) => {
        const updatedChats = prevChats.filter((chat) => chat.id !== id)

        if (currentChatId === id) {
          if (updatedChats.length > 0) {
            setCurrentChatId(updatedChats[0].id)
          } else {
            setCurrentChatId("")
          }
        }

        return updatedChats
      })

      if (chats.filter((chat) => chat.id !== id).length === 0) {
        setTimeout(() => {
          handleNewChat()
        }, 100)
      }
    } catch (error) {
      console.error("Error deleting chat:", error)
    }
  }

  const handleUpdateChatTitle = useCallback(
    async (id: string, title: string) => {
      const supabase = createClient()

      try {
        const { error } = await supabase
          .from("conversations")
          .update({ title, updated_at: new Date().toISOString() })
          .eq("id", id)

        if (error) throw error

        setChats((prevChats) => prevChats.map((chat) => (chat.id === id ? { ...chat, title } : chat)))
      } catch (error) {
        console.error("Error updating chat title:", error)
      }
    },
    [userId],
  )

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <p className="text-muted-foreground">Loading chats...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="max-w-md rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <h3 className="mb-2 text-lg font-semibold text-destructive">Database Error</h3>
          <p className="mb-4 text-sm text-muted-foreground">{error}</p>
          <p className="text-xs text-muted-foreground">
            Please run the SQL script in{" "}
            <code className="rounded bg-muted px-1 py-0.5">scripts/001_create_chat_tables.sql</code> to create the
            necessary database tables.
          </p>
          <button
            onClick={() => loadChats()}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-full">
      <ChatSidebar
        chats={chats}
        currentChatId={currentChatId}
        onSelectChat={setCurrentChatId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />
      {currentChatId && <ChatWindow key={currentChatId} chatId={currentChatId} onUpdateTitle={handleUpdateChatTitle} />}
    </div>
  )
}
