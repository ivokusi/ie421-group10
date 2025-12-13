import type React from "react"
import type { JSX } from "react"

interface MarkdownContentProps {
  content: string
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  const renderContent = (text: string) => {
    const processedLines: React.ReactNode[] = []
    const lines = text.split("\n")
    let i = 0

    while (i < lines.length) {
      const line = lines[i]

      // Handle code blocks with \`\`\`language
      if (line.trim().startsWith("```")) {
        const language = line.trim().slice(3).trim() || "code"
        const codeLines: string[] = []
        i++

        // Collect all lines until closing \`\`\`
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          codeLines.push(lines[i])
          i++
        }

        processedLines.push(
          <div key={i} className="my-4 rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
            {language && (
              <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 text-xs font-mono text-gray-300">
                {language}
              </div>
            )}
            <pre className="p-4 overflow-x-auto">
              <code className="font-mono text-sm text-green-400">{codeLines.join("\n")}</code>
            </pre>
          </div>,
        )
        i++ // Skip closing \`\`\`
        continue
      }

      const isCodeLine =
        line.startsWith("    ") || // 4 spaces indentation
        line.startsWith("\t") || // Tab indentation
        /^(def|function|const|let|var|class|import|from|export|public|private|if|for|while|return)\s/.test(
          line.trim(),
        ) || // Common keywords
        /^[a-zA-Z_$][a-zA-Z0-9_$]*\s*[=:]\s*/.test(line.trim()) || // Variable assignment
        /^[{}[\]();]/.test(line.trim()) // Code symbols

      if (isCodeLine) {
        // Collect consecutive code lines
        const codeLines: string[] = [line]
        i++

        while (
          i < lines.length &&
          (lines[i].startsWith("    ") ||
            lines[i].startsWith("\t") ||
            lines[i].trim() === "" ||
            /^[a-zA-Z_${}[\]();=:]/.test(lines[i].trim()))
        ) {
          codeLines.push(lines[i])
          i++
        }

        processedLines.push(
          <div key={i} className="my-4 rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
            <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 text-xs font-mono text-gray-300">code</div>
            <pre className="p-4 overflow-x-auto">
              <code className="font-mono text-sm text-green-400">{codeLines.join("\n")}</code>
            </pre>
          </div>,
        )
        continue
      }

      // Handle numbered lists
      const numberedListMatch = line.match(/^(\d+)\.\s+(.*)$/)
      if (numberedListMatch) {
        const number = numberedListMatch[1]
        const content = numberedListMatch[2]
        processedLines.push(
          <div key={i} className="my-2 flex gap-2">
            <span className="font-semibold text-primary">{number}.</span>
            <span className="flex-1">{formatInlineText(content)}</span>
          </div>,
        )
        i++
        continue
      }

      // Handle bullet lists
      const bulletListMatch = line.match(/^[•\-*]\s+(.*)$/)
      if (bulletListMatch) {
        const content = bulletListMatch[1]
        processedLines.push(
          <div key={i} className="my-2 flex gap-2">
            <span className="text-primary">•</span>
            <span className="flex-1">{formatInlineText(content)}</span>
          </div>,
        )
        i++
        continue
      }

      // Handle headings
      const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
      if (headingMatch) {
        const level = headingMatch[1].length
        const content = headingMatch[2]
        const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements
        processedLines.push(
          <HeadingTag key={i} className="mt-4 mb-2 font-bold">
            {formatInlineText(content)}
          </HeadingTag>,
        )
        i++
        continue
      }

      // Handle empty lines
      if (line.trim() === "") {
        processedLines.push(<br key={i} />)
        i++
        continue
      }

      // Regular paragraph
      processedLines.push(
        <p key={i} className="my-2">
          {formatInlineText(line)}
        </p>,
      )
      i++
    }

    return processedLines
  }

  const formatInlineText = (text: string) => {
    const parts: React.ReactNode[] = []
    let remaining = text
    let key = 0

    while (remaining.length > 0) {
      // Bold text with **text**
      const boldMatch = remaining.match(/^\*\*(.+?)\*\*/)
      if (boldMatch) {
        parts.push(
          <strong key={key++} className="font-bold text-foreground">
            {boldMatch[1]}
          </strong>,
        )
        remaining = remaining.slice(boldMatch[0].length)
        continue
      }

      // Italic text with *text*
      const italicMatch = remaining.match(/^\*(.+?)\*/)
      if (italicMatch) {
        parts.push(<em key={key++}>{italicMatch[1]}</em>)
        remaining = remaining.slice(italicMatch[0].length)
        continue
      }

      // Inline code with `code`
      const codeMatch = remaining.match(/^`(.+?)`/)
      if (codeMatch) {
        parts.push(
          <code key={key++} className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">
            {codeMatch[1]}
          </code>,
        )
        remaining = remaining.slice(codeMatch[0].length)
        continue
      }

      // Regular text until next special character
      const nextSpecial = remaining.search(/[*`]/)
      if (nextSpecial === -1) {
        parts.push(<span key={key++}>{remaining}</span>)
        break
      } else {
        parts.push(<span key={key++}>{remaining.slice(0, nextSpecial)}</span>)
        remaining = remaining.slice(nextSpecial)
      }
    }

    return parts
  }

  return <div className="space-y-1">{renderContent(content)}</div>
}
