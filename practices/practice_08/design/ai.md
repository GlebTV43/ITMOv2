# Как использовали AI

## Макет

Codex подготовил [интерактивный HTML-макет](prototype.html) по запросу «Спроектируй книжный обмен от поиска по названию или автору до сообщения в созданном обмене. Покажи пустую выдачу, ожидание ответа, ошибки и успех. Используй простую структуру, пригодную для мобильного экрана».

В первом варианте поиск выглядел как обычная форма под заголовком. После проверки добавили отдельную панель с двумя независимыми фильтрами, счётчик результатов и сброс при пустой выдаче. На странице предложения сохранили рядом карточку книги владельца. На узком экране она располагается под формой.

## Интерфейс

Запрос для реализации «Оставь Django-шаблоны, реальные маршруты обмена и CSRF. Переиспользуй карточки, кнопки, формы, уведомления и спиннер Bootstrap 5.3. Покажи успех после перехода к созданному обмену. Во время запроса блокируй повторную отправку».

Первоначальный вариант рассчитывал автоматически переходить по HTTP-редиректу внутри fetch. При проверке потока заметили, что такой промежуточный GET забирает сообщение Django об успехе. Для AJAX сервер теперь возвращает адрес перехода в JSON, а браузер открывает страницу обмена сам. Ошибки валидации возвращаются как HTML со статусом 422. Сетевой сбой оставляет заполненные данные и возвращает фокус к сообщению об ошибке.

## Фотографии

Встроенный ImageGen создал [фотографию для каталога](../books/static/books/reading-room.webp) и [четыре фото демонстрационных экземпляров](../books/static/books/demo). После генерации файлы уменьшили и сохранили в WebP и JPEG для загрузки в браузере. Фото в обычных объявлениях по-прежнему загружают пользователи.

Запрос для фотографии каталога

> Photorealistic natural editorial hero photograph for a Russian community used-book exchange website. Wide 3:2 composition. A short irregular stack of three old clothbound hardcover books in olive, faded rust and tan, with one book open and resting diagonally across the top, gently curved pages. The objects sit on an olive-green linen cloth on the right half. Leaf shadows and warm afternoon sunshine from the upper right. Dominant deep olive, khaki, honey and muted forest green. Tight atmospheric crop, rich visible grain in paper and cloth, professionally styled but secondhand and tangible. No people, no devices, no legible lettering, no graphic overlays, no logos. Left third darker woodland green with quiet soft shadows; text gets added separately.

Запрос для отдельных экземпляров

> Photorealistic single second-hand book listing photo, bookstore product editorial. Portrait composition. A single vintage hardcover book with a [cover motif], set at a slight angle on a warm neutral soft paper backdrop. Whole cover fully within image, visible used spine and a little corner rub, diffuse natural sunlight and soft shadow. No words, no logos, no additional objects. The book fills 78 percent of the height.

Варианты обложек — терракотовые дюны с тёмным солнцем, медная планета на сине-зелёной обложке, чёрный отпечаток ладони на светлом переплёте и старинный золотой орнамент на зелёном.

## Тесты

Запрос для Playwright «Проверь видимые элементы и поведение. Подмени пустой ответ, задержку, успех и ошибку сети. Отдельно проверь количество POST при двойном клике и повторном submit. Один сценарий пройди через настоящий Django и проверь предложение в аккаунте владельца».

Сопоставили тестовые ответы с Django. Успех возвращает JSON с адресом страницы обмена, `422` содержит размеченную форму с ошибками, а пустой ответ берётся из реально отрисованного шаблона каталога. В сквозном тесте добавили проход клавиатурой на ширине 390 px и проверили результат во второй браузерной сессии.
