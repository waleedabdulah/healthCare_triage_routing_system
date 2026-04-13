import React from 'react'
import { Message } from '../store/sessionStore'

interface Props {
  message: Message
  isStreaming?: boolean
}

function renderMarkdown(text: string): string {
  return text
    .replace(/### (.+)/g, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/---/g, '<hr>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul]|<p|<hr)(.+)/gm, '<p>$1</p>')
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const isPatient = message.role === 'patient'

  return (
    <div className={`flex ${isPatient ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isPatient && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold mr-2 mt-1 flex-shrink-0">
          🏥
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isPatient
            ? 'bg-blue-600 text-white rounded-tr-none'
            : 'bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm'
        }`}
      >
        {isPatient ? (
          <p>{message.content}</p>
        ) : (
          <div
            className="prose-chat"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
          />
        )}
        {isStreaming && <span className="cursor-blink" />}
      </div>
      {isPatient && (
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 text-sm ml-2 mt-1 flex-shrink-0">
          👤
        </div>
      )}
    </div>
  )
}
