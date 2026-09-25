module Trips
  class PlacesController < BaseController
    def index
      @places = trip.places.includes(:added_by, :place_comments).order(created_at: :desc)
    end

    def create
      @place = trip.places.build(place_params)
      @place.added_by = current_user

      authorize @place

      if @place.save
        respond_to do |format|
          format.turbo_stream
          format.html { redirect_to trip_places_path(trip) }
        end
      else
        respond_to do |format|
          format.turbo_stream do
            render turbo_stream: turbo_stream.replace(
              'place_form_errors',
              partial: 'trips/places/form_errors',
              locals: { place: @place }
            )
          end
          format.html { redirect_to trip_places_path(trip), alert: @place.errors.full_messages.join(', ') }
        end
      end
    end

    def destroy
      @place = trip.places.find(params[:id])
      authorize @place

      @place.destroy!

      respond_to do |format|
        format.turbo_stream
        format.html { redirect_to trip_places_path(trip) }
      end
    end

    private

    def place_params
      params.require(:place).permit(:name, :address, :latitude, :longitude, :category)
    end
  end
end
