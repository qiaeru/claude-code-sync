// Apply the saved theme before first paint to avoid a flash of wrong theme.
// Loaded as a synchronous script in <head> (instead of an inline block) so the
// Content-Security-Policy can stay at default-src 'self' with no inline carve-out.
(function () {
  try {
    var t = localStorage.getItem("theme");
    if (t === "light" || t === "dark") {
      document.documentElement.setAttribute("data-theme", t);
    }
  } catch (e) {}
})();
