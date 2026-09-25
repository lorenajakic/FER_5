module Geocoding
  class Reverse
    PHOTON_REVERSE_URL = "https://photon.komoot.io/reverse"

    def initialize(lat:, lon:)
      @lat = lat.to_f
      @lon = lon.to_f
    end

    def call
      return unless valid_coordinates?

      feature = fetch_feature
      return unless feature

      build_result(feature)
    end

    private

    attr_reader :lat, :lon

    def valid_coordinates?
      lat.abs <= 90 && lon.abs <= 180
    end

    def fetch_feature
      response = HTTP.get(PHOTON_REVERSE_URL, params: { lat:, lon: })
      return unless response.status.success?

      response.parse.dig("features", 0)
    end

    def build_result(feature)
      props = feature["properties"] || {}
      lat, lon = extract_coordinates(feature)
      return unless lat && lon

      address = build_address(props)

      {
        name: props["name"].presence || address.presence,
        address:,
        latitude: lat,
        longitude: lon
      }
    end

    def extract_coordinates(feature)
      coords = feature.dig("geometry", "coordinates") || []
      lon, lat = coords[0], coords[1]
      return if lon.blank? || lat.blank?

      [ lat, lon ]
    end

    def build_address(props)
      [ props["street"], props["city"], props["state"], props["country"] ]
        .compact.join(", ")
    end
  end
end
