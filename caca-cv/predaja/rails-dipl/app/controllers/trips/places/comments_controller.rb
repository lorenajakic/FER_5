module Trips
  module Places
    class CommentsController < Trips::BaseController
      before_action :set_place

      def create
        @comment = place.place_comments.build(comment_params)
        @comment.user = current_user

        authorize @comment

        if @comment.save
          respond_to do |format|
            format.turbo_stream
            format.html { redirect_to trip_places_path(trip) }
          end
        else
          redirect_to trip_places_path(trip), alert: @comment.errors.full_messages.join(', ')
        end
      end

      def destroy
        @comment = place.place_comments.find(params[:id])
        authorize @comment

        @comment.destroy!

        respond_to do |format|
          format.turbo_stream
          format.html { redirect_to trip_places_path(trip) }
        end
      end

      private

      attr_reader :place

      def set_place
        @place = trip.places.find(params[:place_id])
      end

      def comment_params
        params.require(:place_comment).permit(:body)
      end
    end
  end
end
