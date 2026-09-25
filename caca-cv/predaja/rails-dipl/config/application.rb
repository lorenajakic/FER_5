require_relative "boot"

require "rails/all"

Bundler.require(*Rails.groups)

module TripPlanner
  class Application < Rails::Application
    config.load_defaults 8.0

    config.autoload_lib(ignore: %w[assets tasks])

    config.i18n.default_locale = :en
    config.i18n.available_locales = [ :en, :hr ]
    config.i18n.fallbacks = true

    config.active_storage.resolve_model_to_route = :rails_storage_proxy
  end
end
