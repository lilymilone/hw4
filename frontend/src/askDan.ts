// Opens the chat with a question already typed in (ChatWidget listens for this event).
// Pass '' to just open the chat.
export function askDan(question = '') {
  window.dispatchEvent(new CustomEvent('cc-ask-assistant', { detail: question }))
}
