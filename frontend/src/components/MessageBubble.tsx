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
    .replace(/(<li>[\s\S]*?<\/li>(\s*<li>[\s\S]*?<\/li>)*)/g, '<ul>$1</ul>')
    .replace(/---/g, '<hr>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hul]|<p|<hr)(.+)/gm, '<p>$1</p>')
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const isPatient = message.role === 'patient'

  return (
    <div className={`flex items-end gap-2 mb-3 ${isPatient ? 'justify-end' : 'justify-start'}`}>

      {/* Assistant avatar */}
      {!isPatient && (
        <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 mb-0.5 shadow-sm">
          <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
      )}

      {/* Bubble */}
      <div className={`max-w-[78%] text-[13px] leading-relaxed ${
        isPatient
          ? 'bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 shadow-sm'
          : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm'
      }`}>
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

      {/* Patient avatar */}
      {isPatient && (
        <div className="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 mb-0.5">
          <svg className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      )}
    </div>
  )
}
