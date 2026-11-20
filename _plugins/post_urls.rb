# frozen_string_literal: true

# Index en mémoire des adresses d'articles (site.data["post_urls"] = { "/resultats/route/2026-04-12-etroeungt/" => true }).
# La page d'un coureur recalcule l'adresse de chaque course (discipline + date + nom) et n'affiche un lien que si l'article existe :
# plus besoin d'un fichier _data/race_urls.json.
Jekyll::Hooks.register :site, :post_read do |site|
  site.data["post_urls"] = site.posts.docs.to_h { |post| [post.url, true] }
end
