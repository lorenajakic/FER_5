require "redcarpet"

module ApplicationHelper
  def render_chat_markdown(content)
    return "".html_safe if content.blank?

    renderer = Redcarpet::Render::HTML.new(
      no_images: true,
      safe_links_only: true,
      link_attributes: { target: "_blank", rel: "noopener noreferrer" }
    )
    md = Redcarpet::Markdown.new(renderer,
      autolink: true,
      no_intra_emphasis: true,
      fenced_code_blocks: true,
      strikethrough: true,
      space_after_headers: true
    )
    html = md.render(content.to_s)
    sanitize(html, tags: %w[p br strong em code pre a ul ol li hr h1 h2 h3 del],
                   attributes: %w[href target rel])
  end
end
