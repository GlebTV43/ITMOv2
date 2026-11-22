const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const test = require('node:test');

const workflow = JSON.parse(readFileSync(join(__dirname, 'review.workflow.json'), 'utf8'));
const nodes = new Map(workflow.nodes.map(node => [node.name, node]));

function run(name, input, previous = {}) {
  const $input = { first: () => ({ json: input[0] }), all: () => input.map(json => ({ json })) };
  const $ = node => ({
    first: () => ({ json: previous[node][0] }),
    all: () => previous[node].map(json => ({ json })),
  });
  return new Function('$input', '$', nodes.get(name).parameters.jsCode)($input, $);
}

const repository = { full_name: 'GlebTV43/ITMOv2' };
const open = {
  headers: { 'x-github-event': 'pull_request' },
  body: { action: 'opened', repository, number: 11, pull_request: { base: { ref: '7.1' } } },
};
function comment(body, association = 'OWNER') {
  return {
    headers: { 'x-github-event': 'issue_comment' },
    body: { action: 'created', repository, issue: { number: 11, pull_request: {} },
      comment: { body, author_association: association } },
  };
}

test('only opened PRs and exact commands trigger the intended model', () => {
  const select = event => run('Choose review model', [event]);
  assert.equal(select(open)[0].json.model, 'qwen3.5:4b');
  assert.deepEqual(select({ ...open, body: { ...open.body, action: 'synchronize' } }), []);
  assert.equal(select(comment('/make_ai_review'))[0].json.mode, 'main');
  assert.equal(select(comment('/make_other_ai_review'))[0].json.model, 'gemma4:12b');
  assert.deepEqual(select(comment('/make_other_ai_review please')), []);
  assert.deepEqual(select(comment('/make_ai_review', 'NONE')), []);
});

test('a recorded PR skips the main model while allowing the second model', () => {
  const evaluate = (mode, stored) => run('Skip repeat main review', [stored], {
    'Check review scope': [{ mode, pr_id: '121' }],
  });
  assert.deepEqual(evaluate('main', { pr_id: '121' }), []);
  assert.equal(evaluate('main', {})[0].json.mode, 'main');
  assert.equal(evaluate('other', { pr_id: '121' })[0].json.mode, 'other');
});

const completePatch = {
  filename: 'books/exchanges.py', additions: 1, deletions: 2,
  patch: '@@ -6,2 +6,2 @@\n-old\n+new\n same\n@@ -21 +20,0 @@\n-removed',
};
const scope = { 'Check review scope': [{ changed_files: 1, model: 'main', head: 'a'.repeat(40) }] };

test('each textual hunk gets an anchor on the correct side', () => {
  const anchors = run('Split diff into hunks', [{ body: [completePatch] }], scope).map(v => v.json);
  assert.deepEqual(anchors.map(({ line, side }) => [line, side]), [[6, 'RIGHT'], [21, 'LEFT']]);
  assert.throws(() => run('Split diff into hunks', [{ body: [{ ...completePatch, deletions: 3 }] }], scope),
    /omitted textual changes/);
  const review = run('Build inline GitHub review', [
    { message: { content: 'Проверено @team' } }, { message: { content: 'Удаление проверено' } },
  ], { ...scope, 'Split diff into hunks': anchors })[0].json.review;
  assert.equal(review.event, 'COMMENT');
  assert.equal(review.comments.length, 2);
  assert.equal(review.comments[0].body, 'Проверено ＠team');
  assert.equal(review.comments[1].side, 'LEFT');
});

test('a changed head prevents posting comments on stale coordinates', () => {
  assert.throws(() => run('Reject stale diff', [
    { state: 'open', head: { sha: 'new' }, base: { ref: '7.1' } },
  ], { 'Build inline GitHub review': [{ head: 'old' }] }), /PR changed/);
});
test('local polling processes actual PR creation and command records only once', () => {
  const local = JSON.parse(readFileSync(join(__dirname, 'review.local.workflow.json'), 'utf8'));
  const script = local.nodes.find(node => node.name === 'Select one unseen GitHub event').parameters.jsCode;
  const poll = new Function('$input', '$', '$getWorkflowStaticData', script);
  const pr = { id: 121, number: 11, base: { ref: '7.1' },
    created_at: new Date(Date.now() - 3000).toISOString() };
  const message = {
    id: 130, author_association: 'OWNER', body: '/make_other_ai_review',
    issue_url: 'https://api.github.com/repos/GlebTV43/ITMOv2/issues/11',
    created_at: new Date(Date.now() - 1000).toISOString(),
  };
  const state = {};
  const input = { first: () => ({ json: { body: [message] } }) };
  const previous = () => ({ first: () => ({ json: { body: [pr] } }) });
  const tick = () => poll(input, previous, () => state);
  assert.equal(tick()[0].json.event_key, 'pr:121');
  assert.equal(tick()[0].json.event_key, 'comment:130');
  assert.deepEqual(tick(), []);
});
