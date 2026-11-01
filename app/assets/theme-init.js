// Freyja Consulting dark-mode toggle -- pure client-side, no server round-trip.
//
// Loaded as a real <script src> (via pn.config.js_files in app/theme.py),
// not injected through a Panel HTML pane's innerHTML -- browsers don't
// execute <script> tags inserted that way, which an earlier inline-script
// version of this logic ran into.
//
// Applies the persisted preference immediately, before Panel's own
// components finish rendering, so there's no flash of the wrong theme.
// The toggle button itself is wired via event delegation on `document`
// since it's rendered later, as part of Panel's component tree -- and
// because the button lives inside a Bokeh custom element's shadow root,
// event.target would be retargeted to the shadow host once the click
// bubbles past the shadow boundary, so this uses composedPath() instead,
// which preserves the real originating element.
(function () {
  var KEY = "freyja-theme";
  var root = document.documentElement;

  function apply(dark) {
    root.classList.toggle("freyja-dark", dark);
    var btn = document.getElementById("freyja-theme-toggle");
    if (btn) {
      btn.setAttribute("aria-pressed", String(dark));
      btn.innerHTML = dark ? "&#9790;" : "&#9728;";
    }
  }

  apply(localStorage.getItem(KEY) === "dark");

  document.addEventListener("click", function (event) {
    var origin = event.composedPath ? event.composedPath()[0] : event.target;
    if (origin && origin.id === "freyja-theme-toggle") {
      var dark = !root.classList.contains("freyja-dark");
      localStorage.setItem(KEY, dark ? "dark" : "light");
      apply(dark);
    }
  });
})();
