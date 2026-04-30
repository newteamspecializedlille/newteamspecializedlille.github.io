function updateDisplay() {
  var narrow = window.matchMedia('(max-width: 768px)').matches;
  var smoothWrapper = document.getElementById('smooth-wrapper');
  var titleLarge = document.getElementById('title-large');
  if (narrow && smoothWrapper && titleLarge) {
    smoothWrapper.removeAttribute('data-background');
    smoothWrapper.classList.add('no-background');
    titleLarge.style.display = 'none';
  } else if (smoothWrapper && titleLarge) {
    var image = smoothWrapper.getAttribute('data-name');
    smoothWrapper.setAttribute('data-background', image);
    titleLarge.style.display = 'block';
  }
  var conditional = document.querySelector('.conditional-display');
  if (conditional) {
    conditional.style.display = narrow ? 'block' : 'none';
  }
}

document.addEventListener('DOMContentLoaded', function () {
  updateDisplay();

  var flagElement = document.querySelector('.country-flag');
  if (flagElement && typeof CountryFlag !== 'undefined') {
    var flag = new CountryFlag(flagElement);
    flag.selectByAlpha2(flagElement.id);
  }

  var searchInput = document.getElementById('search');
  var resultsContainer = document.getElementById('results-list');
  if (searchInput && resultsContainer && typeof SimpleJekyllSearch !== 'undefined') {
    SimpleJekyllSearch({
      searchInput: searchInput,
      resultsContainer: resultsContainer,
      json: '/search-data.json',
      searchResultTemplate: '<li><span><a href="{url}">{title}</a></span></li>'
    });
  }
});

window.addEventListener('resize', updateDisplay);
