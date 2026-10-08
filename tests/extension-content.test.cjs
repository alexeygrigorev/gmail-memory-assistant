const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { parseHTML } = require('linkedom');

const source = fs.readFileSync(path.join(__dirname, '../extension/content.js'), 'utf8');
const editor = '<div class="Am Al editable" contenteditable="true" role="textbox" aria-multiline="true"></div>';

function fixture(html) {
  const { window, document } = parseHTML(`<html><body>${html}</body></html>`);
  const callbacks = new Map();
  let nextTimer = 0;
  vm.runInNewContext(source, {
    document, window, MutationObserver: window.MutationObserver,
    setTimeout: fn => { callbacks.set(++nextTimer, fn); return nextTimer; },
    chrome: {}, location: { hash: '' }, crypto: {},
  });
  return {
    document, callbacks,
    async flush() {
      await new Promise(setImmediate);
      const pending = [...callbacks.values()];
      callbacks.clear();
      pending.forEach(fn => fn());
      await new Promise(setImmediate);
    },
  };
}

test('attaches to an inline editor without depending on Gmail container classes', () => {
  const { document } = fixture(`<section>${editor}</section>`);
  assert.equal(document.querySelectorAll('.memhub-panel').length, 1);
  assert.equal(document.querySelector('[contenteditable]').previousElementSibling.className, 'memhub-panel');
});

test('replacing an editor inside a reused marked container attaches fresh controls', async () => {
  const f = fixture(`<div class="ip" data-mem-hub-panel="1">${editor}</div>`);
  const container = f.document.querySelector('.ip');
  container.innerHTML = editor;
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 1);
  assert.equal(container.querySelector('[contenteditable]').previousElementSibling.className, 'memhub-panel');
});

test('restores controls removed by Gmail and never duplicates them', async () => {
  const f = fixture(editor);
  f.document.querySelector('.memhub-panel').remove();
  await f.flush();
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 1);
});

test('editor replacement removes orphaned controls', async () => {
  const f = fixture(`<section>${editor}</section>`);
  f.document.querySelector('[contenteditable]').remove();
  f.document.querySelector('section').insertAdjacentHTML('afterbegin', editor);
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 1);
});

test('recognizes localized editors initialized by attribute changes', async () => {
  const f = fixture('<div role="textbox" aria-multiline="true" aria-label="Nachrichtentext"></div>');
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 0);
  f.document.querySelector('div').setAttribute('contenteditable', 'true');
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 1);
});

test('continuous mutations do not restart the pending attachment timer', async () => {
  const f = fixture('<section></section>');
  f.document.querySelector('section').innerHTML = editor;
  await new Promise(setImmediate);
  const timer = [...f.callbacks.keys()][0];
  assert.ok(timer);
  for (let i = 0; i < 5; i++) {
    f.document.body.appendChild(f.document.createElement('span'));
    await new Promise(setImmediate);
    assert.deepEqual([...f.callbacks.keys()], [timer]);
  }
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 1);
});

test('multiple open editors each get exactly one panel', async () => {
  const f = fixture(`<section>${editor}${editor}</section>`);
  await f.flush();
  assert.equal(f.document.querySelectorAll('.memhub-panel').length, 2);
});
