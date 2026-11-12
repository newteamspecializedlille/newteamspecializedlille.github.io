(function () {
  "use strict";

  var table = document.querySelector(".velo-road-stats__table");
  if (!table) return;

  var body = table.tBodies[0];
  var headers = Array.from(table.querySelectorAll("thead th[data-sort]"));
  var collator = new Intl.Collator("fr");

  headers.forEach(function (header, column) {
    var label = header.textContent.trim();
    var button = document.createElement("button");
    var indicator = document.createElement("span");

    button.type = "button";
    button.className = "velo-road-stats__sort";
    button.textContent = label + " ";
    indicator.className = "velo-road-stats__sort-indicator";
    indicator.setAttribute("aria-hidden", "true");
    indicator.textContent = "\u2195";
    button.appendChild(indicator);
    header.replaceChildren(button);

    button.addEventListener("click", function () {
      var ascending = header.getAttribute("aria-sort") === "descending";
      if (header.dataset.sort === "text") {
        ascending = header.getAttribute("aria-sort") !== "ascending";
      }

      var rows = Array.from(body.rows);
      rows.sort(function (left, right) {
        var leftValue = left.cells[column].textContent.trim();
        var rightValue = right.cells[column].textContent.trim();
        var comparison = header.dataset.sort === "number"
          ? Number(leftValue) - Number(rightValue)
          : collator.compare(leftValue, rightValue);

        return (ascending ? comparison : -comparison)
          || collator.compare(left.cells[0].textContent, right.cells[0].textContent);
      });

      headers.forEach(function (otherHeader) {
        otherHeader.removeAttribute("aria-sort");
        otherHeader.querySelector(".velo-road-stats__sort-indicator").textContent = "\u2195";
      });
      header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      indicator.textContent = ascending ? "\u2191" : "\u2193";
      rows.forEach(function (row) {
        body.appendChild(row);
      });
    });
  });
})();
