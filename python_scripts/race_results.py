class RaceResults:
    def __init__(self, name):
        self.name = name
        self.race_date = ""
        self.race_type = ""
        self.race_year = ""

        self.one = {}
        self.one_riders = 0
        self.two = {}
        self.two_riders = 0
        self.three = {}
        self.three_riders = 0
        self.cadet = {}
        self.cadet_riders = 0
        self.fem = {}
        self.fem_riders = 0

        self.VTTSeniorsA_riders = 0
        self.VTTSeniorsB_riders = 0
        self.VTTVeteransA_riders = 0
        self.VTTVeteransB_riders = 0
        self.VTTVeteransC_riders = 0

        self.VTTSeniorsA = {}
        self.VTTSeniorsB = {}
        self.VTTVeteransA = {}
        self.VTTVeteransB = {}
        self.VTTVeteransC = {}

        self.scratch = {}
