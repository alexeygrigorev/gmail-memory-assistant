// Chat UI over the FastAPI SSE stream in server.py.
// Text deltas and tool events arrive as they happen; this file just
// turns each event into DOM at the bottom of the chat.

const chatEl = document.getElementById('chat')
const formEl = document.getElementById('form')
const inputEl = document.getElementById('input')
const sendEl = document.getElementById('send')
const sessionEl = document.getElementById('session')
const newChatEl = document.getElementById('new-chat')

const session = () => sessionEl.value.trim() || 'web'

function showEmpty() {
  const el = document.createElement('div')
  el.className = 'empty'
  el.textContent = '🧠'
  chatEl.appendChild(el)
}

function scrollIfNearBottom(force = false) {
  const nearBottom =
    chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 120
  if (nearBottom || force) chatEl.scrollTop = chatEl.scrollHeight
}

// --- DOM builders -----------------------------------------------------------

function userMessage(text) {
  const el = document.createElement('div')
  el.className = 'msg user'
  el.textContent = text
  chatEl.appendChild(el)
  scrollIfNearBottom(true)
}

function agentBlock() {
  const root = document.createElement('div')
  root.className = 'msg agent'
  const status = document.createElement('div')
  status.className = 'thinking'
  for (let i = 0; i < 3; i++) status.appendChild(document.createElement('i'))
  root.appendChild(status)
  chatEl.appendChild(root)
  scrollIfNearBottom(true)
  return {
    root,
    status,
    textEl: null, // current bubble deltas append into; null = create new
  }
}

function textBubble(block) {
  block.status.remove()
  const el = document.createElement('div')
  el.className = 'bubble'
  block.root.appendChild(el)
  block.textEl = el
  return el
}

function toolCard(block, name, args) {
  block.status.remove()
  block.textEl = null // next text delta starts a new bubble below the card

  const card = document.createElement('div')
  card.className = `tool ${name}`

  const head = document.createElement('div')
  head.className = 'tool-head'
  const icon = document.createElement('span')
  icon.className = 'tool-icon'
  icon.textContent = name === 'save_memory' ? '💾' : name === 'search_memory' ? '🔎' : '🔧'
  const title = document.createElement('code')
  title.textContent = name
  head.append(icon, title)

  const argsEl = document.createElement('pre')
  argsEl.className = 'tool-args'
  argsEl.textContent = JSON.stringify(args)

  const resultEl = document.createElement('div')
  resultEl.className = 'tool-result'
  resultEl.textContent = '...'

  card.append(head, argsEl, resultEl)
  block.root.appendChild(card)
  scrollIfNearBottom()
  return {
    done(result) {
      resultEl.textContent = result
      card.classList.add('done')
      scrollIfNearBottom()
    },
  }
}

function errorNote(block, message) {
  block.status.remove()
  const el = document.createElement('div')
  el.className = 'error'
  el.textContent = `⚠ ${message}`
  block.root.appendChild(el)
}

// --- streaming --------------------------------------------------------------

async function send(text) {
  chatEl.querySelector('.empty')?.remove()
  userMessage(text)
  inputEl.disabled = true
  sendEl.disabled = true
  const block = agentBlock()

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session: session(), message: text }),
    })
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let frameEnd
      while ((frameEnd = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, frameEnd)
        buffer = buffer.slice(frameEnd + 2)
        const line = frame.split('\n').find((l) => l.startsWith('data: '))
        if (!line) continue
        handleEvent(block, JSON.parse(line.slice(6)))
      }
    }
  } catch (error) {
    errorNote(block, String(error))
  } finally {
    block.status.remove()
    inputEl.disabled = false
    sendEl.disabled = false
    inputEl.focus()
  }
}

function handleEvent(block, event) {
  switch (event.type) {
    case 'text': {
      const el = block.textEl ?? textBubble(block)
      el.textContent += event.delta
      scrollIfNearBottom()
      break
    }
    case 'tool_call':
      block.activeCard = toolCard(block, event.name, event.args)
      break
    case 'tool_result':
      block.activeCard?.done(event.result)
      break
    case 'error':
      errorNote(block, event.message)
      break
    case 'done':
      block.status.remove()
      break
    case 'start':
    default:
      break
  }
}

// --- wiring -----------------------------------------------------------------

formEl.addEventListener('submit', (e) => {
  e.preventDefault()
  const text = inputEl.value.trim()
  if (!text) return
  inputEl.value = ''
  send(text)
})

newChatEl.addEventListener('click', async () => {
  await fetch(`/api/session/${encodeURIComponent(session())}`, { method: 'DELETE' })
  chatEl.replaceChildren()
  showEmpty()
})
