/* Áp dụng nền sáng hoặc tối người dùng đã chọn trước khi trang được vẽ, để không nháy màu. Tệp riêng vì CSP không cho mã viết thẳng trong HTML. */
try {
  const t = JSON.parse(localStorage.getItem("cv_prefs") || "{}").theme;
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
} catch (e) { /* trình duyệt chặn lưu: theo hệ điều hành */ }
