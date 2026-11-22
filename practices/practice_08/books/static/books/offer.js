function setPending(form, pending) {
  const submit = form.querySelector('button[type="submit"]');
  form.setAttribute('aria-busy', String(pending));
  submit.disabled = pending;
  submit.querySelector('[data-offer-spinner]').hidden = !pending;
  submit.querySelector('[data-offer-label]').textContent = pending
    ? 'Отправляем…'
    : 'Отправить предложение';
  form.closest('[data-offer-panel]').querySelector('[data-offer-status]').textContent = pending
    ? 'Отправляем предложение. Подождите.'
    : '';
}

document.addEventListener('submit', async event => {
  const form = event.target;
  if (!form.matches('[data-offer-form]')) return;
  event.preventDefault();
  if (form.getAttribute('aria-busy') === 'true') return;

  const error = form.querySelector('[data-network-error]');
  error.hidden = true;
  const data = new FormData(form);
  setPending(form, true);

  let leaving = false;
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      body: data,
      headers: { 'X-Bookshare-Form': 'offer' },
      signal: AbortSignal.timeout(15000),
    });
    if (response.redirected && response.ok) {
      window.location.assign(response.url);
      leaving = true;
      return;
    }
    if (response.ok && response.headers.get('content-type')?.includes('application/json')) {
      const { redirect } = await response.json();
      const destination = new URL(redirect, window.location.href);
      if (typeof redirect !== 'string' || destination.origin !== window.location.origin) {
        throw new Error('Invalid redirect');
      }
      window.location.assign(destination);
      leaving = true;
      return;
    }
    if (response.status !== 422) throw new Error('Offer submission failed');

    const page = new DOMParser().parseFromString(await response.text(), 'text/html');
    const replacement = page.querySelector('[data-offer-panel]');
    if (!replacement) throw new Error('Validation response did not contain the offer form');
    form.closest('[data-offer-panel]').replaceWith(replacement);
    const focus = replacement.querySelector('[aria-invalid="true"], [role="alert"]:not([hidden]), a.btn');
    focus?.focus();
  } catch {
    error.hidden = false;
    error.focus();
  } finally {
    if (form.isConnected && !leaving) setPending(form, false);
  }
});

window.addEventListener('pageshow', event => {
  if (!event.persisted) return;
  const form = document.querySelector('[data-offer-form][aria-busy="true"]');
  if (form) setPending(form, false);
});
