module Geocoding
  class Autocomplete
    PHOTON_URL = "https://photon.komoot.io/api"

    def initialize(query:, limit: 5, lat: nil, lon: nil)
      @query = query
      @limit = limit
      @lat = lat.present? ? lat.to_f : nil
      @lon = lon.present? ? lon.to_f : nil
    end

    def call
      return [] if query.blank? || query.length < 2

      results = fetch_results
      results = sort_by_proximity(results) if bias_coordinates?
      results.first(limit)
    end

    private

    attr_reader :query, :limit, :lat, :lon

    def fetch_results
      response = HTTP.get(PHOTON_URL, params: request_params)
      return [] unless response.status.success?

      parse_features(response.parse)
    end

    def request_params
      { q: query, limit: fetch_limit }.tap do |p|
        p[:lat] = lat if valid_lat?
        p[:lon] = lon if valid_lon?
      end
    end

    def fetch_limit
      [ [ limit * 3, 20 ].max, 50 ].min
    end

    def bias_coordinates?
      valid_lat? && valid_lon?
    end

    def valid_lat?
      lat.present? && lat.abs <= 90
    end

    def valid_lon?
      lon.present? && lon.abs <= 180
    end

    def parse_features(data)
      (data["features"] || []).filter_map { |feature| parse_feature(feature) }
    end

    def parse_feature(feature)
      props = feature["properties"] || {}
      lat, lon = extract_coordinates(feature)
      return unless lat && lon

      {
        name: props["name"],
        address: build_address(props),
        latitude: lat,
        longitude: lon,
        city: props["city"],
        country: props["country"]
      }
    end

    def extract_coordinates(feature)
      coords = feature.dig("geometry", "coordinates") || []
      lon, lat = coords[0], coords[1]
      return if lon.blank? || lat.blank?

      [ lat, lon ]
    end

    def sort_by_proximity(results)
      results.sort_by do |r|
        dlat = r[:latitude].to_f - lat
        dlon = r[:longitude].to_f - lon
        (dlat**2) + (dlon**2)
      end
    end

    def build_address(props)
      [ props["street"], props["city"], props["state"], props["country"] ]
        .compact.join(", ")
    end
  end
end
