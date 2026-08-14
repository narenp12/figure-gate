/* Tablesort, after the engine and its number plugin have loaded from the CDN.
 *
 * `document$.subscribe` is Zensical's own hook: the callback runs once on the
 * first page and again after every navigation, which is what keeps the sort
 * alive on a reference page reachable in more than one way. Only the gates
 * page opts in -- the table carries the `sortable` class, and a table that
 * stops sorting is more honest than every table sorting.
 *
 * The number plugin (tablesort.number.min.js) registers itself when it loads,
 * so nothing else is needed for the threshold column to sort by value rather
 * than by string.
 */
document$.subscribe(function () {
  document.querySelectorAll("table.sortable").forEach(function (table) {
    new Tablesort(table);
  });
});