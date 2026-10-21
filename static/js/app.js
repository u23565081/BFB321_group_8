(() => {
  const menuButton = document.querySelector(".menu-button");
  const nav = document.querySelector(".main-nav");
  if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
    });
  }

  const page = document.querySelector("[data-page]");
  if (!page) return;
  const shopId = Number(page.dataset.shopId);

  const toast = (message) => {
    const element = document.getElementById("toast");
    if (!element) return;
    element.textContent = message;
    element.hidden = false;
    window.clearTimeout(element._timer);
    element._timer = window.setTimeout(() => { element.hidden = true; }, 4200);
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const payload = await response.json().catch(() => ({ message: "The server returned an unreadable response." }));
    if (!response.ok) throw new Error(payload.message || "Request failed.");
    return payload;
  };

  const setBusy = (button, busy) => {
    if (!button) return;
    button.disabled = busy;
    const spinner = button.querySelector(".spinner");
    if (spinner) spinner.hidden = !busy;
  };

  if (page.dataset.page === "inventory") {
    const form = document.getElementById("movement-form");
    const search = document.getElementById("stock-search");
    search?.addEventListener("input", () => {
      const term = search.value.trim().toLowerCase();
      let visible = 0;
      document.querySelectorAll("#inventory-table tbody tr").forEach((row) => {
        const match = row.dataset.search.includes(term);
        row.hidden = !match;
        if (match) visible += 1;
      });
      document.getElementById("inventory-empty").hidden = visible > 0;
    });

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = form.querySelector(".form-message");
      message.hidden = true;
      form.querySelectorAll("[aria-invalid]").forEach((field) => field.removeAttribute("aria-invalid"));
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      const data = Object.fromEntries(new FormData(form));
      data.shop_id = shopId;
      data.product_id = Number(data.product_id);
      data.quantity = Number(data.quantity);
      const button = form.querySelector("button[type=submit]");
      setBusy(button, true);
      try {
        const result = await requestJson("/api/v1/movements", { method: "POST", body: JSON.stringify(data) });
        const row = document.querySelector(`[data-product-row="${data.product_id}"]`);
        if (row) {
          row.querySelector("[data-balance]").textContent = result.item.on_hand;
          row.querySelector("[data-stock-value]").textContent = `R${Number(result.item.stock_value).toFixed(2)}`;
          const badge = row.querySelector("[data-stock-status]");
          badge.textContent = result.item.status === "out" ? "Out" : result.item.status === "low" ? "Low" : "Healthy";
          badge.className = `badge ${result.item.status === "out" ? "badge-red" : result.item.status === "low" ? "badge-amber" : "badge-green"}`;
        }
        const option = form.querySelector(`select[name="product_id"] option[value="${data.product_id}"]`);
        if (option) option.textContent = `${option.dataset.productName} (${result.item.on_hand} on hand)`;
        form.reset();
        toast(result.message);
      } catch (error) {
        message.textContent = error.message;
        message.hidden = false;
      } finally {
        setBusy(button, false);
      }
    });
  }

  if (page.dataset.page === "replenishment") {
    const form = document.getElementById("recommendation-form");
    const table = document.getElementById("recommendation-table");
    const tbody = table.querySelector("tbody");
    const empty = document.getElementById("recommendation-empty");
    const loading = document.getElementById("recommendation-loading");
    const errorState = document.getElementById("planner-error");
    const summary = document.getElementById("basket-summary");
    const status = document.getElementById("recommendation-status");
    let currentItems = [];

    const money = (value) => `R${Number(value).toLocaleString("en-ZA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const calculate = async () => {
      if (!form.checkValidity()) { form.reportValidity(); return; }
      const data = new FormData(form);
      const supplierId = Number(data.get("supplier_id"));
      const budget = Number(data.get("budget"));
      const button = form.querySelector("button[type=submit]");
      setBusy(button, true);
      empty.hidden = true;
      table.hidden = true;
      summary.hidden = true;
      errorState.hidden = true;
      loading.hidden = false;
      try {
        const result = await requestJson(`/api/v1/recommendations?shop_id=${shopId}&supplier_id=${supplierId}&budget=${budget}`);
        currentItems = result.items.filter((item) => item.allocated_quantity > 0);
        tbody.innerHTML = result.items.map((item) => `
          <tr>
            <td><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.sku)}${item.constraint ? `<span class="constraint-note">Limited by ${escapeHtml(item.constraint)}</span>` : ""}</small></td>
            <td>${item.daily_demand.toFixed(1)}</td>
            <td>${item.days_cover === null ? "No data" : `${item.days_cover.toFixed(1)} days`}</td>
            <td>${Math.ceil(item.target_stock)}</td>
            <td>${item.recommended_quantity}</td>
            <td><strong>${item.allocated_quantity}</strong></td>
            <td>${money(item.line_cost)}</td>
          </tr>`).join("");
        table.hidden = result.items.length === 0;
        empty.hidden = result.items.length > 0;
        summary.hidden = currentItems.length === 0;
        document.getElementById("product-cost").textContent = money(result.totals.product_cost);
        document.getElementById("delivery-cost").textContent = money(result.totals.delivery_fee);
        document.getElementById("total-cost").textContent = money(result.totals.total_cost);
        status.textContent = result.message;
      } catch (error) {
        errorState.querySelector("p").textContent = error.message;
        errorState.hidden = false;
        status.textContent = "The calculation needs attention.";
      } finally {
        loading.hidden = true;
        setBusy(button, false);
      }
    };

    form?.addEventListener("submit", (event) => { event.preventDefault(); calculate(); });
    document.querySelector("[data-retry]")?.addEventListener("click", calculate);
    document.getElementById("create-order")?.addEventListener("click", async (event) => {
      if (!currentItems.length) return;
      const button = event.currentTarget;
      button.disabled = true;
      const supplierId = Number(new FormData(form).get("supplier_id"));
      try {
        const result = await requestJson("/api/v1/orders", {
          method: "POST",
          body: JSON.stringify({ shop_id: shopId, supplier_id: supplierId, lines: currentItems.map((item) => ({ product_id: item.product_id, quantity: item.allocated_quantity })) }),
        });
        toast(result.message);
        window.setTimeout(() => { window.location.href = `/orders?shop_id=${shopId}`; }, 700);
      } catch (error) {
        toast(error.message);
        button.disabled = false;
      }
    });
  }

  if (page.dataset.page === "orders") {
    document.querySelectorAll("[data-order-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const card = button.closest("[data-order-id]");
        const orderId = card.dataset.orderId;
        const action = button.dataset.orderAction;
        button.disabled = true;
        try {
          const result = await requestJson(`/api/v1/orders/${orderId}/${action}`, { method: "POST", body: "{}" });
          toast(result.message);
          window.setTimeout(() => window.location.reload(), 600);
        } catch (error) {
          toast(error.message);
          button.disabled = false;
        }
      });
    });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }
})();
