const { createHash } = require('node:crypto');

const REPO = 'GlebTV43/ITMOv2';
const API = 'https://api.github.com/repos/' + REPO;
const MODEL = 'openai/gpt-4.1-mini';
const MODEL_ENDPOINT = 'https://litellm.data-light.ru/v1';
const GitHub = { authentication: 'predefinedCredentialType', nodeCredentialType: 'githubApi' };
const VseLLM = { authentication: 'genericCredentialType', genericAuthType: 'httpHeaderAuth' };
const githubHeaders = {
  sendHeaders: true,
  headerParameters: { parameters: [
    { name: 'Accept', value: 'application/vnd.github+json' },
    { name: 'X-GitHub-Api-Version', value: '2022-11-28' },
  ] },
};

function id(name) {
  const hex = createHash('sha256').update(name).digest('hex').slice(0, 32);
  return hex.replace(/^(........)(....)(....)(....)(............)$/, '$1-$2-$3-$4-$5');
}

function workflow(workflowId, name, settings = {}) {
  const result = { id: workflowId, name, nodes: [], connections: {}, active: false,
    settings: { executionOrder: 'v1', saveDataSuccessExecution: 'all', ...settings }, pinData: {}, tags: [] };
  return {
    result,
    add(name, type, typeVersion, parameters, x, y = 0, extra = {}) {
      const kind = type.includes('.') ? type : 'n8n-nodes-base.' + type;
      result.nodes.push({ id: id(workflowId + ':' + name), name, type: kind, typeVersion,
        position: [x, y], parameters, ...extra });
      return name;
    },
    code(name, jsCode, x, y = 0) {
      return this.add(name, 'code', 2, { jsCode }, x, y);
    },
    http(name, params, x, y = 0, extra = {}) {
      return this.add(name, 'httpRequest', 4.2, { options: { timeout: 20000 }, ...params }, x, y, extra);
    },
    edge(from, to, slot = 0, type = 'main', input = 0) {
      const routes = result.connections[from] ??= {};
      const lanes = routes[type] ??= [];
      while (lanes.length <= slot) lanes.push([]);
      lanes[slot].push({ node: to, type, index: input });
    },
    chain(...nodes) {
      for (let index = 1; index < nodes.length; index++) this.edge(nodes[index - 1], nodes[index]);
    },
  };
}

function condition(leftValue, rightValue, key = 'text') {
  return { options: { caseSensitive: true, typeValidation: 'strict', version: 2 }, combinator: 'and',
    conditions: [{ id: id(JSON.stringify([leftValue, rightValue, key])), leftValue, rightValue,
      operator: { type: key === 'flag' ? 'boolean' : 'string', operation: 'equals' } }] };
}

function table(w, name, tableName, columns, x, y) {
  return w.add(name, 'dataTable', 1.1, { resource: 'table', operation: 'create', tableName,
    columns: { column: Object.entries(columns).map(([name, type]) => ({ name, type })) },
    options: { createIfNotExists: true },
  }, x, y);
}

function tableId(name) {
  return { __rl: true, mode: 'id', value: `={{ $('${name}').first().json.id }}` };
}

function getRow(w, name, creation, keyName, expression, x, y) {
  return w.add(name, 'dataTable', 1.1, { resource: 'row', operation: 'get',
    dataTableId: tableId(creation), limit: 1,
    filters: { conditions: [{ keyName, condition: 'eq', keyValue: expression }] },
  }, x, y, { alwaysOutputData: true });
}

function saveRow(w, name, creation, keyName, columns, x, y) {
  return w.add(name, 'dataTable', 1.1, { resource: 'row', operation: 'upsert',
    dataTableId: tableId(creation),
    filters: { conditions: [{ keyName, condition: 'eq', keyValue: `={{ $json.${keyName} }}` }] },
    columns: { mappingMode: 'defineBelow', matchingColumns: [],
      value: Object.fromEntries(Object.keys(columns).map(key => [key, `={{ $json.${key} }}`])),
      schema: Object.entries(columns).map(([id, type]) => ({ id, displayName: id,
        required: false, defaultMatch: false, display: true, type, canBeUsedToMatch: true })),
      attemptToConvertTypes: false, convertFieldsToString: false }, options: {},
  }, x, y);
}

function chainModel(w, label, prompt, x, y, schema) {
  const chain = w.add(label, '@n8n/n8n-nodes-langchain.chainLlm', 1.9,
    { promptType: 'define', text: prompt, hasOutputParser: Boolean(schema), batching: {} }, x, y);
  const ai = w.add(label + ' · VseLLM', '@n8n/n8n-nodes-langchain.lmChatOpenAi', 1.2, {
    model: { __rl: true, mode: 'id', value: MODEL },
    options: { baseURL: MODEL_ENDPOINT, temperature: 0.1, maxTokens: 500, timeout: 60000, maxRetries: 1 },
  }, x, y + 220);
  w.edge(ai, chain, 0, 'ai_languageModel');
  if (schema) {
    const parser = w.add('Проверить JSON по схеме', '@n8n/n8n-nodes-langchain.outputParserStructured', 1.3, {
      schemaType: 'manual', inputSchema: JSON.stringify(schema),
    }, x + 240, y + 220);
    w.edge(parser, chain, 0, 'ai_outputParser');
  }
  return chain;
}

const item = (node, key) => `={{ $('${node}').first().json.${key} }}`;
const body = (value) => `={{ JSON.stringify(${value}) }}`;
module.exports = { REPO, API, MODEL, MODEL_ENDPOINT, GitHub, VseLLM, githubHeaders, id, workflow,
  item, body, condition, table, getRow, saveRow, chainModel };
