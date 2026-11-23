const { expect, test } = require('@playwright/test');

const password = 'demo-books-only-8';
const proposal = 'Привет! Предлагаю обмен на «Марсианина».';

async function login(page, user = 'reader') {
  await page.goto('/login/');
  await page.getByLabel('Электронная почта').fill(user + '@example.invalid');
  await page.getByLabel('Пароль').fill(password);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Дай почитать другим/ })).toBeVisible();
}

async function openOffer(page) {
  await login(page);
  await page.getByLabel('Что ищешь').fill('Дюна');
  await page.getByRole('button', { name: 'Найти книги' }).click();
  await page.getByRole('link', { name: /Дюна Фрэнк Герберт/ }).click();
  await page.getByRole('link', { name: 'Предложить обмен' }).click();
  await expect(page.getByRole('heading', { name: 'Предложить обмен', exact: true })).toBeVisible();
}

async function fillOffer(page) {
  await page.getByLabel('Какую книгу предлагаете').selectOption({ label: 'Марсианин' });
  await page.getByLabel('Сообщение владельцу').fill(proposal);
}

async function capture(page, testInfo, filename) {
  await page.screenshot({ path: testInfo.outputPath(filename + '.jpg'), type: 'jpeg', quality: 88, fullPage: true });
}

test('shows real catalogue cards, combines search filters and recovers from empty results', async ({ page }, info) => {
  await page.goto('/');
  const catalog = page.getByRole('region', { name: 'Книги к обмену' });
  await expect(catalog.getByRole('article')).toHaveCount(4);
  await expect(catalog.getByRole('link', { name: /Дюна Фрэнк Герберт/ })).toBeVisible();
  await expect.poll(() => catalog.locator('img').evaluateAll(photos =>
    photos.filter(photo => photo.complete && photo.naturalWidth > 0).length,
  )).toBe(4);
  await capture(page, info, 'catalog');
  await page.getByLabel('Что ищешь').fill('герберт');
  await page.getByLabel('Что готов отдать').fill('марсианин');
  await page.getByRole('button', { name: 'Найти книги' }).click();
  await expect(page.getByRole('region', { name: 'Результаты поиска' }).getByRole('article')).toHaveCount(1);
  await page.getByLabel('Что ищешь').fill('Несуществующая книга');
  await page.getByRole('button', { name: 'Найти книги' }).click();
  await expect(page.getByRole('heading', { name: 'Книг по этому запросу пока нет.' })).toBeVisible();
  await capture(page, info, 'empty');
  await page.getByRole('link', { name: 'Сбросить фильтры' }).click();
  await expect(page.getByRole('region', { name: 'Книги к обмену' }).getByRole('article')).toHaveCount(4);
});

