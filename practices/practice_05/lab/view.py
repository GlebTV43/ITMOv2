"""Server-rendered registry page. All subscriber text is escaped here."""

from html import escape


def render_page(names, message="", error="", name=""):
    """Render a snapshot without changing it or imposing extra validation."""
    rows = "".join(
        f'''<li><span class="subscriber-name">{escape(item, quote=True)}</span>
        <form method="post" action="/unsubscribe" accept-charset="UTF-8">
          <input type="hidden" name="name" value="{escape(item, quote=True)}">
          <button class="remove" type="submit" aria-label="Отписать {escape(item, quote=True)}">Отписать</button>
        </form></li>'''
        for item in names
    )
    content = f'<ul class="subscribers">{rows}</ul>' if names else (
        '<div class="empty"><span aria-hidden="true">○</span>'
        '<p>Пока нет подписчиков</p><small>Добавьте первое имя с помощью формы.</small></div>'
    )
    notice = f'<p class="notice" role="status">{escape(message)}</p>' if message else ""
    problem = f'<p class="error" id="name-error" role="alert">{escape(error)}</p>' if error else ""
    invalid = ' aria-invalid="true" aria-describedby="name-help name-error"' if error else (
        ' aria-describedby="name-help"'
    )
    return f'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Реестр подписчиков</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: #202c38; background: #f3f5f7;
      font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }}
    main {{ max-width: 780px; padding: 52px 24px; margin: auto; }}
    .eyebrow {{ color: #526474; text-transform: uppercase; letter-spacing: .13em;
      font-size: 12px; font-weight: 700; }}
    h1 {{ font-size: clamp(27px, 5vw, 36px); line-height: 1.2; margin: 12px 0; }}
    .intro, footer {{ color: #637180; }}
    section {{ background: white; border: 1px solid #dce2e7;
      border-radius: 16px; padding: 26px; margin: 24px 0; }}
    h2 {{ font-size: 20px; margin: 0 0 18px; }}
    label {{ display: block; font-weight: 600; margin-bottom: 8px; }}
    .entry {{ display: flex; gap: 12px; }}
    input[type=text] {{ min-width: 0; width: 100%; border: 1px solid #9daab5;
      border-radius: 8px; padding: 11px 13px; font: inherit; }}
    button {{ cursor: pointer; border-radius: 8px; border: 1px solid #226b57;
      background: #226b57; color: white; padding: 11px 18px; font: inherit;
      font-weight: 600; white-space: nowrap; }}
    button:hover {{ background: #18513f; }}
    :focus-visible {{ outline: 3px solid #276faa; outline-offset: 3px; }}
    .remove {{ background: white; color: #526474; border-color: #dce2e7;
      padding: 6px 12px; font-size: 14px; }}
    .remove:hover {{ background: #f3f5f7; }}
    small, #name-help {{ color: #637180; font-size: 13px; }}
    #name-help {{ margin: 10px 0 0; }}
    .notice {{ background: #e7f3ec; color: #245740; padding: 12px 16px; border-radius: 8px; }}
    .error {{ color: #a12424; background: #fff0ed; padding: 12px; border-radius: 8px; }}
    .count {{ font-weight: 400; color: #637180; margin-left: 8px; }}
    ul {{ list-style: none; padding: 0; margin: 0; }}
    li {{ display: flex; gap: 16px; align-items: center; justify-content: space-between;
      padding: 14px 0; border-top: 1px solid #e8ecef; }}
    .subscriber-name {{ overflow-wrap: anywhere; min-width: 0; }}
    .empty {{ text-align: center; padding: 22px 8px; color: #637180; }}
    .empty > span {{ font-size: 34px; color: #8faaa1; }}
    .empty p {{ font-weight: 600; margin: 8px 0 0; }}
    footer {{ font-size: 13px; text-align: center; }}
    @media(max-width: 520px) {{ main {{ padding: 28px 16px; }}
      section {{ padding: 20px; }} .entry {{ flex-direction: column; }} }}
  </style>
</head>
<body><main>
  <header><span class="eyebrow">Подписки</span><h1>Реестр подписчиков</h1>
    <p class="intro">Добавляйте имена и управляйте списком в одном месте.</p></header>
  {notice}
  <section aria-labelledby="add-title"><h2 id="add-title">Новый подписчик</h2>
    <form method="post" action="/subscribe" accept-charset="UTF-8">
      <label for="name">Имя подписчика</label>
      <div class="entry"><input type="text" id="name" name="name"
        value="{escape(name, quote=True)}" placeholder="Например, Анна"{invalid}>
        <button type="submit">Подписать</button></div>
      <p id="name-help">От 1 до 80 символов. Пробелы по краям убираются.</p>
      {problem}
    </form>
  </section>
  <section aria-labelledby="list-title"><h2 id="list-title">Подписчики
    <span class="count">{len(names)}</span></h2>{content}</section>
  <footer>Список хранится до перезапуска приложения.</footer>
</main></body></html>'''
