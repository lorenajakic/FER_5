module Trips
  class ItinerariesController < BaseController
    def show
      @itinerary = trip.itinerary
    end

    def update
      plan_json = parse_plan_json
      return head :unprocessable_entity unless plan_json

      itinerary = trip.itinerary || trip.build_itinerary
      itinerary.update!(plan_json: plan_json)

      respond_to do |format|
        format.turbo_stream do
          render turbo_stream: [
            turbo_stream.replace(
              "itinerary_panel",
              partial: "trips/itineraries/panel",
              locals: { trip: trip, itinerary: itinerary }
            ),
            turbo_stream.append(
              "toast_stack_top",
              partial: "shared/turbo_toast",
              locals: { message: t("itinerary.saved"), variant: :notice }
            )
          ]
        end
        format.json { render json: { status: "ok" } }
        format.html { redirect_to trip_itinerary_path(trip) }
      end
    end

    private

    def parse_plan_json
      raw = params[:plan_json]
      return raw if raw.is_a?(Hash)
      JSON.parse(raw)
    rescue
      nil
    end
  end
end
