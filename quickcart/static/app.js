/* QuickCart frontend - vanilla JS, shared across all pages. */
"use strict";

async function request(method, path, body) {
  const options = { method: method, credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const resp = await fetch(path, options);
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    data = { error: "unexpected server response" };
  }
  return { status: resp.status, data: data };
}

function rupee(value) {
  return "\u20B9" + Number(value).toFixed(2);
}

function esc(text) {
  const div = document.createElement("div");
  div.textContent = text === null || text === undefined ? "" : String(text);
  return div.innerHTML;
}

function redirectIfLoggedOut(status) {
  if (status === 401) {
    location.href = "/login";
    return true;
  }
  return false;
}

function setMsg(el, text, kind) {
  el.textContent = text;
  el.className = "msg " + (kind || "");
}

function updateNavCount(cartData) {
  const el = document.getElementById("cart-count");
  const total = (cartData.items || []).reduce(function (sum, item) {
    return sum + item.quantity;
  }, 0);
  el.textContent = String(total);
}

/* ---------- navbar ---------- */

async function initNav() {
  const logout = document.getElementById("nav-logout");
  if (logout) {
    logout.addEventListener("click", async function (event) {
      event.preventDefault();
      await request("POST", "/api/logout");
      location.href = "/login";
    });
  }
  const profile = await request("GET", "/api/profile");
  const guests = document.querySelectorAll(".guest-only");
  const auths = document.querySelectorAll(".auth-only");
  if (profile.status !== 200) {
    auths.forEach(function (el) { el.hidden = true; });
    return;
  }
  guests.forEach(function (el) { el.hidden = true; });
  document.getElementById("nav-user").textContent = "Hi, " + profile.data.name;
  const cart = await request("GET", "/api/cart");
  if (cart.status === 200) updateNavCount(cart.data);
}

/* ---------- register / login ---------- */

function initRegister() {
  const errEl = document.getElementById("reg-error");
  document.getElementById("reg-submit").addEventListener("click", async function () {
    const resp = await request("POST", "/api/register", {
      name: document.getElementById("reg-name").value,
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-password").value,
    });
    if (resp.status === 201) {
      location.href = "/login?registered=1";
    } else {
      setMsg(errEl, resp.data.error || "Registration failed", "error");
    }
  });
}

function initLogin() {
  const errEl = document.getElementById("login-error");
  if (new URLSearchParams(location.search).get("registered") === "1") {
    document.getElementById("login-success").hidden = false;
  }
  document.getElementById("login-submit").addEventListener("click", async function () {
    const resp = await request("POST", "/api/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    if (resp.status === 200) {
      location.href = "/products";
    } else {
      setMsg(errEl, resp.data.error || "Login failed", "error");
    }
  });
}

/* ---------- products list ---------- */

