"use client"

import { MessageSquarePlus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Chat } from "./chat-interface"
import { cn } from "@/lib/utils"

interface ChatSidebarProps {
  chats: Chat[]
  currentChatId: string
  onSelectChat: (id: string) => void
  onNewChat: () => void
  onDeleteChat: (id: string) => void
}

export default function ChatSidebar({ chats, currentChatId, onSelectChat, onNewChat, onDeleteChat }: ChatSidebarProps) {
  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays === 1) return "Yesterday"
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-sidebar">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-3">
        <h2 className="font-semibold text-sidebar-foreground text-lg">AI Chat</h2>
        <Button onClick={onNewChat} size="icon" variant="ghost" className="h-8 w-8">
          <MessageSquarePlus className="h-5 w-5" />
        </Button>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-1 p-2">
          {chats.map((chat) => (
            <div
              key={chat.id}
              className={cn(
                "group flex items-center justify-between rounded-lg px-3 py-2.5 transition-colors cursor-pointer hover:bg-sidebar-accent",
                currentChatId === chat.id && "bg-sidebar-accent",
              )}
              onClick={() => onSelectChat(chat.id)}
            >
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sidebar-foreground text-sm font-medium">{chat.title}</p>
                <p className="text-muted-foreground text-xs">{formatTimestamp(chat.timestamp)}</p>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteChat(chat.id)
                }}
                title="Delete chat"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <p className="text-muted-foreground text-xs text-center">Powered by GPT-5</p>
      </div>
    </aside>
  )
}
