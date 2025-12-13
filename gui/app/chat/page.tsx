import { redirect } from "next/navigation"
import { createClient } from "@/lib/supabase/server"
import ChatInterface from "@/components/chat-interface"
import LogoutButton from "@/components/logout-button"

export const runtime = 'edge';

export default async function Home() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect("/auth/login")
  }

  return (
    <main className="flex h-screen w-full flex-col">
      <header className="flex items-center justify-between border-b border-border bg-background px-6 py-3">
        <h1 className="font-semibold text-lg">AI Chat Assistant</h1>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground text-sm">{user.email}</span>
          <LogoutButton />
        </div>
      </header>
      <div className="flex-1 overflow-hidden">
        <ChatInterface userId={user.id} />
      </div>
    </main>
  )
}

