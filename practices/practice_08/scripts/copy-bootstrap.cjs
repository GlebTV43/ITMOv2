const { copyFileSync, mkdirSync } = require('node:fs');
const { resolve } = require('node:path');

const target = resolve(__dirname, '../books/static/books/vendor');
mkdirSync(target, { recursive: true });
copyFileSync(require.resolve('bootstrap/dist/css/bootstrap.min.css'), resolve(target, 'bootstrap.min.css'));
