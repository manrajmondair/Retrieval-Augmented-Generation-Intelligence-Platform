import MarkdownIt from 'markdown-it'
import { getHighlighter } from 'shiki'

let highlighter: any = null

// Initialize shiki highlighter
async function initHighlighter() {
  if (!highlighter) {
    highlighter = await getHighlighter({
      theme: 'github-dark',
      langs: ['javascript', 'typescript', 'python', 'json', 'bash', 'yaml', 'markdown'],
    })
  }
  return highlighter
}

// Create markdown-it instance with syntax highlighting
async function createMarkdownIt() {
  const hl = await initHighlighter()
  
  return new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    highlight: (str, lang) => {
      if (lang && hl.getLoadedLanguages().includes(lang)) {
        try {
          return hl.codeToHtml(str, { lang })
        } catch (__) {}
      }
      return '' // use external default escaping
    }
  })
}

export async function renderMarkdown(content: string): Promise<string> {
  const md = await createMarkdownIt()
  return md.render(content)
}

export function renderInlineMarkdown(content: string): string {
  // Simple inline markdown rendering for basic formatting
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

export function extractCodeBlocks(content: string): string[] {
  const codeBlockRegex = /```[\s\S]*?```/g
  const matches = content.match(codeBlockRegex) || []
  return matches.map(block => block.replace(/```[\w]*\n?/, '').replace(/```$/, ''))
}

export function extractLinks(content: string): string[] {
  const urlRegex = /https?:\/\/[^\s]+/g
  return content.match(urlRegex) || []
}

export function sanitizeHtml(html: string): string {
  // Basic HTML sanitization
  const allowedTags = ['p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'blockquote']
  const allowedAttributes = ['href', 'target', 'rel']
  
  const div = document.createElement('div')
  div.innerHTML = html
  
  function sanitizeNode(node: Node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return
    }
    
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element
      const tagName = element.tagName.toLowerCase()
      
      if (!allowedTags.includes(tagName)) {
        // Remove disallowed tags
        const parent = element.parentNode
        if (parent) {
          parent.removeChild(element)
        }
        return
      }
      
      // Remove disallowed attributes
      const attributes = Array.from(element.attributes)
      attributes.forEach(attr => {
        if (!allowedAttributes.includes(attr.name)) {
          element.removeAttribute(attr.name)
        }
      })
      
      // Sanitize href attributes
      if (element.hasAttribute('href')) {
        const href = element.getAttribute('href')
        if (href && !href.startsWith('http')) {
          element.removeAttribute('href')
        }
      }
    }
    
    // Recursively sanitize child nodes
    const children = Array.from(node.childNodes)
    children.forEach(sanitizeNode)
  }
  
  sanitizeNode(div)
  return div.innerHTML
} 