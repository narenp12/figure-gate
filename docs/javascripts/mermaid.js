/* Mermaid, after the engine has loaded from the CDN.
 *
 * The engine is not in the Zensical bundle -- verified, the bundle ships the
 * `--md-mermaid-*` theme variables but no renderer -- so it arrives as a CDN
 * script and draws the diagrams the custom fence wrote as `.mermaid` divs.
 * The bundle's theme variables are what make the diagrams follow light and
 * dark mode with no extra stylesheet.
 *
 * `startOnLoad: false` because the renderer runs here, after navigation, via
 * the same `document$.subscribe` the tablesort init uses. Without the wait, a
 * diagram on a page reached by navigation would be left as its source text.
 */
document$.subscribe(function () {
  var blocks = document.querySelectorAll(".mermaid");
  if (!blocks.length) {
    return;
  }
  mermaid.initialize({ startOnLoad: false });
  blocks.forEach(function (block) {
    mermaid.run({ nodes: [block] });
  });
});