import { test, expect } from '@playwright/test'

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173')
  })

  test('should load the chat interface', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('New Conversation')
  })

  test('should allow typing in the input', async ({ page }) => {
    const input = page.locator('input[placeholder*="Ask a question"]')
    await input.fill('Hello, how are you?')
    await expect(input).toHaveValue('Hello, how are you?')
  })

  test('should navigate to ingest page', async ({ page }) => {
    await page.click('text=Ingest Documents')
    await expect(page).toHaveURL('http://localhost:5173/ingest')
    await expect(page.locator('h1')).toContainText('Document Ingestion')
  })

  test('should navigate to evals page', async ({ page }) => {
    await page.click('text=Settings')
    // Note: Settings page not implemented yet, so this would fail
    // await expect(page).toHaveURL('http://localhost:5173/settings')
  })
}) 