function initProducts() {
  const list = document.getElementById("product-list");
  const emptyEl = document.getElementById("no-results");
  const msg = document.getElementById("page-message");
  const categorySelect = document.getElementById("category-filter");

  function buildQuery() {
    const params = new URLSearchParams();
    const search = document.getElementById("search-input").value.trim();
    const category = categorySelect.value;
    const min = document.getElementById("min-price").value.trim();
    const max = document.getElementById("max-price").value.trim();
    const sort = document.getElementById("sort-select").value;
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    if (min !== "") params.set("min_price", min);
    if (max !== "") params.set("max_price", max);
    if (sort) params.set("sort", sort);
    const query = params.toString();
    return query ? "?" + query : "";
  }

  async function load() {
    const resp = await request("GET", "/api/products" + buildQuery());
    if (resp.status !== 200) {
      setMsg(msg, resp.data.error || "Failed to load products", "error");
      list.innerHTML = "";
      emptyEl.hidden = false;
      return;
    }
    const items = resp.data;
    list.innerHTML = items
      .map(function (p) {
        return (
          '<div class="product-card" data-product-id="' + p.id + '">' +
          '<a class="product-name" href="/products/' + p.id + '">' + esc(p.name) + "</a>" +
          '<div class="product-price">' + rupee(p.price) + "</div>" +
          '<div class="product-stock">' +
          (p.stock === 0 ? "Out of stock" : "In stock: " + p.stock) +
          "</div>" +
          '<button class="add-to-cart-btn" data-product-id="' + p.id + '" type="button">Add to Cart</button>' +
          "</div>"
        );
      })
      .join("");
    emptyEl.hidden = items.length !== 0;
  }

  list.addEventListener("click", async function (event) {
    const btn = event.target.closest(".add-to-cart-btn");
    if (!btn) return;
    const resp = await request("POST", "/api/cart/add", {
      product_id: Number(btn.dataset.productId),
      quantity: 1,
    });
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status === 200) {
      setMsg(msg, "Added to cart", "success");
      updateNavCount(resp.data);
    } else {
      setMsg(msg, resp.data.error || "Could not add to cart", "error");
    }
  });

  document.getElementById("apply-filters").addEventListener("click", function (event) {
    event.preventDefault();
    load();
  });

  document.getElementById("clear-filters").addEventListener("click", function (event) {
    event.preventDefault();
    document.getElementById("search-input").value = "";
    categorySelect.value = "";
    document.getElementById("min-price").value = "";
    document.getElementById("max-price").value = "";
    document.getElementById("sort-select").value = "";
    load();
  });

  (async function () {
    // categories come from the unfiltered list, before the first filtered load
    const all = await request("GET", "/api/products");
    if (all.status === 200) {
      const seen = {};
      all.data.forEach(function (p) {
        if (p.category && !seen[p.category]) {
          seen[p.category] = true;
          const opt = document.createElement("option");
          opt.value = p.category;
          opt.textContent = p.category;
          categorySelect.appendChild(opt);
        }
      });
    }
    load();
  })();
}

/* ---------- product detail ---------- */

function initProductDetail() {
  const productId = Number(location.pathname.split("/").pop());
  const msg = document.getElementById("page-message");

  (async function () {
    const resp = await request("GET", "/api/products/" + productId);
    if (resp.status !== 200) {
      setMsg(msg, resp.status === 404 ? "product not found" : (resp.data.error || "Failed to load product"), "error");
      return;
    }
    const p = resp.data;
    document.getElementById("product-name").textContent = p.name;
    document.getElementById("product-price").textContent = rupee(p.price);
    document.getElementById("product-category").textContent = p.category || "";
    document.getElementById("product-stock").textContent =
      p.stock === 0 ? "Out of stock" : "In stock: " + p.stock;
    document.getElementById("product-description").textContent = p.description || "";

    document.getElementById("add-to-cart-btn").addEventListener("click", async function () {
      // Number, not parseInt: a value like 2.5 must reach the API (which rejects it), not be truncated to 2.
      const quantity = Number(document.getElementById("qty-input").value);
      const add = await request("POST", "/api/cart/add", { product_id: productId, quantity: quantity });
      if (redirectIfLoggedOut(add.status)) return;
      if (add.status === 200) {
        setMsg(msg, "Added to cart", "success");
        updateNavCount(add.data);
      } else {
        setMsg(msg, add.data.error || "Could not add to cart", "error");
      }
    });
  })();
}

/* ---------- cart ---------- */

