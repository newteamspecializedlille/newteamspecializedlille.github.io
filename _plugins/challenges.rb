# frozen_string_literal: true

# Classements « challenge route » et « challenge boue » calculés au build à partir de _data/team.json.
#
# Expose, pour chaque saison, site.data["challenge<année>"] et site.data["boue<année>"] avec la même forme que
# les anciens fichiers _data/challenge*.json / boue*.json (point_*, challenge_year, update_date, challenge) :
# les gabarits (challenge.html, rider.html) et les pages `data_file:` n'ont pas à changer.
#
# - challenge route  = résultats `road` de la saison (année civile)
# - challenge boue   = résultats `cx` + `vtt` de la saison (année + 1 dès août)
# - barèmes et règle « un abandon compte-t-il comme participation ? » : _data/challenge_rules.json
module Challenges
  FRENCH_MONTHS = %w[janvier février mars avril mai juin juillet août septembre octobre novembre décembre].freeze
  DISCIPLINES = { "challenge" => %w[road], "boue" => %w[cx vtt] }.freeze

  module_function

  # Points d'un résultat : barème de la place + participation ; un abandon vaut 0 (ou la participation si la règle l'autorise).
  def points_for(result, scale, abandon_counts)
    if result["status"]
      return abandon_counts ? scale["point_participation"] : 0
    end
    rank = result["rank"]
    return 0 unless rank.is_a?(Integer)

    base = if rank == 1 then scale["point_win"]
           elsif rank <= 5 then scale["point_top5"]
           elsif rank <= 10 then scale["point_top10"]
           elsif rank <= 15 then scale["point_top15"] || 0
           else 0
           end
    base + scale["point_participation"]
  end

  def seasons_in_data(members, disciplines)
    members.flat_map { |m| disciplines.flat_map { |d| (m[d] || {}).keys } }.uniq
  end

  # Saisons à construire : celles du fichier de règles + les saisons plus récentes présentes dans les données (barème « default »).
  def seasons_to_build(rules_for_kind, members, disciplines)
    explicit = rules_for_kind.keys.reject { |k| k == "default" }
    latest = explicit.map(&:to_i).max || 0
    newer = seasons_in_data(members, disciplines).select { |y| y.to_i > latest }
    (explicit + newer).uniq.sort
  end

  def last_result_date(members, disciplines, season)
    dates = members.flat_map { |m| disciplines.flat_map { |d| ((m[d] || {})[season] || []).map { |r| r["date"] } } }
    dates.max
  end

  def french_date(iso)
    return nil unless iso

    year, month, day = iso.split("-").map(&:to_i)
    "#{day} #{FRENCH_MONTHS[month - 1]} #{year}"
  end

  def build(kind, season, members, scale, abandon_counts)
    disciplines = DISCIPLINES.fetch(kind)
    totals = members.map do |member|
      results = disciplines.flat_map { |d| (member[d] || {})[season] || [] }
      [member["name"], results.sum { |r| points_for(r, scale, abandon_counts) }]
    end
    ranking = totals.sort_by { |name, points| [-points, name] }.to_h
    scale.merge(
      "update_date" => french_date(last_result_date(members, disciplines, season)),
      "update_iso" => last_result_date(members, disciplines, season).to_s,
      "challenge_year" => season,
      "challenge" => ranking
    )
  end

  def generate(site)
    team = site.data["team"]
    rules = site.data["challenge_rules"]
    return unless team && rules

    members = team["team_members"]
    abandon_counts = rules["abandon_counts"] == true
    DISCIPLINES.each_key do |kind|
      rules_for_kind = rules[kind] || {}
      seasons_to_build(rules_for_kind, members, DISCIPLINES[kind]).each do |season|
        scale = rules_for_kind[season] || rules_for_kind["default"]
        next unless scale

        site.data["#{kind}#{season}"] = build(kind, season, members, scale, abandon_counts)
      end
    end
    # clés triées comme le chargement de _data/ (la page coureur parcourt site.data : boue avant challenge)
    site.data.replace(site.data.sort_by { |key, _| key }.to_h)
  end
end

Jekyll::Hooks.register :site, :post_read do |site|
  Challenges.generate(site)
end
