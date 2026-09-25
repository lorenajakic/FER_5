require "net/http"
require "json"

module Trips
  class AgentService
    BASE_URL = ENV.fetch("AGENT_BASE_URL", "http://localhost:8000")
    TOKEN    = ENV.fetch("AGENT_TOKEN", "")

    def self.call(...)
      new(...).call
    end

    def initialize(trip:, user_message:, conversation_history: [], current_plan: nil)
      @trip                 = trip
      @user_message         = user_message
      @conversation_history = conversation_history
      @current_plan         = current_plan
    end

    def call
      stream_response || error_response(@stream_error.presence || I18n.t("agent.errors.no_response"))
    rescue => e
      Rails.logger.error("[AgentService] #{e.class}: #{e.message}")
      error_response(I18n.t("agent.errors.unreachable"))
    end

    private

    attr_reader :trip, :user_message, :conversation_history, :current_plan

    def stream_response
      result = nil
      Net::HTTP.start(uri.host, uri.port, read_timeout: 180) do |http|
        http.request(request) { |response| result = parse_sse_stream(response) }
      end
      result
    end

    def parse_sse_stream(response)
      result = nil
      buffer = ""

      response.read_body do |chunk|
        buffer += chunk.gsub("\r\n", "\n")
        while (sep = buffer.index("\n\n"))
          result = parse_event(buffer[0...sep]) || result
          buffer = buffer[(sep + 2)..]
        end
      end

      result = parse_event(buffer) || result if buffer.present?
      result
    end

    def uri
      @uri ||= URI("#{BASE_URL}/chat")
    end

    def request
      Net::HTTP::Post.new(uri).tap do |req|
        req["Content-Type"]  = "application/json"
        req["Accept"]        = "text/event-stream"
        req["X-Agent-Token"] = TOKEN if TOKEN.present?
        req.body             = payload.to_json
      end
    end

    def payload
      {
        trip:                 trip_payload,
        places:               places_payload,
        place_comments:       comments_payload,
        conversation_history:,
        current_plan:,
        user_message:,
        thread_id:            "trip-#{trip.id}"
      }
    end

    def trip_payload
      {
        id:                       trip.id,
        title:                    trip.title,
        destination:              trip.destination,
        start_date:               trip.start_date&.iso8601,
        end_date:                 trip.end_date&.iso8601,
        participant_count:        trip.participants.count,
        accommodation_address:    trip.accommodation_address,
        accommodation_details:    trip.accommodation_details,
        accommodation_latitude:   trip.accommodation_latitude&.to_f,
        accommodation_longitude:  trip.accommodation_longitude&.to_f,
        arrival_transport_mode:   trip.arrival_transport_mode,
        arrival_at:               trip.arrival_at&.iso8601,
        arrival_details:          trip.arrival_details,
        departure_transport_mode: trip.departure_transport_mode,
        departure_at:             trip.departure_at&.iso8601,
        departure_details:        trip.departure_details
      }.compact
    end

    def places_payload
      trip.places.map do |place|
        { name: place.name, latitude: place.latitude.to_f, longitude: place.longitude.to_f, category: place.category }
      end
    end

    def comments_payload
      trip.places.flat_map do |place|
        place.place_comments.includes(:user).map do |comment|
          { place_name: place.name, user_name: comment.user.name, body: comment.body }
        end
      end.last(50)
    end

    def parse_event(block)
      event = block[/^event:\s*(.+)$/, 1]&.strip
      return unless event

      raw  = block.scan(/^data:\s*(.+)$/).flatten.join("\n")
      data = (JSON.parse(raw) if raw.present?)

      case event
      when "final"
        data
      when "error"
        @stream_error = data && data["message"]
        Rails.logger.error("[AgentService] agent error event: #{@stream_error}")
        nil
      end
    rescue JSON::ParserError
      nil
    end

    def error_response(msg)
      { "message" => msg, "structured_response" => {}, "intent" => "general" }
    end
  end
end
