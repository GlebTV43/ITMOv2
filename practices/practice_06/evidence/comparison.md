# Повтор одних и тех же HTTP-проверок

| ID | Проверка | Исходный ответ | После фикса |
|---|---|---:|---:|
| A01 | Unauthenticated profile access | 200 | 401 |
| A02 | Cross-customer profile IDOR | 200 | 403 |
| A03 | Numeric SQL injection | 200 | 400 |
| A04 | String SQL injection and unrestricted search | 200 | 200 |
| A05 | All-customer order disclosure | 200 | 200 |
| A06 | Client controls purchase price | 201 | 201 |
| A07 | Forged staff role without session | 200 | 401 |
| A08 | Forged staff role with customer session | 200 | 403 |
| A09 | Cross-customer receipt access | 200 | 403 |
| A10 | Traversal within physical sandbox | 200 | 403 |
| A11 | Stored HTML/script injection | 200 | 200 |
| A12 | Password and token exposure in debug logs | 200 | 403 |
| A13 | Cross-customer AI context | 200 | 403 |
| A14 | SQL injection in AI order lookup | 200 | 400 |
| A15 | AI executor reads another receipt | 200 | 403 |
| A16 | AI executor reads private note | 200 | 403 |
| A17 | AI executor exports profiles | 200 | 403 |
| A18 | Unauthenticated AI tool execution | 200 | 401 |
| A19 | Malformed JSON leaks exception details | 500 | 400 |
| A20 | Unexpected JSON type causes internal error | 500 | 400 |
| A21 | Unbounded review length | 201 | 400 |
| A22 | Anonymous review creation | 201 | 401 |
| A23 | AI deletion of fixture files | 200 | 403 |
| A24 | Receipt survives dangerous decision | 500 | 200 |

Статус 200 после фикса бывает правильным: например, search возвращает только разрешённые записи, а HTML экранирован. Проверяется не только код ответа, но и содержимое/состояние.