function initCart() {
  const list = document.getElementById("cart-items");
  const emptyEl = document.getElementById("cart-empty");
  const msg = document.getElementById("page-message");
  const couponMsg = document.getElementById("coupon-message");
  const couponInput = document.getElementById("coupon-input");
  const checkoutBtn = document.getElementById("checkout-btn");

  function fill(data) {
    list.innerHTML = (data.items || [])
      .map(function (it) {
        return (
          '<div class="cart-row" data-product-id="' + it.product_id + '">' +
          '<span class="cart-name">' + esc(it.name) + "</span>" +
          '<span class="cart-price">' + rupee(it.price) + "</span>" +
          '<input class="cart-qty" type="number" value="' + it.quantity + '" min="1" max="10">' +
          '<button class="update-btn" type="button">Update</button>' +
          '<button class="remove-btn" type="button">Remove</button>' +
          '<span class="line-total">' + rupee(it.line_total) + "</span>" +
          "</div>"
        );
      })
      .join("");
    document.getElementById("cart-subtotal").textContent = rupee(data.subtotal);
    document.getElementById("cart-discount").textContent = rupee(data.discount);
    document.getElementById("cart-total").textContent = rupee(data.total);
    couponMsg.textContent = data.coupon_message || "";
    couponMsg.className = "msg" + (data.coupon_message ? " msg-error" : "");
    const empty = (data.items || []).length === 0;
    emptyEl.hidden = !empty;
    checkoutBtn.hidden = empty;
    updateNavCount(data);
  }

  (async function () {
    const view = await request("GET", "/api/cart");
    if (redirectIfLoggedOut(view.status)) return;
    fill(view.data);
  })();

  list.addEventListener("click", async function (event) {
    const row = event.target.closest(".cart-row");
    if (!row) return;
    const productId = Number(row.dataset.productId);
    if (event.target.matches(".update-btn")) {
      const quantity = Number(row.querySelector(".cart-qty").value);
      const resp = await request("PUT", "/api/cart/update", { product_id: productId, quantity: quantity });
      if (redirectIfLoggedOut(resp.status)) return;
      if (resp.status === 200) {
        fill(resp.data);
        setMsg(msg, "Cart updated", "success");
      } else {
        setMsg(msg, resp.data.error || "Could not update cart", "error");
      }
    } else if (event.target.matches(".remove-btn")) {
      const resp = await request("DELETE", "/api/cart/remove/" + productId);
      if (redirectIfLoggedOut(resp.status)) return;
      if (resp.status === 200) {
        fill(resp.data);
        setMsg(msg, "Product removed from cart", "success");
      } else {
        setMsg(msg, resp.data.error || "Could not remove product", "error");
      }
    }
  });

  document.getElementById("apply-coupon-btn").addEventListener("click", async function () {
    const resp = await request("POST", "/api/cart/coupon", { code: couponInput.value });
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status === 200) {
      fill(resp.data);
      setMsg(couponMsg, resp.data.message, "success");
    } else {
      setMsg(couponMsg, resp.data.error || "Could not apply coupon", "error");
    }
  });

  document.getElementById("remove-coupon-btn").addEventListener("click", async function () {
    const resp = await request("DELETE", "/api/cart/coupon");
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status === 200) {
      fill(resp.data);
      setMsg(couponMsg, resp.data.message, "success");
    } else {
      setMsg(couponMsg, resp.data.error || "Could not remove coupon", "error");
    }
  });

  checkoutBtn.addEventListener("click", function () {
    location.href = "/checkout";
  });
}

/* ---------- checkout ---------- */

function initCheckout() {
  const errEl = document.getElementById("checkout-error");

  (async function () {
    const view = await request("GET", "/api/cart");
    if (redirectIfLoggedOut(view.status)) return;
    const data = view.data;
    const items = data.items || [];
    document.getElementById("checkout-subtotal").textContent = rupee(data.subtotal);
    document.getElementById("checkout-discount").textContent = rupee(data.discount);
    document.getElementById("checkout-total").textContent = rupee(data.total);
    if (items.length === 0) {
      setMsg(errEl, "Your cart is empty. Add products before checkout.", "error");
      document.getElementById("place-order-btn").disabled = true;
    }
  })();

  document.getElementById("place-order-btn").addEventListener("click", async function () {
    const body = {
      shipping_address: document.getElementById("shipping-address").value,
      name_on_card: document.getElementById("card-name").value,
      card_number: document.getElementById("card-number").value,
      expiry: document.getElementById("card-expiry").value,
      cvv: document.getElementById("card-cvv").value,
    };
    const resp = await request("POST", "/api/checkout", body);
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status === 201) {
      location.href = "/orders/" + resp.data.id + "?placed=1";
    } else {
      setMsg(errEl, resp.data.error || "Checkout failed", "error");
    }
  });
}

/* ---------- orders ---------- */

function initOrders() {
  const tbody = document.getElementById("orders-body");
  const emptyEl = document.getElementById("orders-empty");

  (async function () {
    const resp = await request("GET", "/api/orders");
    if (redirectIfLoggedOut(resp.status)) return;
    const orders = resp.status === 200 ? resp.data : [];
    tbody.innerHTML = orders
      .map(function (o) {
        return (
          '<tr class="order-row" data-order-id="' + o.id + '">' +
          '<td class="order-id">' + o.id + "</td>" +
          '<td class="order-date">' + esc(o.created_at) + "</td>" +
          '<td class="order-total">' + rupee(o.total) + "</td>" +
          '<td class="order-status">' + esc(o.status) + "</td>" +
          '<td><a class="view-order" href="/orders/' + o.id + '">View</a></td>' +
          "</tr>"
        );
      })
      .join("");
    emptyEl.hidden = orders.length !== 0;
  })();
}

