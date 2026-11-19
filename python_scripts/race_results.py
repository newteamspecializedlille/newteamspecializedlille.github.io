class RaceResults:
    """Résultats d'une course tels qu'affichés dans le post.

    team[catégorie] = {membre: place} ; riders[catégorie] = nombre de partants ; scratch = classement général.
    Les catégories sont celles de parse_results.POST_SECTIONS (+ les catégories jeunes).
    """

    def __init__(self, name):
        self.name = name
        self.race_date = ""
        self.race_type = ""
        self.race_year = ""
        self.team = {}
        self.riders = {}
        self.scratch = {}

    def add_rider(self, category):
        self.riders[category] = self.riders.get(category, 0) + 1

    def add_team_result(self, category, member, result):
        self.team.setdefault(category, {})[member] = result
