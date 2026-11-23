const { copyFileSync, cpSync, mkdirSync } = require('node:fs');
const { dirname, join, resolve } = require('node:path');

const target = resolve(__dirname, '../books/static/books/vendor');
mkdirSync(target, { recursive: true });
copyFileSync(require.resolve('bootstrap/dist/css/bootstrap.min.css'), resolve(target, 'bootstrap.min.css'));

for (const family of ['lora', 'manrope']) {
  const source = dirname(require.resolve('@fontsource-variable/' + family));
  const destination = join(target, family);
  mkdirSync(destination, { recursive: true });
  copyFileSync(join(source, 'index.css'), join(destination, 'index.css'));
  copyFileSync(join(source, 'LICENSE'), join(destination, 'LICENSE'));
  cpSync(join(source, 'files'), join(destination, 'files'), { recursive: true });
}
