/* Tablesort, after the engine and its number plugin have loaded from the CDN.
 *
 * `document$.subscribe` is Zensical's own hook: the callback runs once on the
 * first page and again after every navigation, which is what keeps the sort
 * alive on a reference page reachable in more than one way. Only the gates
 * page opts in -- the table carries the `sortable` class, and a table that
 * stops sorting is more honest than every table sorting.
 *
 * The number plugin (tablesort.number.min.js) registers itself when it loads.
 * Its detect() requires a column's cells to *start* with a digit, and the
 * threshold column's cells are prose or backtick-quoted names, so none of them
 * auto-detect. Forcing the method on that one header via data-sort-method makes
 * it sort by value; the rest of the table stays string-sorted, which is the
 * honest sort for prose.
 */
document$.subscribe(function () {
  document.querySelectorAll(".sortable table").forEach(function (table) {
    table.querySelectorAll("th").forEach(function (th) {
      if (th.textContent.trim() === "Threshold") {
        th.setAttribute("data-sort-method", "number");
      }
    });
    new Tablesort(table);
  });
});