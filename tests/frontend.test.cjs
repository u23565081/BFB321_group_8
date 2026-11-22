const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function element() {
  return {
    hidden: true, disabled: false, textContent: "", className: "", handlers: {},
    addEventListener(event, handler) { this.handlers[event] = handler; },
    querySelector() { return this.child ||= element(); },
  };
}

function setup(responses) {
  const elements = new Map();
  const get = (id) => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const planner = get("recommendation-form");
  const settings = get("shop-settings-form");
  planner.elements = { supplier_id: { value: "2" }, budget: { value: "2500" } };
  settings.elements = {
    cash_budget: { value: "123.45" }, review_period_days: { value: "4" },
    safety_stock_days: { value: "2" },
  };
  for (const form of [planner, settings]) {
    form.checkValidity = () => true;
    form.reportValidity = () => {};
  }
  const calls = [];
  const page = { dataset: { page: "replenishment", shopId: "3" } };
  class FormData {
    constructor(form) { this.form = form; }
    get(key) { return this.form.elements[key].value; }
    *[Symbol.iterator]() {
      for (const [key, input] of Object.entries(this.form.elements)) yield [key, input.value];
    }
  }
  const context = {
    document: {
      getElementById: get,
      querySelector: (selector) => selector === "[data-page]" ? page : get(selector),
    },
    FormData,
    fetch: async (url, options) => {
      calls.push({ url, options });
      const response = responses.shift();
      assert.ok(response, "Unexpected fetch");
      return { ok: response.ok, json: async () => response.body };
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/js/app.js"), "utf8"), context);
  return {
    get, calls, planner, settings,
    submit: () => settings.handlers.submit({ preventDefault() {} }),
  };
}

const saved = { cash_budget: 123.45, review_period_days: 4, safety_stock_days: 2 };
const basket = { items: [], totals: { product_cost: 0, delivery_fee: 0, total_cost: 0 }, message: "Recalculated" };

test("shop settings PATCH sends numeric values and recalculates using the saved budget", async () => {
  const ui = setup([{ ok: true, body: saved }, { ok: true, body: basket }]);
  await ui.submit();
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.calls[0].url, "/api/v1/shops/3");
  assert.equal(ui.calls[0].options.method, "PATCH");
  assert.deepEqual(JSON.parse(ui.calls[0].options.body), saved);
  assert.match(ui.calls[1].url, /shop_id=3&supplier_id=2&budget=123.45/);
  assert.equal(ui.planner.elements.budget.value, 123.45);
  assert.match(ui.get("shop-settings-message").textContent, /123.45/);
  assert.match(ui.get("shop-settings-message").className, /alert-success/);
  assert.equal(ui.get("shop-settings-message").hidden, false);
  assert.equal(ui.settings.querySelector().disabled, false);
});

test("failed settings PATCH shows the JSON error and does not recalculate", async () => {
  const ui = setup([{ ok: false, body: { message: "You cannot update another owner's shop." } }]);
  await ui.submit();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.get("shop-settings-message").textContent, "You cannot update another owner's shop.");
  assert.match(ui.get("shop-settings-message").className, /alert-danger/);
  assert.equal(ui.planner.elements.budget.value, "2500");
  assert.equal(ui.get("create-order").disabled, true);
  assert.equal(ui.settings.querySelector().disabled, false);
});

test("a failed basket refresh keeps the saved-settings success and shows the planner error", async () => {
  const ui = setup([{ ok: true, body: saved }, { ok: false, body: { message: "Calculation unavailable" } }]);
  await ui.submit();
  assert.match(ui.get("shop-settings-message").className, /alert-success/);
  assert.equal(ui.get("planner-error").hidden, false);
  assert.equal(ui.get("planner-error").querySelector().textContent, "Calculation unavailable");
  assert.equal(ui.get("create-order").disabled, true);
});