test('renders an empty catalogue response with a way to clear filters', async ({ page }) => {
  const fixture = await page.request.get('/?q=__empty_response_fixture__');
  expect(fixture.ok()).toBe(true);
  await page.route(url => url.pathname === '/' && url.searchParams.get('q') === 'пустая выдача',
    route => route.fulfill({ response: fixture }));
  await page.goto('/');
  await page.getByLabel('Что ищешь').fill('пустая выдача');
  await page.getByRole('button', { name: 'Найти книги' }).click();
  await expect(page.getByRole('heading', { name: 'Книг по этому запросу пока нет.' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Сбросить фильтры' })).toBeVisible();
});

test('shows required-field and invalid-input errors while keeping the form editable', async ({ page }, info) => {
  await openOffer(page);
  await capture(page, info, 'offer');
  const button = page.getByRole('button', { name: 'Отправить предложение' });
  await button.click();
  await expect(page.getByText('Обязательное поле.', { exact: true })).toHaveCount(2);
  await expect(page.getByLabel('Какую книгу предлагаете')).toBeFocused();
  await expect(button).toBeEnabled();
  await fillOffer(page);
  const message = page.getByLabel('Сообщение владельцу');
  await message.evaluate(input => { input.removeAttribute('maxlength'); input.value = 'Ж'.repeat(2001); });
  await button.click();
  await expect(page.getByText(/2000 символов/)).toBeVisible();
  await expect(message).toHaveValue('Ж'.repeat(2001));
  await message.fill('Тестовое сообщение после исправления.');
  await capture(page, info, 'validation');
});

test('locks a delayed submission, ignores double activation, and shows a successful response', async ({ page }, info) => {
  await openOffer(page);
  await fillOffer(page);
  let requests = 0;
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  await page.route('**/books/*/offer/', async route => {
    requests++;
    await pending;
    await route.fulfill({ json: { redirect: '/exchanges/9999/' } });
  });
  await page.route('**/exchanges/9999/', route => route.fulfill({
    contentType: 'text/html; charset=utf-8',
    body: '<!doctype html><p role="status">Предложение отправлено.</p><h1>Марсианин ↔ Дюна</h1>',
  }));
  const submit = page.getByRole('button', { name: 'Отправить предложение' });
  const bounds = await submit.boundingBox();
  await page.mouse.dblclick(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  await expect(page.getByRole('button', { name: 'Отправляем…' })).toBeDisabled();
  await expect(page.getByRole('status')).toHaveText('Отправляем предложение. Подождите.');
  await page.locator('[data-offer-form]').evaluate(form => form.requestSubmit());
  await expect.poll(() => requests).toBe(1);
  await capture(page, info, 'loading');
  release();
  await expect(page.getByRole('heading', { name: 'Марсианин ↔ Дюна' })).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Предложение отправлено.');
  expect(requests).toBe(1);
});

test('keeps filled values after a failed request and lets the reader retry', async ({ page }, info) => {
  await openOffer(page);
  await fillOffer(page);
  let requests = 0;
  await page.route('**/books/*/offer/', async route => {
    requests++;
    if (requests === 1) {
      await route.fulfill({ status: 503, body: 'Unavailable' });
    } else {
      await route.fulfill({ json: { redirect: '/exchanges/9998/' } });
    }
  });
  await page.route('**/exchanges/9998/', route => route.fulfill({
    contentType: 'text/html; charset=utf-8', body: '<h1>Предложение принято</h1>',
  }));
  const submit = page.getByRole('button', { name: 'Отправить предложение' });
  await submit.click();
  const error = page.getByRole('alert');
  await expect(error).toContainText('Не удалось отправить предложение');
  await expect(error).toBeFocused();
  await expect(page.getByLabel('Сообщение владельцу')).toHaveValue(proposal);
  await expect(submit).toBeEnabled();
  await capture(page, info, 'network-error');
  await submit.click();
  await expect(page.getByRole('heading', { name: 'Предложение принято' })).toBeVisible();
  expect(requests).toBe(2);
});

test('runs the complete flow against Django on a narrow screen and shows the offer to the owner', async ({ page, browser }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'К содержимому' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  const search = page.getByLabel('Что ищешь');
  await search.fill('Дюна');
  await search.press('Enter');
  await page.getByRole('link', { name: /Дюна Фрэнк Герберт/ }).press('Enter');
  await expect(page.getByRole('heading', { name: 'Дюна', exact: true })).toBeVisible();
  await capture(page, info, 'book-mobile');
  await page.getByRole('link', { name: 'Предложить обмен' }).press('Enter');
  await fillOffer(page);
  const message = page.getByLabel('Сообщение владельцу');
  await message.focus();
  await page.keyboard.press('Tab');
  const submit = page.getByRole('button', { name: 'Отправить предложение' });
  await expect(submit).toBeFocused();
  expect(await submit.evaluate(button => getComputedStyle(button).outlineStyle)).toBe('solid');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Марсианин ↔ Дюна' })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Предложение отправлено');
  await expect(page.getByText(proposal, { exact: true })).toBeVisible();
  const exchangeURL = page.url();
  await capture(page, info, 'success-mobile');

  const context = await browser.newContext();
  try {
    const owner = await context.newPage();
    await login(owner, 'owner');
    await owner.getByRole('link', { name: 'Обмены', exact: true }).click();
    await owner.getByRole('link', { name: 'Марсианин ↔ Дюна' }).click();
    await expect(owner).toHaveURL(exchangeURL);
    await expect(owner.getByText(proposal, { exact: true })).toBeVisible();
    await expect(owner.getByRole('button', { name: 'Принять предложение' })).toBeVisible();
  } finally {
    await context.close();
  }
});