/* ---------- order detail ---------- */

function initOrderDetail() {
  const orderId = Number(location.pathname.split("/").pop());
  const msg = document.getElementById("page-message");

  (async function () {
    const resp = await request("GET", "/api/orders/" + orderId);
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status !== 200) {
      setMsg(msg, resp.data.error || "order not found", "error");
      return;
    }
    const o = resp.data;
    document.getElementById("order-id").textContent = o.id;
    document.getElementById("order-status").textContent = o.status;
    document.getElementById("order-subtotal").textContent = rupee(o.subtotal);
    document.getElementById("order-discount").textContent = rupee(o.discount);
    document.getElementById("order-total").textContent = rupee(o.total);
    document.getElementById("order-coupon").textContent = o.coupon_code || "-";
    document.getElementById("order-address").textContent = o.shipping_address;
    document.getElementById("order-card").textContent = "**** **** **** " + o.card_last4;
    document.getElementById("order-items").innerHTML = (o.items || [])
      .map(function (it) {
        return (
          '<div class="order-item">' +
          '<span class="item-name">' + esc(it.product_name) + "</span>" +
          '<span class="item-price">' + rupee(it.price) + "</span>" +
          '<span class="item-qty">' + it.quantity + "</span>" +
          "</div>"
        );
      })
      .join("");

    const flow = ["Placed", "Packed", "Shipped", "Delivered"];
    const index = flow.indexOf(o.status);
    ["step-placed", "step-packed", "step-shipped", "step-delivered"].forEach(function (id, i) {
      document.getElementById(id).classList.toggle("active", i === index);
    });

    if (new URLSearchParams(location.search).get("placed") === "1") {
      document.getElementById("order-success").hidden = false;
    }

    const select = document.getElementById("status-select");
    select.value = o.status;
    document.getElementById("update-status-btn").addEventListener("click", async function () {
      const upd = await request("PUT", "/api/orders/" + orderId + "/status", { status: select.value });
      if (redirectIfLoggedOut(upd.status)) return;
      if (upd.status === 200) {
        location.reload();
      } else {
        setMsg(msg, upd.data.error || "Could not update status", "error");
      }
    });
  })();
}

/* ---------- profile ---------- */

function initProfile() {
  const msgEl = document.getElementById("profile-message");

  (async function () {
    const resp = await request("GET", "/api/profile");
    if (redirectIfLoggedOut(resp.status)) return;
    const p = resp.data;
    document.getElementById("profile-name").value = p.name || "";
    document.getElementById("profile-email").value = p.email || "";
    document.getElementById("profile-phone").value = p.phone || "";
    document.getElementById("profile-address").value = p.address || "";
  })();

  document.getElementById("profile-save").addEventListener("click", async function () {
    const resp = await request("PUT", "/api/profile", {
      name: document.getElementById("profile-name").value,
      phone: document.getElementById("profile-phone").value,
      address: document.getElementById("profile-address").value,
    });
    if (redirectIfLoggedOut(resp.status)) return;
    if (resp.status === 200) {
      setMsg(msgEl, "Profile updated", "success");
    } else {
      setMsg(msgEl, resp.data.error || "Could not save profile", "error");
    }
  });
}

/* ---------- page dispatch ---------- */

document.addEventListener("DOMContentLoaded", function () {
  initNav();
  if (document.getElementById("reg-submit")) initRegister();
  if (document.getElementById("login-submit")) initLogin();
  if (document.getElementById("product-list")) initProducts();
  if (document.getElementById("product-description")) initProductDetail();
  if (document.getElementById("cart-items")) initCart();
  if (document.getElementById("place-order-btn")) initCheckout();
  if (document.getElementById("orders-table")) initOrders();
  if (document.getElementById("order-items")) initOrderDetail();
  if (document.getElementById("profile-save")) initProfile();
});
