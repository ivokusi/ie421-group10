"use client"

import { useState, useCallback } from "react"
import ChatSidebar from "./chat-sidebar"
import ChatWindow from "./chat-window"

export interface Chat {
  id: string
  title: string
  timestamp: Date
}

export default function ChatInterface() {
  const [chats, setChats] = useState<Chat[]>([])
  const [currentChatId, setCurrentChatId] = useState<string>("")

  const handleNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: "New Chat",
      timestamp: new Date(),
    }
    setChats((prev) => [newChat, ...prev])
    setCurrentChatId(newChat.id)
  }

  const handleDeleteChat = (id: string) => {
    setChats((prevChats) => {
      const updatedChats = prevChats.filter((chat) => chat.id !== id)
      if (currentChatId === id && updatedChats.length > 0) {
        setCurrentChatId(updatedChats[0].id)
      } else if (updatedChats.length === 0) {
        setCurrentChatId("")
      }
      return updatedChats
    })
  }

  const handleUpdateChatTitle = useCallback((id: string, title: string) => {
    setChats((prevChats) => prevChats.map((chat) => (chat.id === id ? { ...chat, title } : chat)))
  }, [])

  if (chats.length === 0 && currentChatId === "") {
    handleNewChat()
    return null
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

